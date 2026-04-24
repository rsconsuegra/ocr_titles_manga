# US-PP2: Preview Single Preprocessing Step

**Feature**: Preprocessing Playground
**Depends on**: US-PP1 (step registry and schemas)
**Blocks**: US-PP3 (pipeline preview builds on this)

---

## Overview

Create an API endpoint that accepts an image and a single step configuration, applies the step, and returns the transformed image as base64 alongside metadata. This enables the "try before you commit" workflow.

---

## Implementation Details

### 1. `ocr_manga_title/api/schemas/preprocess.py` (additions)

```python
class PreviewStepRequest(BaseModel):
    step_name: str
    config: dict[str, Any]

class PreviewStepResponse(BaseModel):
    image: str                  # base64 data URL: "data:image/png;base64,..."
    metadata: dict[str, Any]
    processing_time_ms: int
```

### 2. `ocr_manga_title/api/routes/preprocess.py` (additions)

```python
import base64
import time
import numpy as np
import cv2
from fastapi import UploadFile, File, Form, HTTPException

@router.post("/preview/step", response_model=PreviewStepResponse)
async def preview_step(
    image: UploadFile = File(...),
    config: str = Form(...),       # JSON string of PreviewStepRequest
):
    import json
    request = PreviewStepRequest(**json.loads(config))
    
    # Validate step name
    if request.step_name not in STEP_REGISTRY:
        raise HTTPException(422, f"Unknown step: {request.step_name}")
    
    # Decode image
    content = await image.read()
    nparr = np.frombuffer(content, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(400, "Could not decode image")
    
    # Create step instance and process
    step = _create_step(request.step_name)
    start = time.time()
    result_img, metadata = step.process(img, request.config)
    elapsed_ms = int((time.time() - start) * 1000)
    
    # Encode result
    _, buffer = cv2.imencode(".png", result_img)
    b64 = "data:image/png;base64," + base64.b64encode(buffer).decode()
    
    return PreviewStepResponse(image=b64, metadata=metadata, processing_time_ms=elapsed_ms)
```

Helper `_create_step(step_name)` instantiates the correct step class from the steps module.

### 3. Frontend: API Client

Add to `frontend/src/api/client.ts`:
```typescript
export async function previewStep(
    file: File, stepName: string, config: Record<string, any>
): Promise<PreviewStepResponse> {
    const formData = new FormData();
    formData.append("image", file);
    formData.append("config", JSON.stringify({ step_name: stepName, config }));
    return apiFetch("/api/v1/preprocess/preview/step", { method: "POST", body: formData });
}
```

### 4. Frontend: ImageCompare component

`frontend/src/components/ImageCompare.tsx`:
- Two-panel layout: "Original" (left) | "Transformed" (right)
- Props: `originalSrc: string | null`, `transformedSrc: string | null`
- Images displayed with `object-contain` scaling
- Empty state placeholders

---

## Acceptance Criteria

- [ ] `POST /api/v1/preprocess/preview/step` accepts multipart (image file + JSON config)
- [ ] Returns base64 data URL of transformed image
- [ ] Returns metadata dict with step-specific information (e.g., threshold value for binarize)
- [ ] Returns processing time in milliseconds
- [ ] Returns 422 for unknown step names
- [ ] Returns 400 for unrecognizable image data
- [ ] Grayscale step produces a grayscale image from a color input
- [ ] Binarize step with `method: "otsu"` produces a binary image
- [ ] Frontend displays original and transformed images side by side
- [ ] Preview works for all 5 step types

---

## Test Specifications

**File**: `tests/test_api/test_preprocess.py` (additions)

Tests:
- `test_preview_grayscale`: POST with grayscale step on a color image → returns base64, metadata has `converted: true`
- `test_preview_binarize_otsu`: POST with binarize otsu → metadata has `method: "otsu"` and `threshold` value
- `test_preview_unknown_step`: POST with step_name="nonexistent" → 422
- `test_preview_invalid_image`: POST with non-image bytes → 400
- `test_preview_roi_with_contour`: POST with roi step → metadata has `crop_performed` key
- `test_preview_denoise_gaussian`: POST with denoise → metadata has `method: "gaussian"`
- `test_preview_upscale_cubic`: POST with upscale → metadata has `scale_factor` and size info
