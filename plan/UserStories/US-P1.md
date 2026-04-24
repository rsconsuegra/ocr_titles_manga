# US-P1: Config, Schemas & Base Infrastructure

**Phase**: P (Preprocessing) — Sub-phase PA  
**Priority**: Critical (blocking — all other P stories depend on this)  
**Status**: Planned

---

## Story

> As an operator, I want a configurable preprocessing pipeline loaded from `preprocess.yaml` so that I can enable/disable individual steps and tune parameters without editing source code.

---

## Scope

### In Scope
- `preprocess.yaml` config file with all preprocessing settings
- `load_preprocess_config()` function in `manga_ocr/config.py`
- `PreProcessStepResult` and `PreProcessResult` Pydantic schemas
- Update `PipelineResult` with `preprocess_result` field
- `BasePreProcessor` abstract base class
- `PreProcessingPipeline` orchestrator skeleton (step loading, ordering, debug mode)
- Debug mode: save intermediate images to `{images_path}/.preprocess/`
- Step registry: mapping step names to classes

### Out of Scope
- Individual step implementations (US-P2 through US-P5)
- Engine integration (US-P6)
- Notebook and full test suite (US-P7)

---

## Preconditions

1. Phase 0 complete: `manga_ocr/schemas.py`, `manga_ocr/config.py`, `manga_ocr/exceptions.py` exist
2. `opencv-python-headless` and `numpy` added to `pyproject.toml` dependencies
3. `pyyaml` already available from Phase 0

---

## Implementation Details

### File: `preprocess.yaml` (project root)

```yaml
preprocessing:
  enabled: true
  debug: true
  roi:
    enabled: true
    method: "contour"
    min_area: 500
    padding: 10
    merge_overlap: 0.3
  grayscale:
    enabled: true
  upscale:
    enabled: true
    method: "cubic"
    scale_factor: 2
  denoise:
    enabled: true
    method: "gaussian"
    strength: "light"
  binarize:
    enabled: true
    method: "otsu"
    invert: false
    block_size: 11
    c: 2
```

### File: `manga_ocr/schemas.py` (updated)

Add after existing schemas:

```python
class PreProcessStepResult(BaseModel):
    step_name: str
    enabled: bool
    success: bool
    processing_time_ms: int
    output_path: str | None = None
    error: str | None = None
    metadata: dict[str, Any] = {}


class PreProcessResult(BaseModel):
    input_path: str
    output_path: str | None = None
    steps: list[PreProcessStepResult] = []
    total_processing_time_ms: int = 0
```

Update `PipelineResult`:

```python
class PipelineResult(BaseModel):
    ...existing fields...
    preprocess_result: PreProcessResult | None = None
```

### File: `manga_ocr/config.py` (updated)

Add function:

```python
def load_preprocess_config(config_path: str | Path = "preprocess.yaml") -> dict:
    """
    1. Read file using PyYAML (yaml.safe_load)
    2. Return raw dict (not Pydantic) for flexibility — step classes access their own keys
    3. Missing file: return {"preprocessing": {"enabled": false}} (preprocessing disabled by default)
    4. Empty file: same as missing
    5. Missing "preprocessing" key: return {"preprocessing": {"enabled": false}}
    6. Missing step sub-keys: each step uses its own defaults
    """
```

Key behavior: **preprocessing config is optional**. If file is missing or empty, preprocessing is disabled. This ensures backward compatibility.

### File: `manga_ocr/preprocess/__init__.py`

```python
from manga_ocr.preprocess.pipeline import PreProcessingPipeline

__all__ = ["PreProcessingPipeline"]
```

### File: `manga_ocr/preprocess/base.py`

```python
from abc import ABC, abstractmethod

import numpy as np


class BasePreProcessor(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def is_available(self) -> bool: ...

    @abstractmethod
    def process(self, image: np.ndarray, config: dict) -> tuple[np.ndarray, dict]:
        """
        Process image and return (processed_image, metadata_dict).
        If step is disabled or encounters an error, return input unchanged.
        """
        ...
```

### File: `manga_ocr/preprocess/steps/__init__.py`

Empty file. Individual step modules added in US-P2 through US-P5.

### File: `manga_ocr/preprocess/pipeline.py`

```python
import logging
import time
from pathlib import Path

import cv2
import numpy as np

from manga_ocr.preprocess.base import BasePreProcessor
from manga_ocr.schemas import PreProcessResult, PreProcessStepResult

logger = logging.getLogger(__name__)


class PreProcessingPipeline:
    STEP_ORDER = ["roi", "grayscale", "upscale", "denoise", "binarize"]

    def __init__(self, config: dict, images_path: Path):
        self._config = config.get("preprocessing", {})
        self._debug = self._config.get("debug", False)
        self._images_path = images_path
        self._steps: list[BasePreProcessor] = self._initialize_steps()

    def _initialize_steps(self) -> list[BasePreProcessor]:
        """Initialize step instances. Individual steps added in US-P2-P5."""
        steps = []
        for step_name in self.STEP_ORDER:
            step_config = self._config.get(step_name, {})
            step = self._create_step(step_name, step_config)
            if step is not None:
                steps.append(step)
        return steps

    def _create_step(self, name: str, config: dict) -> BasePreProcessor | None:
        """Factory method. Returns None for unknown steps."""
        # Will be populated as steps are implemented
        # For US-P1, returns None for all steps (skeleton only)
        logger.debug(f"Step '{name}' not yet registered")
        return None

    def _debug_save(self, image: np.ndarray, step_name: str, timestamp: str) -> str:
        """Save intermediate image for debugging."""
        debug_dir = self._images_path / ".preprocess"
        debug_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{timestamp}_{step_name}.png"
        path = debug_dir / filename
        cv2.imwrite(str(path), image)
        return str(path)

    def process(self, image_path: str) -> PreProcessResult:
        """
        Run preprocessing pipeline on image.
        Returns PreProcessResult with step results.
        If pipeline fails, returns result with error info but no crash.
        """
        start_time = time.time()
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        step_results: list[PreProcessStepResult] = []

        image = cv2.imread(image_path)
        if image is None:
            return PreProcessResult(
                input_path=image_path,
                output_path=None,
                steps=[PreProcessStepResult(
                    step_name="load",
                    enabled=True,
                    success=False,
                    processing_time_ms=0,
                    error=f"Failed to read image: {image_path}",
                )],
                total_processing_time_ms=0,
            )

        current_image = image
        final_output_path: str | None = None

        for step in self._steps:
            step_config = self._config.get(step.name, {})
            enabled = step_config.get("enabled", True)

            if not enabled:
                step_results.append(PreProcessStepResult(
                    step_name=step.name,
                    enabled=False,
                    success=True,
                    processing_time_ms=0,
                ))
                continue

            step_start = time.time()
            try:
                result_image, metadata = step.process(current_image, step_config)
                step_time_ms = int((time.time() - step_start) * 1000)

                output_path = None
                if self._debug and result_image is not None:
                    output_path = self._debug_save(result_image, step.name, timestamp)

                step_results.append(PreProcessStepResult(
                    step_name=step.name,
                    enabled=True,
                    success=True,
                    processing_time_ms=step_time_ms,
                    output_path=output_path,
                    metadata=metadata,
                ))
                current_image = result_image
                final_output_path = output_path
            except Exception as e:
                step_time_ms = int((time.time() - step_start) * 1000)
                logger.error(f"Preprocessing step '{step.name}' failed: {e}")
                step_results.append(PreProcessStepResult(
                    step_name=step.name,
                    enabled=True,
                    success=False,
                    processing_time_ms=step_time_ms,
                    error=str(e),
                ))

        total_time_ms = int((time.time() - start_time) * 1000)

        return PreProcessResult(
            input_path=image_path,
            output_path=final_output_path,
            steps=step_results,
            total_processing_time_ms=total_time_ms,
        )
```

---

## Postconditions

1. `load_preprocess_config("preprocess.yaml")` returns a dict with preprocessing config
2. `load_preprocess_config("nonexistent.yaml")` returns `{"preprocessing": {"enabled": false}}` (no error)
3. `PreProcessResult` and `PreProcessStepResult` schemas importable from `manga_ocr.schemas`
4. `PipelineResult` has `preprocess_result` field (default `None`)
5. `BasePreProcessor` ABC is importable, cannot be instantiated directly
6. `PreProcessingPipeline` can be instantiated with config dict and images_path
7. `PreProcessingPipeline.process()` returns `PreProcessResult` even with no steps registered
8. Debug mode creates `.preprocess/` directory and saves intermediate images

---

## Validation Checklist

- [ ] `load_preprocess_config()` loads valid YAML without error
- [ ] `load_preprocess_config()` with missing file returns disabled config (no exception)
- [ ] `load_preprocess_config()` with empty file returns disabled config
- [ ] `PreProcessStepResult` validates correctly with all fields
- [ ] `PreProcessResult` validates correctly with nested step results
- [ ] `PipelineResult` accepts `preprocess_result=None` (backward compatible)
- [ ] `PipelineResult` accepts `preprocess_result=PreProcessResult(...)` 
- [ ] `BasePreProcessor` cannot be instantiated (abstract)
- [ ] `PreProcessingPipeline.__init__()` succeeds with valid config
- [ ] `PreProcessingPipeline.process()` returns `PreProcessResult` for valid image
- [ ] `PreProcessingPipeline.process()` returns error result for unreadable image
- [ ] Debug mode saves images to `.preprocess/` directory

---

## Test Plan

### File: `tests/test_preprocess.py`

**Config tests**:
1. `test_load_preprocess_config_valid` — valid YAML, assert returned dict has expected structure
2. `test_load_preprocess_config_missing_file` — nonexistent file, assert returns `{"preprocessing": {"enabled": false}}`
3. `test_load_preprocess_config_empty_file` — empty YAML, assert returns disabled config
4. `test_load_preprocess_config_missing_preprocessing_key` — YAML without `preprocessing:` key, assert disabled

**Schema tests**:
5. `test_preprocess_step_result_valid` — construct with all fields, assert valid
6. `test_preprocess_result_with_steps` — construct with nested step results
7. `test_pipeline_result_with_preprocess_result` — verify backward compatibility

**Base class tests**:
8. `test_base_preprocessor_is_abstract` — attempt to instantiate, assert TypeError

**Pipeline tests** (with mocked steps):
9. `test_pipeline_init_with_no_steps` — no steps registered, assert empty step list
10. `test_pipeline_process_returns_result` — process a real image, assert PreProcessResult returned
11. `test_pipeline_process_invalid_image` — nonexistent image, assert error in result
12. `test_pipeline_debug_saves_intermediates` — debug=True, mock step, assert file saved
13. `test_pipeline_disabled_step_skipped` — step with enabled=False, assert not called

---

## Questions for Operator

None.

---

## Dependencies

- Phase 0 complete (schemas, config, exceptions)
- `opencv-python-headless` and `numpy` installed

---

## Estimated Complexity

**Medium** — straightforward config and schema work, but the pipeline skeleton needs to handle step registration, debug output, and error recovery correctly.
