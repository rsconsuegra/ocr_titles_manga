"""OCR playground API routes."""

import asyncio
import json
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ocr_manga_title.api.dependencies import get_db
from ocr_manga_title.api.routes._helpers import (
    parse_llm_form_config,
    save_uploaded_image,
)
from ocr_manga_title.api.schemas.ocr import (
    ModelDescriptorResponse,
    ModelParamDescriptorResponse,
    OCRExportRequest,
    OCRRunResponse,
    YamlExportResponse,
)
from ocr_manga_title.config import resolve_model_configs
from ocr_manga_title.db.models import ModelConfig as ModelConfigDB
from ocr_manga_title.engine.registry import MODEL_REGISTRY, get_model
from ocr_manga_title.services.cache import hash_bytes, run_ocr_cached
from ocr_manga_title.services.ocr import (
    check_model_availability,
    run_llm_extraction,
)

router = APIRouter()


@router.get("/registry", response_model=list[ModelDescriptorResponse])
async def list_ocr_models(db: AsyncSession = Depends(get_db)):
    """Return all OCR model descriptors with availability and effective enabled status."""
    stmt = select(ModelConfigDB)
    result = await db.execute(stmt)
    db_rows = {
        m.model_name: {"is_enabled": m.is_enabled, "parameters": m.parameters or {}}
        for m in result.scalars().all()
    }

    resolved = resolve_model_configs(db_rows)

    response = []
    for name, descriptor in MODEL_REGISTRY.items():
        cfg = resolved.get(name)
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
                enabled=cfg.enabled if cfg else False,
            )
        )
    return response


@router.post("/run", response_model=OCRRunResponse)
async def run_ocr(
    file: UploadFile = File(...),
    model_name: str = Form(...),
    params: str = Form("{}"),
    enable_llm: bool = Form(False),
    llm_provider: str = Form("openrouter"),
    llm_model: str = Form(""),
    llm_system_prompt: str = Form(""),
    llm_user_prompt: str = Form(""),
    llm_temperature: str = Form(""),
    llm_max_ocr_chars: str = Form(""),
    reasoning_enabled: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    """Run a single OCR model on the given image, optionally with LLM post-processing."""
    descriptor = get_model(model_name)
    if not descriptor:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown model: {model_name}",
        )

    try:
        parsed_params = json.loads(params)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON in params",
        )

    raw, tmp_path = await save_uploaded_image(file)
    try:
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
            llm_cfg = parse_llm_form_config(
                llm_system_prompt, llm_user_prompt, llm_temperature, llm_max_ocr_chars, reasoning_enabled
            )
            llm_data = await asyncio.to_thread(
                run_llm_extraction,
                ocr_data.raw_text,
                provider=llm_provider,
                llm_model=llm_model or None,
                llm_config=llm_cfg,
            )

        return OCRRunResponse(ocr=ocr_data, llm=llm_data)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@router.post("/export", response_model=YamlExportResponse)
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
    return YamlExportResponse(yaml=yaml_str)
