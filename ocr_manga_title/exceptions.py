"""Custom exception hierarchy for the manga OCR pipeline."""


class MangaOCRError(Exception):
    """Base exception for all manga OCR errors."""


class ConfigurationError(MangaOCRError):
    """Raised when a configuration file is missing, malformed, or contains invalid values.

    Attributes:
        field_name: Optional name of the offending configuration field.
        file_path: Optional path of the configuration file that caused the error.

    """

    def __init__(
        self,
        message: str = "",
        field_name: str | None = None,
        file_path: str | None = None,
    ):
        self.field_name = field_name
        self.file_path = file_path
        parts = []
        if file_path:
            parts.append(f"[{file_path}]")
        if field_name:
            parts.append(f"field '{field_name}'")
        parts.append(message)
        super().__init__(" ".join(parts))


class ModelNotAvailableError(MangaOCRError):
    """Raised when an OCR model's runtime dependency is not installed or accessible."""


class LLMExtractionError(MangaOCRError):
    """Raised when LLM-based title extraction fails unrecoverably."""


class PermanentError(MangaOCRError):
    """Errors that should NOT be retried by the task queue."""
