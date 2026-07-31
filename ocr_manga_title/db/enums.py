"""Canonical status enums for pipeline runs, batch runs, and catalog entries."""

from enum import StrEnum


class RunStatus(StrEnum):
    """Status values for pipeline runs."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BatchStatus(StrEnum):
    """Status values for batch runs."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL_FAILURE = "partial_failure"


class CatalogStatus(StrEnum):
    """Status values for catalog entries."""

    AUTO_CONFIRMED = "auto_confirmed"
    NEEDS_REVIEW = "needs_review"
    REJECTED = "rejected"
