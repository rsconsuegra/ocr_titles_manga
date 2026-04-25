# US-2A3: Run Vision API Model for Manga Text Extraction

**Sub-phase**: 2A — Additional OCR Models
**Depends on**: US-1A2 (ModelConfig table), existing `openai` dep
**Blocks**: US-2C1 (pipeline diagram shows enabled models)

---

## Overview

Replace the GLM OCR stub in `ocr_manga_title/engine/glm_ocr_model.py` with a generic vision API adapter. The adapter sends images as base64 to any OpenAI-compatible vision endpoint (OpenRouter, ZhipuAI, OpenAI, etc.) using the existing `openai` Python SDK. No model download required — pure HTTP client. Configurable endpoint, model, API key, and prompt via model parameters.

---

## Implementation Details

### 1. `ocr_manga_title/engine/glm_ocr_model.py`

Replace the existing stub with a generic vision API adapter:

```python
import base64
import time
import logging
from pathlib import Path

import openai

from ocr_manga_title.engine.base import BaseOCRModel
from ocr_manga_title.schemas import ModelConfig, OCRResult
from ocr_manga_title.exceptions import ModelNotAvailableError

logger = logging.getLogger(__name__)

MIME_MAP = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
    "tiff": "image/tiff",
    "tif": "image/tiff",
    "bmp": "image/bmp",
}


class GLMOCRModel(BaseOCRModel):
    def __init__(self, config: ModelConfig):
        self._config = config
        self._client = None

    @property
    def name(self) -> str:
        return "glm_ocr"

    @property
    def is_available(self) -> bool:
        params = self._config.parameters or {}
        return bool(params.get("api_endpoint"))

    def _get_client(self) -> openai.OpenAI:
        if self._client is None:
            params = self._config.parameters or {}
            self._client = openai.OpenAI(
                base_url=params.get("api_endpoint", ""),
                api_key=params.get("api_key", ""),
            )
        return self._client

    def _encode_image(self, image_path: str) -> str:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def run(self, image_path: str) -> OCRResult:
        if not self.is_available:
            raise ModelNotAvailableError("Vision API endpoint not configured")

        start = time.monotonic()
        try:
            client = self._get_client()
            params = self._config.parameters or {}

            ext = Path(image_path).suffix.lower().lstrip(".")
            mime = MIME_MAP.get(ext, "image/png")
            b64 = self._encode_image(image_path)

            response = client.chat.completions.create(
                model=params.get("model", "google/gemini-2.5-flash"),
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": params.get(
                                    "prompt",
                                    "Extract all text from this image.",
                                ),
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime};base64,{b64}"
                                },
                            },
                        ],
                    }
                ],
                max_tokens=params.get("max_tokens", 4096),
                temperature=params.get("temperature", 0.1),
            )

            raw_text = response.choices[0].message.content or ""
            elapsed_ms = int((time.monotonic() - start) * 1000)

            return OCRResult(
                raw_text=raw_text,
                model_name=self.name,
                confidence=0.8 if raw_text else 0.0,
                processing_time_ms=elapsed_ms,
            )
        except Exception as e:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            logger.warning("Vision API error for %s: %s", image_path, e)
            return OCRResult(
                raw_text="",
                model_name=self.name,
                confidence=0.0,
                processing_time_ms=elapsed_ms,
                error=str(e),
            )
```

### 2. `ocr_manga_title/engine/registry.py` (partial update)

Update GLM OCR's `ModelDescriptor` params:

```python
"glm_ocr": ModelDescriptor(
    name="glm_ocr",
    label="Vision API (GLM OCR)",
    description="Generic vision-language model OCR via OpenAI-compatible API",
    model_cls=GLMOCRModel,
    params=[
        ParamDescriptor(
            name="api_endpoint",
            type="select",
            default="",
            label="API Endpoint",
            description="Vision API base URL (e.g. https://openrouter.ai/api/v1)",
        ),
        ParamDescriptor(
            name="model",
            type="select",
            default="google/gemini-2.5-flash",
            label="Model",
            description="Vision model identifier at the endpoint",
        ),
        ParamDescriptor(
            name="api_key",
            type="select",
            default="",
            label="API Key",
            description="API key (leave empty to use OpenRouter key)",
        ),
        ParamDescriptor(
            name="prompt",
            type="select",
            default="Extract all text from this image.",
            label="Extraction Prompt",
            description="Text prompt sent with the image",
        ),
    ],
),
```

### 3. `config/ocrs.yaml` (partial update)

```yaml
  glm_ocr:
    enabled: false
    api_endpoint: ""
    model: "google/gemini-2.5-flash"
    api_key: ""
    prompt: "Extract all text from this image."
```

### 4. `migrations/versions/002_seed_models.py` (update)

Update the glm_ocr seed row parameters JSONB to include new fields:

```python
# glm_ocr seed
{
    "model_name": "glm_ocr",
    "is_enabled": False,
    "parameters": {
        "api_endpoint": "",
        "model": "google/gemini-2.5-flash",
        "api_key": "",
        "prompt": "Extract all text from this image.",
    },
}
```

---

## Acceptance Criteria

- [ ] Vision API model appears as "GLM OCR" in `GET /api/v1/models`
- [ ] `is_available` returns `True` when `api_endpoint` configured, `False` when empty
- [ ] When enabled, sends image as base64 to configured endpoint via OpenAI chat completions format
- [ ] Configurable: `api_endpoint`, `api_key`, `model`, `prompt`, `max_tokens`, `temperature`
- [ ] If `api_key` empty, falls back to OpenRouter API key from `configs.toml`
- [ ] Returns `OCRResult` with model response as `raw_text`, confidence 0.8 for non-empty
- [ ] Handles API errors: timeout, rate limit (429), auth failure — returns `OCRResult` with error
- [ ] No model download required (pure API client)

---

## Test Specifications

**File**: `tests/test_engine/test_vision_api_model.py`

Tests:
- `test_is_available_true_when_endpoint_set` — `ModelConfig(parameters={"api_endpoint": "https://example.com/v1"})`; verify `is_available == True`
- `test_is_available_false_when_endpoint_empty` — `ModelConfig(parameters={})`; verify `is_available == False`
- `test_run_sends_base64_image` — mock `openai.OpenAI`; verify `chat.completions.create` called with image_url content type containing `data:image/png;base64,`
- `test_run_handles_api_error` — mock client to raise `openai.APIConnectionError`; verify `OCRResult.error` is set
- `test_run_handles_rate_limit` — mock client to raise `openai.RateLimitError`; verify error captured
- `test_configurable_model_and_prompt` — pass `parameters={"model": "gpt-4o", "prompt": "Read this"}`; verify passed to API call
- `test_uses_configured_endpoint` — verify `openai.OpenAI(base_url=...)` receives the configured endpoint
- `test_run_raises_when_not_available` — `api_endpoint=""`; verify `ModelNotAvailableError`
- `test_name_returns_glm_ocr` — verify `name` property returns `"glm_ocr"`
- `test_handles_various_image_formats` — test with `.jpg`, `.png`, `.webp` paths; verify correct MIME type in request
