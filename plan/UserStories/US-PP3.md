# US-PP3: Compose and Preview Pipeline

**Feature**: Preprocessing Playground
**Depends on**: US-PP1 (step registry), US-PP2 (single step preview)
**Blocks**: US-PP4 (export uses same pipeline config format)

---

## Overview

Create an API endpoint that accepts an image and a full pipeline configuration (ordered steps with enable flags), runs the enabled steps sequentially in canonical order, and returns intermediate images after each step. The frontend displays these as a horizontal filmstrip.

---

## Implementation Details

### 1. `ocr_manga_title/api/schemas/preprocess.py` (additions)

```python
class PipelineStepConfig(BaseModel):
    step_name: str
    enabled: bool
    config: dict[str, Any]

class StepIntermediate(BaseModel):
    step_name: str
    enabled: bool
    success: bool
    image: str | None = None       # base64 data URL, None if disabled/failed
    metadata: dict[str, Any]
    processing_time_ms: int

class PreviewPipelineResponse(BaseModel):
    intermediates: list[StepIntermediate]   # one per STEP_ORDER entry
    final_image: str                        # base64 of last successful output
    total_processing_time_ms: int
```

### 2. `ocr_manga_title/api/routes/preprocess.py` (additions)

```python
@router.post("/preview/pipeline", response_model=PreviewPipelineResponse)
async def preview_pipeline(
    image: UploadFile = File(...),
    config: str = Form(...),       # JSON string of {steps: [...]}
):
    import json
    request_data = json.loads(config)
    steps_config = {s["step_name"]: s for s in request_data["steps"]}
    
    # Validate all step names
    for s in request_data["steps"]:
        if s["step_name"] not in STEP_REGISTRY:
            raise HTTPException(422, f"Unknown step: {s["step_name"]}")
    
    # Decode image
    content = await image.read()
    current_image = cv2.imdecode(np.frombuffer(content, np.uint8), cv2.IMREAD_COLOR)
    if current_image is None:
        raise HTTPException(400, "Could not decode image")
    
    start = time.time()
    intermediates = []
    final_b64 = _encode_image(current_image)  # original as fallback
    
    # Execute in canonical order
    for step_name in STEP_ORDER:
        cfg = steps_config.get(step_name, {"enabled": False, "config": {}})
        enabled = cfg.get("enabled", False)
        step_config = cfg.get("config", {})
        
        if not enabled:
            intermediates.append(StepIntermediate(
                step_name=step_name, enabled=False, success=True,
                metadata={}, processing_time_ms=0,
            ))
            continue
        
        step = _create_step(step_name)
        step_start = time.time()
        try:
            result_img, metadata = step.process(current_image, step_config)
            elapsed = int((time.time() - step_start) * 1000)
            b64 = _encode_image(result_img)
            intermediates.append(StepIntermediate(
                step_name=step_name, enabled=True, success=True,
                image=b64, metadata=metadata, processing_time_ms=elapsed,
            ))
            current_image = result_img
            final_b64 = b64
        except Exception as e:
            elapsed = int((time.time() - step_start) * 1000)
            intermediates.append(StepIntermediate(
                step_name=step_name, enabled=True, success=False,
                metadata={"error": str(e)}, processing_time_ms=elapsed,
            ))
    
    total_ms = int((time.time() - start) * 1000)
    return PreviewPipelineResponse(
        intermediates=intermediates, final_image=final_b64,
        total_processing_time_ms=total_ms,
    )
```

Helper `_encode_image(img) -> str`: encodes numpy array to base64 data URL.

### 3. Frontend: API Client

```typescript
export async function previewPipeline(
    file: File, steps: PipelineStepConfig[]
): Promise<PreviewPipelineResponse> {
    const formData = new FormData();
    formData.append("image", file);
    formData.append("config", JSON.stringify({ steps }));
    return apiFetch("/api/v1/preprocess/preview/pipeline", { method: "POST", body: formData });
}
```

### 4. Frontend: PipelineFilmstrip component

`frontend/src/components/PipelineFilmstrip.tsx`:
- Horizontal scrollable container
- For each intermediate in `PreviewPipelineResponse.intermediates`:
  - If disabled: gray placeholder with step name and "Skipped"
  - If enabled + success: thumbnail image with step name and processing time
  - If enabled + failed: red border with error message
- Arrow (→) between each thumbnail
- Last successful image highlighted with border
- Clicking a thumbnail could enlarge it (stretch goal)

### 5. Frontend: Pipeline section on Playground page

- Shows all 5 steps as toggle switches in canonical order
- Each toggle shows step display_name and enabled state
- "Run Pipeline" button sends current config to API
- Filmstrip appears below after pipeline runs
- "Export YAML" button (US-PP4)

---

## Acceptance Criteria

- [ ] `POST /api/v1/preprocess/preview/pipeline` accepts multipart (image + JSON pipeline config)
- [ ] Steps execute in canonical order regardless of request order
- [ ] Returns exactly 5 `StepIntermediate` entries (one per canonical step)
- [ ] Disabled steps have `enabled=false` and `image=null`
- [ ] Enabled steps have base64 image in `image` field
- [ ] Each enabled step's output feeds as input to the next step
- [ ] `final_image` is the last successful step's output
- [ ] Failed steps do not break the pipeline — error is captured in metadata
- [ ] Response includes `total_processing_time_ms`
- [ ] Frontend filmstrip shows intermediate images for each step
- [ ] Pipeline toggles allow enabling/disabling individual steps
- [ ] Re-running pipeline with different config updates filmstrip

---

## Test Specifications

**File**: `tests/test_api/test_preprocess.py` (additions)

Tests:
- `test_pipeline_two_steps`: Enable grayscale + binarize → returns 5 intermediates, 2 enabled with images, 3 disabled
- `test_pipeline_all_disabled`: All steps disabled → final_image is original, all intermediates have image=null
- `test_pipeline_all_enabled`: All 5 enabled → all intermediates have images, final is binarize output
- `test_pipeline_step_order`: Verify intermediates are in canonical order regardless of config order
- `test_pipeline_chaining`: Enable grayscale then binarize → binarize input is grayscale output (verify via metadata)
- `test_pipeline_unknown_step`: Include unknown step name → 422
- `test_pipeline_invalid_image`: Non-image bytes → 400
