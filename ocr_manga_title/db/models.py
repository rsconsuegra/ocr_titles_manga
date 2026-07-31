"""SQLAlchemy ORM models for all database tables."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from ocr_manga_title.db.enums import BatchStatus, CatalogStatus, RunStatus


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all ORM models."""

    pass


class BatchRun(Base):
    """Groups multiple PipelineRuns into a single batch for bulk processing."""

    __tablename__ = "batch_runs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=BatchStatus.PENDING
    )
    total_count: Mapped[int] = mapped_column(Integer, nullable=False)
    completed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    runs: Mapped[list["PipelineRun"]] = relationship(back_populates="batch_run")

    __table_args__ = (Index("ix_batch_runs_status", "status"),)


class PipelineRun(Base):
    """Tracks a single image through the OCR processing pipeline."""

    __tablename__ = "pipeline_runs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    input_image_path: Mapped[str] = mapped_column(String(500), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    source_platform: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=RunStatus.PENDING)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    preprocess_config: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    batch_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("batch_runs.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    ocr_results: Mapped[list["OCRResult"]] = relationship(
        back_populates="pipeline_run", cascade="all, delete-orphan"
    )
    catalog_entries: Mapped[list["CatalogEntry"]] = relationship(
        back_populates="source_run"
    )
    batch_run: Mapped["BatchRun | None"] = relationship(back_populates="runs")

    __table_args__ = (
        Index("ix_pipeline_runs_status", "status"),
        Index("ix_pipeline_runs_created_at", "created_at"),
        Index("ix_pipeline_runs_batch_run_id", "batch_run_id"),
    )


class OCRResult(Base):
    """Stores raw OCR output for a single model run within a pipeline run."""

    __tablename__ = "ocr_results"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    pipeline_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("pipeline_runs.id", ondelete="CASCADE"), nullable=False
    )
    model_name: Mapped[str] = mapped_column(String(50), nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    processing_time_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    blocks: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    pipeline_run: Mapped["PipelineRun"] = relationship(back_populates="ocr_results")
    post_processing_results: Mapped[list["PostProcessingResult"]] = relationship(
        back_populates="ocr_result", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_ocr_results_pipeline_run_id", "pipeline_run_id"),)


class PostProcessingResult(Base):
    """Stores LLM/rule-extracted title metadata derived from an OCR result."""

    __tablename__ = "post_processing_results"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    ocr_result_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ocr_results.id", ondelete="CASCADE"), nullable=False
    )
    prompt_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("prompt_versions.id"), nullable=True
    )
    title_en: Mapped[str | None] = mapped_column(String(500), nullable=True)
    title_ja: Mapped[str | None] = mapped_column(String(500), nullable=True)
    code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    processing_type: Mapped[str] = mapped_column(String(20), nullable=False)
    system_prompt_used: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_prompt_used: Mapped[str | None] = mapped_column(Text, nullable=True)
    temperature_used: Mapped[float | None] = mapped_column(Float, nullable=True)
    raw_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    ocr_result: Mapped["OCRResult"] = relationship(
        back_populates="post_processing_results"
    )


class PromptVersion(Base):
    """Versioned prompt template used for LLM-based title extraction."""

    __tablename__ = "prompt_versions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    prompt_type: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    agenta_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    tags: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class CatalogEntry(Base):
    """A deduplicated manga title entry in the master catalog."""

    __tablename__ = "catalog_entries"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    title_en: Mapped[str | None] = mapped_column(String(500), nullable=True)
    title_ja: Mapped[str | None] = mapped_column(String(500), nullable=True)
    code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("pipeline_runs.id"), nullable=False
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=CatalogStatus.NEEDS_REVIEW)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(nullable=True)

    source_run: Mapped["PipelineRun"] = relationship(back_populates="catalog_entries")

    __table_args__ = (
        Index("ix_catalog_entries_code", "code"),
        Index("ix_catalog_entries_status", "status"),
    )


class PipelineProfile(Base):
    """Named, reusable pipeline configuration (preprocessing + OCR + LLM)."""

    __tablename__ = "pipeline_profiles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    preprocess_steps: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    ocr_models: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    enable_llm: Mapped[bool] = mapped_column(Boolean, default=False)
    llm_provider: Mapped[str] = mapped_column(String(20), default="openrouter")
    llm_config: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (Index("ix_pipeline_profiles_is_default", "is_default"),)


class ModelConfig(Base):
    """Per-OCR-model runtime configuration persisted in the database."""

    __tablename__ = "model_configs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    model_name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    parameters: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    language_hint: Mapped[str | None] = mapped_column(String(50), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )


class ImageCache(Base):
    """Content-addressable cache for preprocessed images and OCR results."""

    __tablename__ = "image_cache"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    image_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    config_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    cache_type: Mapped[str] = mapped_column(String(20), nullable=False)
    result_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    result_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(nullable=False)

    __table_args__ = (
        Index(
            "uq_image_cache_lookup",
            "image_hash",
            "config_hash",
            "cache_type",
            unique=True,
        ),
        Index("ix_image_cache_expires_at", "expires_at"),
    )


class ApiCredential(Base):
    """Encrypted API key storage for external services (e.g. OpenRouter)."""

    __tablename__ = "api_credentials"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    service_name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    encrypted_api_key: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )
