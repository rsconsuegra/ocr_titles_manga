"""Quick run API route — stateless full pipeline execution with image caching."""

import json
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from ocr_manga_title.api.dependencies import get_db
from ocr_manga_title.api.schemas.ocr import QuickRunResponse
from ocr_manga_title.services.cache import (
    hash_bytes,
    run_all_models_cached,
    run_preprocessing_cached,
)
from ocr_manga_title.services.image import save_bytes
from ocr_manga_title.services.ocr import run_llm_extraction

SYNC_BLOCKED_METHODS = {"edsr"}

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
    pp_steps = json.loads(preprocess_steps)
    ocr_mods = json.loads(ocr_models)
    effective_llm_provider = llm_provider

    llm_cfg: dict | None = None
    if llm_system_prompt or llm_user_prompt or llm_temperature or llm_max_ocr_chars:
        llm_cfg = {
            "system_prompt": llm_system_prompt,
            "user_prompt_template": llm_user_prompt or "{ocr_text}",
            "temperature": float(llm_temperature) if llm_temperature else 0.1,
            "max_ocr_chars": int(llm_max_ocr_chars) if llm_max_ocr_chars else 0,
        }

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
        if not llm_cfg and hasattr(profile, "llm_config") and profile.llm_config:
            llm_cfg = profile.llm_config

    try:
        raw = await file.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid image: {e}"
        ) from e

    tmp_path: str | None = None
    try:
        try:
            tmp_path = save_bytes(raw)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid image: {e}",
            ) from e

        image_hash = hash_bytes(raw)

        ocr_image_path = tmp_path
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
                pp_path = await run_preprocessing_cached(db, raw, pp_steps)
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
                llm_data = run_llm_extraction(
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
        if tmp_path:
            Path(tmp_path).unlink(missing_ok=True)
