"""Config snapshot helpers for pipeline profiles."""

from typing import Any

from ocr_manga_title.db.models import PipelineProfile


def build_run_config_snapshot(profile: PipelineProfile | None) -> dict[str, Any] | None:
    """Build a serialisable config snapshot from a pipeline profile."""
    if profile is None:
        return None
    return {
        "preprocess_steps": profile.preprocess_steps or {},
        "ocr_models": profile.ocr_models or {},
        "enable_llm": profile.enable_llm,
        "llm_provider": profile.llm_provider,
        "llm_config": profile.llm_config,
    }
