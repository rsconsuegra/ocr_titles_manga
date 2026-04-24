"""OCR playground API routes."""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ocr_manga_title.api.dependencies import get_db
from ocr_manga_title.api.schemas.ocr import (
    ModelDescriptorResponse,
    ModelParamDescriptorResponse,
    OCRExportRequest,
    OCRRunRequest,
    OCRRunResponse,
)
from ocr_manga_title.db.models import ModelConfig as ModelConfigDB
from ocr_manga_title.engine.registry import MODEL_REGISTRY, get_model
from ocr_manga_title.services.image import decode_and_save
from ocr_manga_title.services.ocr import (
    check_model_availability,
    run_llm_extraction,
    run_single_model,
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
async def run_ocr(body: OCRRunRequest):
    """Run a single OCR model on the given image, optionally with LLM post-processing."""
    descriptor = get_model(body.model_name)
    if not descriptor:
        raise HTTPException(status_code=400, detail=f"Unknown model: {body.model_name}")

    tmp_path = None
    try:
        try:
            tmp_path = decode_and_save(body.image)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid image: {e}") from e

        ocr_data = run_single_model(body.model_name, tmp_path, body.params)

        if ocr_data.error and "not available" in ocr_data.error:
            raise HTTPException(status_code=400, detail=ocr_data.error)

        llm_data = None
        if body.enable_llm and ocr_data.raw_text.strip():
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
