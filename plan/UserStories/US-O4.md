# US-O4: Run Tesseract on English and Japanese Text

**Phase**: 0 (OCR Engine) — Sub-phase 0B  
**Priority**: High  
**Status**: Planned

---

## Story

> As an operator, I want to use Tesseract as a general-purpose OCR fallback that handles both English and Japanese so that I have a baseline comparison for manga-ocr results.

---

## Scope

### In Scope
- `TesseractModel` class implementing `BaseOCRModel` interface
- pytesseract wrapper with configurable language packs
- PSM (Page Segmentation Mode) and OEM (OCR Engine Mode) configuration from `ocrs.yaml`
- Confidence calculation from pytesseract word-level data
- Processing time measurement

### Out of Scope
- Tesseract binary installation (operator responsibility)
- Language pack installation (operator responsibility)
- Image preprocessing (deskewing, binarization)
- Custom traineddata files
- PDF input support

---

## Preconditions

1. **US-O2 complete**: `schemas.py`, `exceptions.py`, `models/base.py` exist
2. `pyproject.toml` has `pytesseract` and `pillow` in dependencies
3. Tesseract binary installed on system (`tesseract` in PATH)
4. English (`eng`) and Japanese (`jpn`) language packs installed
5. `ocrs.yaml` has tesseract config block with `languages`, `psm`, `oem` fields

---

## Implementation Details

### File: `manga_ocr/models/tesseract_model.py`

```python
class TesseractModel(BaseOCRModel):
    def __init__(self, config: ModelConfig):
        # Extract config:
        # self._languages = config.language or config.parameters.get("languages", ["eng", "jpn"])
        #   If config.language is a list, join with "+" for tesseract: "eng+jpn"
        #   If config.language is a str, use directly
        # self._psm = config.parameters.get("psm", 3)
        # self._oem = config.parameters.get("oem", 3)
        # self._config = "--psm {psm} --oem {oem}"

    @property
    def name(self) -> str:
        return "tesseract"

    @property
    def is_available(self) -> bool:
        # Try: pytesseract.get_tesseract_version()
        # Return True if succeeds, False if raises (binary not found)
        # Do NOT raise

    def run(self, image_path: str) -> OCRResult:
        # 1. Validate image_path exists
        # 2. Open with PIL Image
        # 3. Start timer
        # 4. raw_text = pytesseract.image_to_string(image, lang=self._lang_string, config=self._config)
        # 5. data = pytesseract.image_to_data(image, lang=self._lang_string, config=self._config, output_type=Output.DICT)
        # 6. Stop timer
        # 7. Calculate confidence:
        #    confs = [int(c) for c in data["conf"] if int(c) >= 30]
        #    confidence = sum(confs) / len(confs) / 100.0 if confs else 0.0
        # 8. Return OCRResult(...)
```

Key decisions:
- Language string format: pytesseract expects `"eng+jpn"`, not a list. Convert from `ocrs.yaml` list format.
- Confidence: use `image_to_data()` which returns per-word confidence scores (0-100). Filter out words with confidence < 30 (noise), average the rest, normalize to 0.0-1.0.
- `image_to_string()` for the actual text output.
- Both calls (`image_to_string` and `image_to_data`) add overhead. If performance becomes an issue, use only `image_to_data` and reconstruct text from the word list. For v1, use both for clarity.
- PSM modes reference:
  - 3 = Fully automatic page segmentation (default, good for general images)
  - 6 = Assume a single uniform block of text
  - 11 = Sparse text. Find as much text as possible in no particular order
- OEM modes reference:
  - 3 = Default, based on what is available
  - 1 = LSTM only (most accurate for Japanese)

Error handling:
- `image_path` does not exist: raise `FileNotFoundError`
- Tesseract binary not found: `is_available` returns `False`, `run()` raises `ModelNotAvailableError` with message like "Tesseract binary not found. Install: brew install tesseract"
- Language pack missing: pytesseract raises `TesseractError`. Catch and return `OCRResult` with error message suggesting: "Japanese language pack missing. Install: brew install tesseract-lang"
- Corrupt image: catch PIL errors, return `OCRResult` with error

---

## Postconditions

1. `TesseractModel` can be instantiated with a `ModelConfig`
2. `is_available` returns `True` when Tesseract binary is in PATH
3. `run()` returns `OCRResult` with English and/or Japanese text
4. Confidence is computed from word-level scores
5. Language, PSM, OEM settings come from `ocrs.yaml`

---

## Validation Checklist

- [ ] `TesseractModel(config).name == "tesseract"`
- [ ] `TesseractModel(config).is_available` returns bool
- [ ] `run("english_text.png")` returns `OCRResult` with English text, confidence > 0
- [ ] `run("japanese_text.png")` returns `OCRResult` with Japanese text
- [ ] `run("mixed_en_ja.png")` returns `OCRResult` with both languages
- [ ] `run("nonexistent.png")` raises `FileNotFoundError`
- [ ] Language setting from `ocrs.yaml` is used (not hardcoded)
- [ ] PSM and OEM from `ocrs.yaml` parameters are applied
- [ ] `processing_time_ms` is recorded and > 0
- [ ] Confidence is computed as average of word-level scores (filtered < 30)

---

## Test Plan

### File: `tests/test_models.py` (section for Tesseract)

**Mocked tests**:

1. `test_tesseract_name` — assert `model.name == "tesseract"`
2. `test_tesseract_is_available_when_installed` — mock `get_tesseract_version()`, assert `True`
3. `test_tesseract_is_available_when_not_installed` — mock to raise, assert `False`
4. `test_tesseract_run_returns_ocr_result` — mock `image_to_string` to return "Hello World", assert `OCRResult` structure
5. `test_tesseract_run_uses_language_config` — verify `lang="eng+jpn"` passed to pytesseract
6. `test_tesseract_run_uses_psm_config` — verify `config` string contains `--psm 3`
7. `test_tesseract_run_uses_oem_config` — verify `config` string contains `--oem 3`
8. `test_tesseract_confidence_from_word_data` — mock `image_to_data` with known confidence values, assert computed average matches
9. `test_tesseract_confidence_filters_low_words` — mock data with some conf=10 values, assert they are excluded
10. `test_tesseract_confidence_zero_when_no_words` — mock empty data, assert confidence=0.0
11. `test_tesseract_run_nonexistent_image_raises` — assert `FileNotFoundError`
12. `test_tesseract_run_records_processing_time` — assert `processing_time_ms >= 0`
13. `test_tesseract_language_list_format` — config with `languages: ["eng", "jpn"]`, verify joined as `"eng+jpn"`
14. `test_tesseract_language_string_format` — config with `language: "eng"`, verify used directly

---

## Questions for Operator

1. Do you already have Tesseract installed with Japanese language pack? (If not, `brew install tesseract tesseract-lang` on macOS)

---

## Dependencies

- **US-O2** (config, schemas, exceptions, base interface)
- System dependency: Tesseract binary + language packs

---

## Estimated Complexity

**Medium** — similar to manga-ocr but with additional confidence calculation logic and more config options.
