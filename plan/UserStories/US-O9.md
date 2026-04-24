# US-O9: Test the Pipeline Interactively

**Phase**: 0 (OCR Engine) — Sub-phase 0E  
**Priority**: Medium  
**Status**: Planned

---

## Story

> As an operator, I want a Jupyter notebook where I can load images, run individual models, compare outputs, and test the full pipeline so that I can experiment with configuration and evaluate results visually.

---

## Scope

### In Scope
- Jupyter notebook `notebooks/01_ocr_testing.ipynb`
- Sections for: config loading, individual model testing, LLM extraction, rule matching, full pipeline, batch testing
- Inline display of results (text, confidence scores)
- Works with any image in `images_path`

### Out of Scope
- Automated notebook testing (notebooks are for manual use)
- Image display/rendering in notebook (just text results)
- Interactive widgets or forms
- Notebook parameterization (papermill)

---

## Preconditions

1. **US-O2 through US-O8 complete**: all pipeline components implemented
2. `pyproject.toml` has `jupyter` in dev dependencies
3. At least one test image available in `images_path` (or operator will provide their own)
4. All dependencies installed via `uv sync`

---

## Implementation Details

### File: `notebooks/01_ocr_testing.ipynb`

**Section 1: Setup & Config**

```python
import sys
sys.path.insert(0, "..")

from manga_ocr.config import load_config, load_ocr_config
from manga_ocr.schemas import OCRResult, ExtractedTitle, PipelineResult

config = load_config("../configs.toml")
ocr_config = load_ocr_config("../ocrs.yaml")

print("App Config:")
print(f"  images_path: {config.images_path}")
print(f"  openrouter model: {config.openrouter.default_model}")
print(f"\nOCR Models:")
for name, cfg in ocr_config.items():
    print(f"  {name}: enabled={cfg.enabled}, language={cfg.language}")
```

**Section 2: Run manga-ocr**

```python
from manga_ocr.models.manga_ocr_model import MangaOCRModel

model = MangaOCRModel(ocr_config["manga_ocr"])
print(f"Available: {model.is_available}")

if model.is_available:
    import glob
    images = sorted(glob.glob(str(config.images_path / "*.png")))[:3]
    for img_path in images:
        print(f"\n--- {img_path} ---")
        result = model.run(img_path)
        print(f"Raw text: {result.raw_text[:200]}")
        print(f"Confidence: {result.confidence}")
        print(f"Time: {result.processing_time_ms}ms")
```

**Section 3: Run Tesseract**

```python
from manga_ocr.models.tesseract_model import TesseractModel

model = TesseractModel(ocr_config["tesseract"])
# Same pattern as Section 2
```

**Section 4: LLM Extraction**

```python
from manga_ocr.postprocess.llm_extractor import LLMExtractor

extractor = LLMExtractor(config.openrouter, prompt_path="../prompts/llm/extract_title_v1.md")

sample_text = "ワンピース One Piece ISBN 978-4-08-872509-4"
result = extractor.extract(sample_text)
print(f"title_en: {result.title_en}")
print(f"title_ja: {result.title_ja}")
print(f"code: {result.code}")
print(f"confidence: {result.confidence}")
```

**Section 5: Rule Matching**

```python
from manga_ocr.postprocess.rule_matcher import RuleMatcher

matcher = RuleMatcher()
text = "Published as ISBN 978-4-06-319310-8"
result = matcher.match(text)
print(f"code: {result.code}")
print(f"confidence: {result.confidence}")
```

**Section 6: Full Pipeline**

```python
from manga_ocr.engine import OCREngine

engine = OCREngine(config, ocr_config)
if images:
    result = engine.process(images[0])
    print(f"Input: {result.input_path}")
    print(f"Extracted: {result.extracted}")
    print(f"OCR Results: {len(result.ocr_results)}")
    for r in result.ocr_results:
        print(f"  {r.model_name}: conf={r.confidence}, time={r.processing_time_ms}ms")
        if r.error:
            print(f"    ERROR: {r.error}")
    print(f"Errors: {result.errors}")
```

**Section 7: Batch Test**

```python
import pandas as pd

results = []
for img in images[:10]:
    r = engine.process(img)
    results.append({
        "image": Path(r.input_path).name,
        "title_en": r.extracted.title_en if r.extracted else None,
        "title_ja": r.extracted.title_ja if r.extracted else None,
        "code": r.extracted.code if r.extracted else None,
        "confidence": r.extracted.confidence if r.extracted else 0,
        "errors": len(r.errors),
    })

df = pd.DataFrame(results)
df
```

---

## Postconditions

1. Notebook exists at `notebooks/01_ocr_testing.ipynb`
2. All cells are runnable (may produce empty results if no images or API key)
3. No import errors when running cells
4. Each section demonstrates one pipeline component
5. Full pipeline section shows end-to-end processing

---

## Validation Checklist

- [ ] Notebook file exists at `notebooks/01_ocr_testing.ipynb`
- [ ] Section 1 loads config without errors
- [ ] Section 2 runs manga-ocr (or shows "not available" gracefully)
- [ ] Section 3 runs Tesseract (or shows "not available" gracefully)
- [ ] Section 4 runs LLM extraction on sample text
- [ ] Section 5 runs rule matching on sample text
- [ ] Section 6 runs full pipeline on an image
- [ ] Section 7 creates a results DataFrame
- [ ] No cells produce unhandled exceptions (graceful degradation)

---

## Test Plan

No automated tests for the notebook itself. Validated manually by running all cells.

Verify:
- `make notebook` launches Jupyter and opens the notebook
- All cells execute without errors (given proper config and at least one image)

---

## Questions for Operator

1. Do you have sample manga images available for testing, or should I include instructions for obtaining test images?

---

## Dependencies

- **US-O2 through US-O8** all complete
- `jupyter` in dev dependencies
- `pandas` optional (for Section 7 batch table) — add to dev deps if used

---

## Estimated Complexity

**Low** — primarily documentation/display code in a notebook format.
