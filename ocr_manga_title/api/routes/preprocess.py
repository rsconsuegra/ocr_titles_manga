"""Preprocessing playground API routes."""

import time

from fastapi import APIRouter, HTTPException

from ocr_manga_title.api.schemas.preprocess import (
    ExportPipelineRequest,
    PipelineStepResult,
    PreviewPipelineRequest,
    PreviewPipelineResponse,
    PreviewStepRequest,
    PreviewStepResponse,
    StepDescriptorResponse,
)
from ocr_manga_title.preprocess.registry import STEP_ORDER, STEP_REGISTRY, get_all_steps
from ocr_manga_title.services.image import decode_image, encode_image
from ocr_manga_title.services.preprocess import get_step_instance

router = APIRouter()


@router.get("/steps", response_model=list[StepDescriptorResponse])
async def list_steps():
    """Return all available preprocessing step descriptors in canonical order."""
    steps = get_all_steps()
    return [
        StepDescriptorResponse(
            name=s.name,
            label=s.label,
            description=s.description,
            params=[p.__dict__ for p in s.params],
        )
        for s in steps
    ]


@router.post("/preview/step", response_model=PreviewStepResponse)
async def preview_step(body: PreviewStepRequest):
    """Preview a single preprocessing step applied to the given image."""
    if body.step_name not in STEP_REGISTRY:
        raise HTTPException(status_code=400, detail=f"Unknown step: {body.step_name}")

    try:
        image = decode_image(body.image)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image: {e}") from e

    step = get_step_instance(body.step_name)
    start = time.monotonic()
    try:
        result_img, metadata = step.process(image, body.params)
        elapsed_ms = int((time.monotonic() - start) * 1000)
        return PreviewStepResponse(
            image=encode_image(result_img),
            step_name=body.step_name,
            metadata=metadata,
            processing_time_ms=elapsed_ms,
            success=True,
        )
    except Exception as e:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        return PreviewStepResponse(
            image=encode_image(image),
            step_name=body.step_name,
            metadata={},
            processing_time_ms=elapsed_ms,
            success=False,
            error=str(e),
        )


@router.post("/preview/pipeline", response_model=PreviewPipelineResponse)
async def preview_pipeline(body: PreviewPipelineRequest):
    """Preview the full preprocessing pipeline, returning an image after each step."""
    try:
        current_image = decode_image(body.image)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image: {e}") from e

    start_total = time.monotonic()
    results: list[PipelineStepResult] = []

    for step_name in STEP_ORDER:
        step_config = body.steps.get(step_name, {})
        enabled = (
            step_config.pop("enabled", True) if isinstance(step_config, dict) else True
        )

        if not enabled:
            results.append(
                PipelineStepResult(
                    step_name=step_name,
                    enabled=False,
                    success=True,
                    image=None,
                )
            )
            continue

        step = get_step_instance(step_name)
        step_start = time.monotonic()
        try:
            result_img, metadata = step.process(current_image, step_config)
            elapsed_ms = int((time.monotonic() - step_start) * 1000)
            results.append(
                PipelineStepResult(
                    step_name=step_name,
                    enabled=True,
                    success=True,
                    image=encode_image(result_img),
                    metadata=metadata,
                    processing_time_ms=elapsed_ms,
                )
            )
            current_image = result_img
        except Exception as e:
            elapsed_ms = int((time.monotonic() - step_start) * 1000)
            results.append(
                PipelineStepResult(
                    step_name=step_name,
                    enabled=True,
                    success=False,
                    image=encode_image(current_image),
                    error=str(e),
                    processing_time_ms=elapsed_ms,
                )
            )

    total_ms = int((time.monotonic() - start_total) * 1000)
    return PreviewPipelineResponse(steps=results, total_processing_time_ms=total_ms)


@router.post("/export")
async def export_pipeline(body: ExportPipelineRequest):
    """Export the configured pipeline as a YAML string matching preprocess.yaml format."""
    import yaml

    yaml_steps: dict[str, dict] = {}
    for step_name in STEP_ORDER:
        step_config = dict(body.steps.get(step_name, {}))
        step_config["enabled"] = True
        yaml_steps[step_name] = step_config

    payload = {
        "preprocessing": {
            "enabled": True,
            "debug": False,
            **yaml_steps,
        }
    }

    yaml_str = yaml.dump(payload, default_flow_style=False, sort_keys=False)
    return {"yaml": yaml_str}
