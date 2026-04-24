"""Quick run API route — stateless full pipeline execution."""

import time
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ocr_manga_title.api.dependencies import get_db
from ocr_manga_title.api.schemas.ocr import QuickRunRequest, QuickRunResponse
from ocr_manga_title.services.image import decode_and_save
from ocr_manga_title.services.ocr import run_all_enabled_models, run_llm_extraction
from ocr_manga_title.services.preprocess import run_preprocessing_pipeline

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
    body: QuickRunRequest,
    db: AsyncSession = Depends(get_db),
):
    preprocess_steps = body.preprocess_steps
    ocr_models = body.ocr_models
    enable_llm = body.enable_llm

    if body.profile_id:
        from ocr_manga_title.db.crud import get_profile

        try:
            pid = uuid.UUID(body.profile_id)
        except ValueError:
            raise HTTPException(
                status_code=400, detail="Invalid profile_id"
            ) from None
        profile = await get_profile(db, pid)
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        preprocess_steps, ocr_models, enable_llm = _merge_profile_with_overrides(
            profile.preprocess_steps,
            profile.ocr_models,
            profile.enable_llm,
            body.preprocess_steps,
            body.ocr_models,
            body.enable_llm if body.enable_llm else None,
        )

    tmp_paths: list[str] = []
    try:
        try:
            tmp_path = decode_and_save(body.image)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid image: {e}") from e
        tmp_paths.append(tmp_path)

        ocr_image_path = tmp_path
        if preprocess_steps:
            try:
                pp_path = run_preprocessing_pipeline(body.image, preprocess_steps)
                tmp_paths.append(pp_path)
                ocr_image_path = pp_path
            except Exception as e:
                raise HTTPException(
                    status_code=400, detail=f"Preprocessing failed: {e}"
                ) from e

        start_total = time.monotonic()
        ocr_results = run_all_enabled_models(ocr_image_path, ocr_models)

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
        for p in tmp_paths:
            Path(p).unlink(missing_ok=True)
