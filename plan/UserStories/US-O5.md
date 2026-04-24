# US-O5: Extract Structured Data via LLM

**Phase**: 0 (OCR Engine) — Sub-phase 0C  
**Priority**: High  
**Status**: Planned

---

## Story

> As an operator, I want raw OCR text to be sent to an LLM (via OpenRouter) that extracts the manga title (English and Japanese), codes, and ISBNs so that I get clean, structured data instead of noisy raw text.

---

## Scope

### In Scope
- `LLMExtractor` class with `extract()` method
- OpenRouter API integration via OpenAI Python SDK
- Prompt loading from local file (`prompts/llm/extract_title_v1.md`)
- JSON response parsing into `ExtractedTitle`
- Graceful error handling: invalid JSON, API errors, timeouts
- Configurable model ID from `configs.toml`
- Logging of token usage and latency

### Out of Scope
- Agenta.ai integration (Phase 2)
- Prompt versioning (Phase 2)
- Multiple prompt templates (Phase 2)
- Streaming responses
- Response caching
- Token cost tracking

---

## Preconditions

1. **US-O2 complete**: `AppConfig` with `OpenRouterConfig` available, `ExtractedTitle` schema defined
2. `pyproject.toml` has `openai` in dependencies
3. `configs.toml` has valid `openrouter.api_key` and `openrouter.default_model`
4. `prompts/llm/extract_title_v1.md` exists with extraction prompt
5. OpenRouter API accessible (network)

---

## Implementation Details

### File: `prompts/llm/extract_title_v1.md`

This is the LLM system prompt. It must instruct the model to:

```
You are a manga metadata extraction assistant. You receive raw OCR text from manga-related images
(social media posts, book covers, storefront screenshots). Your job is to extract structured manga
metadata.

Extract the following fields:
- title_en: English manga title (if present). Use the official English title if recognizable.
- title_ja: Japanese manga title (if present). Original Japanese title in kanji/kana.
- code: Any ISBN, product code, or manga identifier found. Normalize ISBN by removing hyphens/spaces.
- confidence: Your confidence in the extraction as a float 0.0 to 1.0.

Rules:
- OCR text may be noisy, contain artifacts, or be partially readable.
- Text may be in English, Japanese, or mixed.
- If multiple titles appear, extract the primary/most prominent one.
- If a field cannot be determined, set it to null.
- If no manga-related content is found at all, return all nulls with confidence 0.0.

You MUST respond with valid JSON only, no other text:
{"title_en": "...", "title_ja": "...", "code": "...", "confidence": 0.0}
```

### File: `manga_ocr/postprocess/llm_extractor.py`

```python
class LLMExtractor:
    def __init__(self, config: OpenRouterConfig, prompt_path: str | Path | None = None):
        # self._client = openai.OpenAI(
        #     api_key=config.api_key,
        #     base_url=config.base_url,
        # )
        # self._model = config.default_model
        # self._prompt_path = Path(prompt_path or "prompts/llm/extract_title_v1.md")
        # self._system_prompt = self._load_prompt()

    def _load_prompt(self) -> str:
        # Read self._prompt_path, return contents as string
        # If file not found: log error, return a hardcoded fallback prompt
        # (hardcoded fallback prevents total failure if prompt file is missing)

    def extract(self, raw_text: str, model: str | None = None) -> ExtractedTitle:
        # 1. model = model or self._model
        # 2. Start timer
        # 3. response = self._client.chat.completions.create(
        #      model=model,
        #      messages=[
        #        {"role": "system", "content": self._system_prompt},
        #        {"role": "user", "content": raw_text}
        #      ],
        #      temperature=0.1,  # low temperature for consistent extraction
        #      response_format={"type": "json_object"}  # force JSON if model supports it
        #    )
        # 4. content = response.choices[0].message.content
        # 5. Parse content as JSON
        # 6. Map to ExtractedTitle:
        #      title_en=json.get("title_en")
        #      title_ja=json.get("title_ja")
        #      code=json.get("code")
        #      confidence=float(json.get("confidence", 0.0))
        #      source_model=model
        #      source_method="llm"
        # 7. Log token usage and latency at DEBUG level
        # 8. Return ExtractedTitle
        #
        # Error handling:
        # - JSON decode error: try to extract JSON from markdown code blocks (```json ... ```)
        #   If still fails: return ExtractedTitle(confidence=0.0), log error
        # - openai.APIError: return ExtractedTitle(confidence=0.0, source_method="llm_failed"), log error
        # - openai.APITimeoutError: same as above
        # - openai.AuthenticationError: same as above (log as ERROR, not DEBUG)
        # - Any other exception: same pattern, log with traceback
```

Key decisions:
- Use `openai` SDK with `base_url` pointing to OpenRouter. OpenRouter is OpenAI-compatible.
- `temperature=0.1` for deterministic extraction (not 0.0 — some models don't support exact 0)
- `response_format={"type": "json_object"}` — not all OpenRouter models support this. Wrap in try/except; if it fails, retry without `response_format`.
- Prompt file fallback: if `extract_title_v1.md` is missing, use a hardcoded string rather than crashing. This is a safety net.
- JSON extraction from markdown: LLM sometimes wraps JSON in ```json ... ``` blocks. Handle this with regex: `re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)`
- Never raise exceptions from `extract()`. Always return `ExtractedTitle`, even if all fields are None with confidence 0.0. This ensures the pipeline continues.

---

## Postconditions

1. `LLMExtractor` can be instantiated with `OpenRouterConfig`
2. `extract("raw text")` sends request to OpenRouter and returns `ExtractedTitle`
3. Invalid JSON responses are handled without crashing
4. API errors (timeout, auth, rate limit) return `ExtractedTitle(confidence=0.0)` with error logged
5. Prompt is loaded from `prompts/llm/extract_title_v1.md`
6. Model ID is configurable (from config or per-call override)

---

## Validation Checklist

- [ ] `LLMExtractor(config).extract("One Piece ワンピース ISBN 978-4-08-872509-4")` returns `ExtractedTitle` with title_en="One Piece", title_ja="ワンピース", code containing ISBN
- [ ] `extract()` uses model from `configs.toml` by default
- [ ] `extract(model="anthropic/claude-sonnet-4")` overrides default model
- [ ] Prompt loaded from `prompts/llm/extract_title_v1.md`
- [ ] If prompt file missing, hardcoded fallback is used (logged as warning)
- [ ] LLM returning `{"title_en": null, "title_ja": null, "code": null, "confidence": 0.0}` produces valid `ExtractedTitle`
- [ ] LLM returning invalid JSON produces `ExtractedTitle(confidence=0.0)` with error logged
- [ ] LLM returning JSON wrapped in markdown code blocks is parsed correctly
- [ ] OpenRouter timeout returns `ExtractedTitle(confidence=0.0, source_method="llm_failed")`
- [ ] Invalid API key returns `ExtractedTitle(confidence=0.0)` with ERROR-level log
- [ ] Token usage logged at DEBUG level
- [ ] No unhandled exceptions from `extract()`

---

## Test Plan

### File: `tests/test_postprocess.py` (section for LLM extractor)

All tests mock the `openai.OpenAI` client. No real API calls.

**Mocking strategy**: Use `unittest.mock.patch("openai.OpenAI")` or inject mock client via constructor.

1. `test_llm_extract_valid_response` — mock response with valid JSON `{"title_en": "Naruto", "title_ja": "ナルト", "code": "978-4-08-873021-0", "confidence": 0.95}`, assert `ExtractedTitle` fields match
2. `test_llm_extract_null_response` — mock response with all nulls, assert `ExtractedTitle` with None fields
3. `test_llm_extract_invalid_json` — mock response with plain text "not json", assert `ExtractedTitle(confidence=0.0)`
4. `test_llm_extract_json_in_markdown` — mock response with "```json\n{...}\n```", assert parsed correctly
5. `test_llm_extract_api_error` — mock `client.chat.completions.create` to raise `openai.APIError`, assert graceful return
6. `test_llm_extract_timeout` — mock to raise `openai.APITimeoutError`, assert graceful return
7. `test_llm_extract_auth_error` — mock to raise `openai.AuthenticationError`, assert graceful return with ERROR log
8. `test_llm_extract_uses_config_model` — verify `model` argument in API call matches config
9. `test_llm_extract_uses_override_model` — call `extract(text, model="custom-model")`, verify override model used
10. `test_llm_extract_loads_prompt` — create temp prompt file, verify system message content matches
11. `test_llm_extract_fallback_prompt` — set nonexistent prompt path, verify hardcoded fallback used with warning log
12. `test_llm_extract_temperature` — verify `temperature=0.1` in API call
13. `test_llm_extract_logs_token_usage` — mock response with `usage` field, verify logged at DEBUG

---

## Questions for Operator

1. Do you have an OpenRouter API key ready? It needs to be in `configs.toml` before testing this interactively.
2. Any preferred default model on OpenRouter, or keep `google/gemini-2.5-flash`?

---

## Dependencies

- **US-O2** (config, schemas, exceptions)
- `prompts/llm/extract_title_v1.md` must exist
- OpenRouter API key configured in `configs.toml`

---

## Estimated Complexity

**Medium-High** — API integration with robust error handling, JSON parsing edge cases, and configurable parameters.
