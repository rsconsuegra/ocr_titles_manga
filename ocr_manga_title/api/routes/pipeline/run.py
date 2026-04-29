"""Quick run API route — stateless full pipeline execution with image caching."""

import asyncio
import json
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from ocr_manga_title.api.dependencies import get_db
from ocr_manga_title.api.routes._helpers import (
    parse_llm_form_config,
    save_uploaded_image,
)
from ocr_manga_title.api.schemas.ocr import QuickRunResponse
from ocr_manga_title.services.cache import (
    hash_bytes,
    run_all_models_cached,
    run_preprocessing_cached,
)
from ocr_manga_title.services.ocr import run_llm_extraction

from ocr_manga_title.preprocess.registry import SYNC_BLOCKED_METHODS

router = APIRouter()


def _merge_profile_with_overrides(
    profile_steps: dict | None,
    profile_models: dict | None,
    profile_llm: bool,
    profile_llm_provider: str,
    override_steps: dict,
    override_models: dict,
    override_llm: bool | None,
    override_llm_provider: str | None,
) -> tuple[dict, dict, bool, str]:
    base_steps = dict(profile_steps or {})
    base_steps.update(override_steps)

    base_models = dict(profile_models or {})
    base_models.update(override_models)

    enable_llm = override_llm if override_llm is not None else profile_llm
    llm_provider = override_llm_provider or profile_llm_provider
    return base_steps, base_models, enable_llm, llm_provider


@router.post("/quick", response_model=QuickRunResponse)
async def quick_run(
    file: UploadFile = File(...),
    preprocess_steps: str = Form("{}"),
    ocr_models: str = Form("{}"),
    enable_llm: bool = Form(False),
    llm_provider: str = Form("openrouter"),
    llm_model: str = Form(""),
    llm_system_prompt: str = Form(""),
    llm_user_prompt: str = Form(""),
    llm_temperature: str = Form(""),
    llm_max_ocr_chars: str = Form(""),
    profile_id: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
):
    try:
        pp_steps = json.loads(preprocess_steps)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON in preprocess_steps",
        )
    try:
        ocr_mods = json.loads(ocr_models)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON in ocr_models",
        )
    effective_llm_provider = llm_provider
    llm_cfg = parse_llm_form_config(
        llm_system_prompt, llm_user_prompt, llm_temperature, llm_max_ocr_chars
    )

    if profile_id:
        from ocr_manga_title.db.crud import get_profile

        try:
            pid = uuid.UUID(profile_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid profile_id"
            ) from None
        profile = await get_profile(db, pid)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
            )
        pp_steps, ocr_mods, enable_llm, effective_llm_provider = _merge_profile_with_overrides(
            profile.preprocess_steps,
            profile.ocr_models,
            profile.enable_llm,
            profile.llm_provider,
            pp_steps,
            ocr_mods,
            None,
            None,
        )
        if not llm_cfg and profile.llm_config:
            llm_cfg = profile.llm_config

    raw, tmp_path = await save_uploaded_image(file)
    try:
        image_hash = hash_bytes(raw)

        ocr_image_path = tmp_path
        step_metadata = None
        if pp_steps:
            upscale_cfg = pp_steps.get("upscale", {})
            if isinstance(upscale_cfg, dict) and upscale_cfg.get("method") in SYNC_BLOCKED_METHODS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "EDSR super-resolution is too slow on CPU for interactive use. "
                        "Use FSRCNN or cubic for quick runs, or include EDSR in a pipeline profile."
                    ),
                )
            try:
                pp_path, step_metadata = await run_preprocessing_cached(db, raw, pp_steps)
                ocr_image_path = pp_path
            except TimeoutError as e:
                raise HTTPException(
                    status_code=status.HTTP_408_REQUEST_TIMEOUT,
                    detail=str(e),
                ) from e
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Preprocessing failed: {e}",
                ) from e

        start_total = time.monotonic()
        ocr_results = await run_all_models_cached(
            db, image_hash, ocr_image_path, ocr_mods
        )

        if step_metadata:
            from ocr_manga_title.preprocess.transform import CoordinateTransform
            transform = CoordinateTransform.from_pipeline(step_metadata)
            for ocr_result in ocr_results:
                if ocr_result.blocks:
                    for block in ocr_result.blocks:
                        block.bbox = transform.inverse_map_bbox(block.bbox)

        llm_data = None
        if enable_llm:
            best = next(
                (
                    r
                    for r in sorted(
                        ocr_results, key=lambda r: r.confidence, reverse=True
                    )
                    if r.raw_text.strip() and not r.error
                ),
                None,
            )
            if best:
                llm_data = await asyncio.to_thread(
                    run_llm_extraction,
                    best.raw_text,
                    provider=effective_llm_provider,
                    llm_model=llm_model or None,
                    llm_config=llm_cfg,
                )

        total_ms = int((time.monotonic() - start_total) * 1000)
        return QuickRunResponse(
            ocr_results=ocr_results,
            llm=llm_data,
            total_processing_time_ms=total_ms,
        )
    finally:
        Path(tmp_path).unlink(missing_ok=True)
