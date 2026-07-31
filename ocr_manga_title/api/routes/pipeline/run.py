"""Quick run API route — stateless full pipeline execution with image caching."""

import asyncio
import copy
import time
import uuid
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from ocr_manga_title.api.dependencies import get_db
from ocr_manga_title.api.routes._helpers import (
    check_edsr_sync_blocked,
    get_profile_or_404,
    parse_json_form,
    parse_llm_form_config,
    uploaded_image,
)
from ocr_manga_title.api.schemas.ocr import QuickRunResponse
from ocr_manga_title.preprocess.transform import CoordinateTransform
from ocr_manga_title.services.cache import (
    hash_bytes,
    run_all_models_cached,
    run_preprocessing_cached,
)
from ocr_manga_title.services.ocr import pick_best, run_llm_extraction

router = APIRouter()


def _merge_profile_with_overrides(
    profile_steps: dict[str, Any] | None,
    profile_models: dict[str, Any] | None,
    profile_llm: bool,
    profile_llm_provider: str,
    override_steps: dict[str, Any],
    override_models: dict[str, Any],
    override_llm: bool | None,
    override_llm_provider: str | None,
) -> tuple[dict[str, Any], dict[str, Any], bool, str]:
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
    reasoning_enabled: str = Form(""),
    profile_id: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
) -> QuickRunResponse:
    """Execute a stateless full pipeline run on a single image."""
    pp_steps = parse_json_form(preprocess_steps, "preprocess_steps")
    ocr_mods = parse_json_form(ocr_models, "ocr_models")
    effective_llm_provider = llm_provider
    llm_cfg = parse_llm_form_config(
        llm_system_prompt,
        llm_user_prompt,
        llm_temperature,
        llm_max_ocr_chars,
        reasoning_enabled,
    )

    if profile_id:
        try:
            pid = uuid.UUID(profile_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid profile_id"
            ) from None
        profile = await get_profile_or_404(db, pid)
        pp_steps, ocr_mods, enable_llm, effective_llm_provider = (
            _merge_profile_with_overrides(
                profile.preprocess_steps,
                profile.ocr_models,
                profile.enable_llm,
                profile.llm_provider,
                pp_steps,
                ocr_mods,
                None,
                None,
            )
        )
        if not llm_cfg and profile.llm_config:
            llm_cfg = profile.llm_config

    async with uploaded_image(file) as (raw, tmp_path):
        image_hash = hash_bytes(raw)

        ocr_image_path = tmp_path
        step_metadata = None
        if pp_steps:
            upscale_cfg = pp_steps.get("upscale", {})
            check_edsr_sync_blocked("upscale", upscale_cfg if isinstance(upscale_cfg, dict) else {})
            try:
                pp_path, step_metadata = await run_preprocessing_cached(
                    db, raw, pp_steps
                )
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
            ocr_results = copy.deepcopy(ocr_results)
            transform = CoordinateTransform.from_pipeline(step_metadata)
            for ocr_result in ocr_results:
                if ocr_result.blocks:
                    for block in ocr_result.blocks:
                        block.bbox = transform.inverse_map_bbox(block.bbox)

        llm_data = None
        if enable_llm:
            best = pick_best(ocr_results)
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
