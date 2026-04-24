# US-O6: Detect ISBN and Codes via Rules

**Phase**: 0 (OCR Engine) — Sub-phase 0C  
**Priority**: High  
**Status**: Planned

---

## Story

> As an operator, I want the rule-based matcher to detect ISBN-10, ISBN-13, and other common manga code patterns from raw text so that codes are extracted even when the LLM misses them.

---

## Scope

### In Scope
- `RuleMatcher` class with `match()` and `augment()` methods
- ISBN-10 detection via regex
- ISBN-13 detection via regex
- Title normalization (whitespace, unicode, punctuation)
- Augmenting existing `ExtractedTitle` with rule-based findings
- All patterns defined in code (no external config)

### Out of Scope
- ISBN checksum validation (verify check digit)
- Custom configurable regex patterns (future)
- Manga-specific code databases
- URL detection in text
- Date detection in text

---

## Preconditions

1. **US-O2 complete**: `ExtractedTitle` schema defined
2. No external dependencies beyond standard library (`re`, `unicodedata`)

---

## Implementation Details

### File: `manga_ocr/postprocess/rule_matcher.py`

```python
import re
import unicodedata
from manga_ocr.schemas import ExtractedTitle


class RuleMatcher:
    ISBN_10_PATTERN = re.compile(
        r'(?:ISBN[- ]?)?(?:\d[\s-]?){9}[\dXx]'
    )
    ISBN_13_PATTERN = re.compile(
        r'(?:ISBN[- ]?)?97[89](?:[\s-]?\d){10}'
    )

    def match(self, text: str) -> ExtractedTitle:
        """
        Scan text for ISBNs and codes.
        Returns ExtractedTitle with any found codes.
        """

    def augment(self, existing: ExtractedTitle, text: str) -> ExtractedTitle:
        """
        Takes an existing ExtractedTitle (e.g., from LLM).
        Fills in None fields with rule-based findings.
        Does NOT overwrite fields the LLM already populated.
        Returns new ExtractedTitle with augmented data.
        """

    @staticmethod
    def normalize_title(title: str) -> str:
        """
        1. unicodedata.normalize("NFC", title)
        2. Collapse whitespace (re.sub(r'\s+', ' ', ...))
        3. Strip leading/trailing whitespace
        4. Strip trailing punctuation (。、！？!?,.)
        """

    @staticmethod
    def normalize_isbn(isbn: str) -> str:
        """
        Strip hyphens, spaces, and "ISBN" prefix.
        Return digits only (plus X for ISBN-10 check digit).
        """
```

**`match()` logic**:
1. Try ISBN-13 regex first (more specific, 13-digit pattern)
2. If not found, try ISBN-10 regex
3. If found, normalize ISBN (strip hyphens/spaces)
4. Return `ExtractedTitle(code=normalized_isbn, confidence=0.9, source_method="rules")`
5. If no code found, return `ExtractedTitle(confidence=0.0, source_method="rules")`

**`augment()` logic**:
1. If `existing.code is None`: run `match()` to find codes, fill in
2. If `existing.title_en is None`: no rule-based way to detect title, leave as None
3. If `existing.title_ja is None`: no rule-based way to detect title, leave as None
4. If `existing.title_en is not None`: apply `normalize_title()` to it
5. If `existing.title_ja is not None`: apply `normalize_title()` to it
6. Build new `ExtractedTitle` with augmented data
7. Set `source_method` to `"llm+rules"` if LLM data was present and rules added something, otherwise keep original method

**ISBN regex details**:
- ISBN-10: 10 digits (last may be X), possibly separated by hyphens/spaces, optionally preceded by "ISBN" or "ISBN-10"
- ISBN-13: starts with 978 or 979, 13 digits total, same separators
- Pattern should match in longer text (not require the ISBN to be isolated)
- Multiple ISBNs: return the first match (or all matches in future)

---

## Postconditions

1. `RuleMatcher.match("ISBN 4-06-319310-6")` returns `ExtractedTitle(code="4063193106", confidence=0.9)`
2. `RuleMatcher.match("978-4-06-319310-8")` returns `ExtractedTitle(code="9784063193108", confidence=0.9)`
3. `RuleMatcher.match("no codes here")` returns `ExtractedTitle(confidence=0.0)`
4. `RuleMatcher.augment(existing_llm_result, raw_text)` fills in missing fields without overwriting existing ones
5. `normalize_title("  Hello   World ！！")` returns `"Hello   World"`
6. `normalize_isbn("ISBN 978-4-06-319310-8")` returns `"9784063193108"`

---

## Validation Checklist

- [ ] ISBN-10 detected: `"ISBN 4-06-319310-6"` -> code `"4063193106"`
- [ ] ISBN-10 without prefix: `"0-306-40615-2"` -> code `"0306406152"`
- [ ] ISBN-10 with X check digit: `"0-8044-2957-X"` -> code `"080442957X"`
- [ ] ISBN-13 detected: `"978-4-06-319310-8"` -> code `"9784063193108"`
- [ ] ISBN-13 with "ISBN" prefix: `"ISBN 978-4063193108"` -> code `"9784063193108"`
- [ ] ISBN-13 preferred over ISBN-10 when both present in text
- [ ] No false positive on random digit sequences
- [ ] Title normalization: whitespace collapsed, trailing punctuation stripped
- [ ] Title normalization: unicode NFC normalized
- [ ] `augment()` does NOT overwrite LLM-populated fields
- [ ] `augment()` fills in `code` when LLM returned `None`
- [ ] `augment()` normalizes existing titles from LLM

---

## Test Plan

### File: `tests/test_postprocess.py` (section for rule matcher)

Pure unit tests, no mocks needed:

1. `test_match_isbn10_with_prefix` — `"ISBN 4-06-319310-6"` -> `code="4063193106"`
2. `test_match_isbn10_without_prefix` — `"0-306-40615-2"` -> `code="0306406152"`
3. `test_match_isbn10_with_x` — `"0-8044-2957-X"` -> `code="080442957X"`
4. `test_match_isbn13_with_prefix` — `"ISBN 978-4-06-319310-8"` -> `code="9784063193108"`
5. `test_match_isbn13_without_prefix` — `"9784063193108"` -> `code="9784063193108"`
6. `test_match_isbn13_preferred_over_isbn10` — text with both -> returns ISBN-13
7. `test_match_no_code` — `"just some text"` -> `ExtractedTitle(confidence=0.0)`
8. `test_match_code_in_longer_text` — `"Published as ISBN 4-06-319310-6 in Japan"` -> finds code
9. `test_normalize_title_whitespace` — `"  Hello   World  "` -> `"Hello World"`
10. `test_normalize_title_trailing_punctuation` — `"One Piece！！"` -> `"One Piece"`
11. `test_normalize_title_unicode_nfc` — composed vs decomposed chars -> NFC form
12. `test_normalize_isbn_strips_hyphens` — `"978-4-06-319310-8"` -> `"9784063193108"`
13. `test_normalize_isbn_strips_prefix` — `"ISBN 978-4-06-319310-8"` -> `"9784063193108"`
14. `test_augment_fills_missing_code` — `ExtractedTitle(code=None)` + text with ISBN -> `code` filled
15. `test_augment_does_not_overwrite_code` — `ExtractedTitle(code="existing")` + text with ISBN -> `code` stays "existing"
16. `test_augment_normalizes_existing_titles` — `ExtractedTitle(title_en="  Naruto  ！")` -> title normalized
17. `test_augment_source_method` — when rules add code to LLM result -> `source_method="llm+rules"`
18. `test_augment_no_changes` — LLM result fully populated, no codes in text -> unchanged except normalization

---

## Questions for Operator

None.

---

## Dependencies

- **US-O2** (`ExtractedTitle` schema)
- Standard library only

---

## Estimated Complexity

**Low-Medium** — regex patterns and string normalization. The `augment()` logic with conditional merging adds moderate complexity.
