"""Rule-based extraction and normalization of ISBN codes and manga titles."""

import re
import unicodedata

from ocr_manga_title.schemas import ExtractedTitle


class RuleMatcher:
    """Regex-driven extractor for ISBN-10 / ISBN-13 codes and title normalizer."""

    ISBN_10_PATTERN = re.compile(r"(?:ISBN[- ]?)?(?:\d[\s-]?){9}[\dXx]")
    ISBN_13_PATTERN = re.compile(r"(?:ISBN[- ]?)?97[89](?:[\s-]?\d){10}")

    def match(self, text: str) -> ExtractedTitle:
        """Search *text* for ISBN codes and return a structured result.

        ISBN-13 patterns are checked before ISBN-10 to avoid false positives.
        Only ISBNs with valid check digits are accepted.

        Args:
            text: Raw OCR text to scan.

        Returns:
            :class:`~ocr_manga_title.schemas.ExtractedTitle` with ``confidence=0.9``
            if a code is found, otherwise ``confidence=0.0``.

        """
        isbn13_match = self.ISBN_13_PATTERN.search(text)
        if isbn13_match:
            normalized = self.normalize_isbn(isbn13_match.group())
            if self._validate_isbn13(normalized):
                return ExtractedTitle(
                    code=normalized,
                    confidence=0.9,
                    source_method="rules",
                )

        isbn10_match = self.ISBN_10_PATTERN.search(text)
        if isbn10_match:
            normalized = self.normalize_isbn(isbn10_match.group())
            if self._validate_isbn10(normalized):
                return ExtractedTitle(
                    code=normalized,
                    confidence=0.9,
                    source_method="rules",
                )

        return ExtractedTitle(confidence=0.0, source_method="rules")

    def augment(self, existing: ExtractedTitle, text: str) -> ExtractedTitle:
        """Supplement an LLM-extracted title with rule-based data.

        Fills in a missing ``code`` from ISBN regex matches, normalizes
        title strings, and updates ``source_method`` to ``"llm+rules"`` when
        both sources contributed.

        Args:
            existing: Previously extracted title (typically from LLM).
            text: Original raw OCR text.

        Returns:
            New :class:`~ocr_manga_title.schemas.ExtractedTitle` with augmented fields.

        """
        rule_result = self.match(text)

        code = existing.code
        source_method = existing.source_method

        if code is None and rule_result.code is not None:
            code = rule_result.code
            if source_method and "llm" in source_method:
                source_method = "llm+rules"
            else:
                source_method = "rules"

        title_en = (
            self.normalize_title(existing.title_en)
            if existing.title_en
            else existing.title_en
        )
        title_ja = (
            self.normalize_title(existing.title_ja)
            if existing.title_ja
            else existing.title_ja
        )

        return ExtractedTitle(
            title_en=title_en,
            title_ja=title_ja,
            code=code,
            confidence=existing.confidence,
            source_model=existing.source_model,
            source_method=source_method,
        )

    @staticmethod
    def normalize_title(title: str) -> str:
        """Clean a title string: NFC normalization, whitespace collapse, trailing punctuation removal."""
        title = unicodedata.normalize("NFC", title)
        title = re.sub(r"\s+", " ", title)
        title = title.strip()
        title = re.sub(r"[。、！？!?,.]+$", "", title)
        title = title.strip()
        return title

    @staticmethod
    def normalize_isbn(isbn: str) -> str:
        """Strip ISBN prefixes, hyphens, and spaces; uppercase the result."""
        isbn = isbn.replace("ISBN", "").replace("-", "").replace(" ", "")
        isbn = isbn.strip()
        return isbn.upper()

    @staticmethod
    def _validate_isbn13(isbn: str) -> bool:
        """Verify the ISBN-13 check digit."""
        if len(isbn) != 13:
            return False
        try:
            digits = [int(c) for c in isbn]
        except ValueError:
            return False
        total = sum(d * (1 if i % 2 == 0 else 3) for i, d in enumerate(digits[:12]))
        check = (10 - total % 10) % 10
        return check == digits[12]

    @staticmethod
    def _validate_isbn10(isbn: str) -> bool:
        """Verify the ISBN-10 check digit."""
        if len(isbn) != 10:
            return False
        try:
            digits = [10 if c == "X" else int(c) for c in isbn]
        except ValueError:
            return False
        total = sum(d * (10 - i) for i, d in enumerate(digits[:9]))
        check = (11 - total % 11) % 11
        return check == digits[9]
