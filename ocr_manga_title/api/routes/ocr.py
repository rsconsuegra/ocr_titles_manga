"""OCR playground API routes."""

import json
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ocr_manga_title.api.dependencies import get_db
from ocr_manga_title.api.schemas.ocr import (
    ModelDescriptorResponse,
    ModelParamDescriptorResponse,
    OCRExportRequest,
    OCRRunResponse,
)
from ocr_manga_title.db.models import ModelConfig as ModelConfigDB
from ocr_manga_title.engine.registry import MODEL_REGISTRY, get_model
from ocr_manga_title.services.cache import hash_bytes, run_ocr_cached
from ocr_manga_title.services.image import save_bytes
from ocr_manga_title.services.ocr import (
    check_model_availability,
    run_llm_extraction,
)

router = APIRouter()


@router.get("/registry", response_model=list[ModelDescriptorResponse])
async def list_ocr_models(db: AsyncSession = Depends(get_db)):
    """Return all OCR model descriptors with availability and DB enabled status."""
    stmt = select(ModelConfigDB)
    result = await db.execute(stmt)
    db_configs = {m.model_name: m for m in result.scalars().all()}

    response = []
    for name, descriptor in MODEL_REGISTRY.items():
        db_cfg = db_configs.get(name)
        available = check_model_availability(name)

        response.append(
            ModelDescriptorResponse(
                name=descriptor.name,
                label=descriptor.label,
                description=descriptor.description,
                params=[
                    ModelParamDescriptorResponse(**p.__dict__)
                    for p in descriptor.params
                ],
                available=available,
                enabled=db_cfg.is_enabled if db_cfg else False,
            )
        )
    return response


@router.post("/run", response_model=OCRRunResponse)
async def run_ocr(
    file: UploadFile = File(...),
    model_name: str = Form(...),
    params: str = Form("{}"),
    enable_llm: bool = Form(False),
    db: AsyncSession = Depends(get_db),
):
    """Run a single OCR model on the given image, optionally with LLM post-processing."""
    descriptor = get_model(model_name)
    if not descriptor:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown model: {model_name}",
        )

    parsed_params = json.loads(params)

    try:
        raw = await file.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid image: {e}"
        ) from e

    tmp_path = None
    try:
        try:
            tmp_path = save_bytes(raw)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid image: {e}",
            ) from e

        image_hash = hash_bytes(raw)
        ocr_data = await run_ocr_cached(
            db, image_hash, model_name, tmp_path, parsed_params
        )

        if ocr_data.error and "not available" in ocr_data.error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=ocr_data.error
            )

        llm_data = None
        if enable_llm and ocr_data.raw_text.strip():
            llm_data = run_llm_extraction(ocr_data.raw_text)

        return OCRRunResponse(ocr=ocr_data, llm=llm_data)
    finally:
        if tmp_path:
            Path(tmp_path).unlink(missing_ok=True)


@router.post("/export")
async def export_ocr_config(body: OCRExportRequest):
    """Export the configured OCR models as YAML matching ocrs.yaml format."""
    import yaml

    models_yaml: dict[str, dict] = {}
    for name, descriptor in MODEL_REGISTRY.items():
        override = body.models.get(name, {})
        params = {p.name: p.default for p in descriptor.params}
        params.update(override)

        if "languages" in params:
            lang = params.pop("languages")
            if isinstance(lang, str) and "+" in lang:
                params["languages"] = lang.split("+")
            else:
                params["languages"] = [lang] if isinstance(lang, str) else lang

        models_yaml[name] = {"enabled": override.get("enabled", True), **params}

    payload = {"models": models_yaml}
    yaml_str = yaml.dump(payload, default_flow_style=False, sort_keys=False)
    return {"yaml": yaml_str}
