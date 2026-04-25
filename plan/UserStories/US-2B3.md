# US-2B3: Wire Prompt Version Tracking into Pipeline

**Sub-phase**: 2B — Agenta.ai Integration
**Depends on**: US-2B2 (Prompt CRUD API), US-1A3 (PromptVersion table)
**Blocks**: US-2B4 (frontend shows prompt version in run results)

---

## Overview

Connect the pipeline execution to the `prompt_versions` table. When `LLMExtractor` runs, it should load the active prompt from the database (not from file), and when results are saved, the `prompt_version_id` should be recorded on each `PostProcessingResult`. This enables full traceability from output back to the exact prompt used.

---

## Implementation Details

### 1. `ocr_manga_title/postprocess/llm_extractor.py` (update)

Add `prompt_version_id` parameter and DB loading:

```python
import logging
from pathlib import Path

import openai

from ocr_manga_title.schemas import ExtractedTitle, OpenRouterConfig

logger = logging.getLogger(__name__)


class LLMExtractor:
    def __init__(
        self,
        config: OpenRouterConfig,
        prompt_content: str | None = None,
        prompt_version_id: int | None = None,
    ):
        self._config = config
        self._prompt_content = prompt_content or self._load_fallback_prompt()
        self.prompt_version_id = prompt_version_id
        self._client = openai.OpenAI(
            base_url=config.base_url,
            api_key=config.api_key or "",
        )

    @classmethod
    def from_db(
        cls,
        config: OpenRouterConfig,
        session,
        prompt_type: str = "llm",
    ) -> "LLMExtractor":
        """Create extractor using the active prompt from the database."""
        from ocr_manga_title.db.crud import get_active_prompt

        pv = await_sync(get_active_prompt(session, prompt_type))
        if pv:
            return cls(
                config,
                prompt_content=pv.content,
                prompt_version_id=pv.id,
            )
        return cls(config)

    def _load_fallback_prompt(self) -> str:
        prompt_path = Path("prompts/llm/extract_title_v1.md")
        if prompt_path.exists():
            return prompt_path.read_text()
        return self._FALLBACK_PROMPT

    _FALLBACK_PROMPT = "Extract manga title metadata from OCR text..."

    def extract(self, raw_text: str) -> ExtractedTitle:
        # ... existing implementation unchanged ...
        pass
```

### 2. `ocr_manga_title/engine/ocr_engine.py` (update)

Pass `prompt_version_id` through from LLMExtractor to pipeline results:

```python
class OCREngine:
    def __init__(
        self,
        config: AppConfig,
        ocr_config: dict[str, ModelConfig],
        preprocess_config: dict | None = None,
        prompt_version_id: int | None = None,
    ):
        # ... existing init ...
        self._prompt_version_id = prompt_version_id

    def _extract_titles(
        self, results: dict[str, OCRResult]
    ) -> dict[str, ExtractedTitle]:
        if self._enable_llm:
            extractor = LLMExtractor(
                self._config.openrouter,
                prompt_version_id=self._prompt_version_id,
            )
            # ... existing extraction logic ...
```

### 3. `ocr_manga_title/services/pipeline.py` (update)

Save `prompt_version_id` on `PostProcessingResult`:

```python
async def save_pipeline_results(
    session: AsyncSession,
    run_id,
    pipeline_result: PipelineResult,
    prompt_version_id: int | None = None,
):
    for model_name, ocr_data in pipeline_result.ocr_results.items():
        ocr_result = OCRResult(
            pipeline_run_id=run_id,
            model_name=ocr_data.model_name,
            raw_text=ocr_data.raw_text,
            confidence=ocr_data.confidence,
            processing_time_ms=ocr_data.processing_time_ms,
            error=ocr_data.error,
        )
        session.add(ocr_result)
        await session.flush()

        extracted = pipeline_result.extracted_titles.get(model_name)
        if extracted:
            pp_result = PostProcessingResult(
                ocr_result_id=ocr_result.id,
                prompt_version_id=prompt_version_id,
                title_en=extracted.title_en,
                title_ja=extracted.title_ja,
                code=extracted.code,
                confidence=extracted.confidence,
                processing_type="llm",
            )
            session.add(pp_result)
        else:
            # rule-based or none
            pp_result = PostProcessingResult(
                ocr_result_id=ocr_result.id,
                prompt_version_id=None,
                processing_type="rule",
                title_en="",
                title_ja="",
                code="",
                confidence=0.0,
            )
            session.add(pp_result)
```

### 4. `ocr_manga_title/workers/ocr_worker.py` (update)

Load active prompt version and pass through:

```python
async def _process(run_id, session_factory):
    async with session_factory() as session:
        run = await crud.get_pipeline_run(session, run_id)
        # ... existing setup ...

        prompt_version = await crud.get_active_prompt(session, "llm")
        prompt_version_id = prompt_version.id if prompt_version else None

        engine = OCREngine(
            config,
            model_configs,
            preprocess_config,
            prompt_version_id=prompt_version_id,
        )
        result = engine.process(image_path, enable_llm=enable_llm)
        await save_pipeline_results(
            session, run.id, result,
            prompt_version_id=prompt_version_id,
        )
```

### 5. `ocr_manga_title/api/schemas/results.py` (update)

Add `prompt_version_id` to response:

```python
class PostProcessingResultResponse(BaseModel):
    id: int
    ocr_result_id: int
    prompt_version_id: int | None  # NEW
    title_en: str | None
    title_ja: str | None
    code: str | None
    confidence: float
    processing_type: str | None
```

---

## Acceptance Criteria

- [ ] Pipeline worker loads the active `llm` prompt from `prompt_versions` table
- [ ] `LLMExtractor` uses DB-loaded prompt content instead of file when available
- [ ] Falls back to file-based prompt (`prompts/llm/extract_title_v1.md`) if DB has no active prompt
- [ ] `PostProcessingResult.prompt_version_id` is populated after LLM extraction runs
- [ ] `prompt_version_id` is `None` for rule-based extraction (no LLM)
- [ ] OCR playground and quick-run also use DB-loaded prompt
- [ ] Frontend can display which prompt version was used for each post-processing result
- [ ] Existing pipeline runs continue to work (backward compatible — prompt_version_id nullable)

---

## Test Specifications

**File**: `tests/test_services/test_prompt_tracking.py`

Tests:
- `test_worker_loads_active_prompt_from_db` — seed active prompt; run worker; verify `LLMExtractor` initialized with DB prompt content
- `test_worker_falls_back_to_file_prompt` — no active prompt in DB; verify file prompt loaded
- `test_post_processing_result_stores_prompt_version_id` — run pipeline with LLM; verify `prompt_version_id` set on `PostProcessingResult`
- `test_rule_based_result_has_null_prompt_version_id` — run pipeline with `enable_llm=False`; verify `prompt_version_id=None`
- `test_prompt_version_id_propagated_through_engine` — pass `prompt_version_id=42` to `OCREngine`; verify it reaches `LLMExtractor`
- `test_api_response_includes_prompt_version_id` — GET run detail; verify `prompt_version_id` in post-processing response
