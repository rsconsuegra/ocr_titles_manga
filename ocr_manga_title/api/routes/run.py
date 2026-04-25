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

router = APIRouter()


def _merge_profile_with_overrides(
    profile_steps: dict | None,
    profile_models: dict | None,
    profile_llm: bool,
    override_steps: dict,
    override_models: dict,
    override_llm: bool | None,
) -> tuple[dict, dict, bool]:
    base_steps = dict(profile_steps or {})
    base_steps.update(override_steps)

    base_models = dict(profile_models or {})
    base_models.update(override_models)

    enable_llm = override_llm if override_llm is not None else profile_llm
    return base_steps, base_models, enable_llm


@router.post("/quick", response_model=QuickRunResponse)
async def quick_run(
    file: UploadFile = File(...),
    preprocess_steps: str = Form("{}"),
    ocr_models: str = Form("{}"),
    enable_llm: bool = Form(False),
    profile_id: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
):
    pp_steps = json.loads(preprocess_steps)
    ocr_mods = json.loads(ocr_models)

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
        pp_steps, ocr_mods, enable_llm = _merge_profile_with_overrides(
            profile.preprocess_steps,
            profile.ocr_models,
            profile.enable_llm,
            pp_steps,
            ocr_mods,
            None,
        )

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
            try:
                pp_path = await run_preprocessing_cached(db, raw, pp_steps)
                ocr_image_path = pp_path
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
                llm_data = run_llm_extraction(best.raw_text)

        total_ms = int((time.monotonic() - start_total) * 1000)
        return QuickRunResponse(
            ocr_results=ocr_results,
            llm=llm_data,
            total_processing_time_ms=total_ms,
        )
    finally:
        if tmp_path:
            Path(tmp_path).unlink(missing_ok=True)
