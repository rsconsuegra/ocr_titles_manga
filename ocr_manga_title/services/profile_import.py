from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ocr_manga_title.engine.registry import MODEL_REGISTRY
from ocr_manga_title.preprocess.registry import STEP_REGISTRY

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class ValidationMessage:
    field: str
    message: str


@dataclass
class ProfileValidationResult:
    warnings: list[ValidationMessage] = field(default_factory=list)
    errors: list[ValidationMessage] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0


def validate_profile_data(profile_data: dict) -> ProfileValidationResult:
    result = ProfileValidationResult()

    name = profile_data.get("name", "").strip()
    if not name:
        result.errors.append(ValidationMessage(field="name", message="Profile name is required"))

    pp_steps = profile_data.get("preprocess_steps") or {}
    _validate_step_configs(pp_steps, "preprocess_steps", result)

    ocr_models = profile_data.get("ocr_models") or {}
    _validate_model_configs(ocr_models, "ocr_models", result)

    llm_provider = profile_data.get("llm_provider", "openrouter")
    if llm_provider not in ("openrouter", "ollama"):
        result.errors.append(
            ValidationMessage(
                field="llm_provider",
                message=f"Unknown LLM provider '{llm_provider}'. Must be 'openrouter' or 'ollama'",
            )
        )

    llm_config = profile_data.get("llm_config")
    if llm_config is not None:
        if not isinstance(llm_config, dict):
            result.errors.append(
                ValidationMessage(field="llm_config", message="llm_config must be a dict")
            )
        else:
            temp = llm_config.get("temperature")
            if temp is not None:
                try:
                    t = float(temp)
                    if not (0.0 <= t <= 2.0):
                        result.errors.append(
                            ValidationMessage(
                                field="llm_config.temperature",
                                message=f"Temperature {t} out of range [0.0, 2.0]",
                            )
                        )
                except (TypeError, ValueError):
                    result.errors.append(
                        ValidationMessage(
                            field="llm_config.temperature",
                            message="Temperature must be a number",
                        )
                    )
            max_chars = llm_config.get("max_ocr_chars")
            if max_chars is not None:
                try:
                    v = int(max_chars)
                    if v < 0:
                        result.errors.append(
                            ValidationMessage(
                                field="llm_config.max_ocr_chars",
                                message="max_ocr_chars must be >= 0",
                            )
                        )
                except (TypeError, ValueError):
                    result.errors.append(
                        ValidationMessage(
                            field="llm_config.max_ocr_chars",
                            message="max_ocr_chars must be an integer",
                        )
                    )
            llm_model = llm_config.get("llm_model")
            if llm_model is not None and not isinstance(llm_model, str):
                result.errors.append(
                    ValidationMessage(
                        field="llm_config.llm_model",
                        message="llm_model must be a string",
                    )
                )
            reasoning_enabled = llm_config.get("reasoning_enabled")
            if reasoning_enabled is not None and not isinstance(reasoning_enabled, bool):
                result.errors.append(
                    ValidationMessage(
                        field="llm_config.reasoning_enabled",
                        message="reasoning_enabled must be a boolean",
                    )
                )

    return result


def _validate_step_configs(
    steps: dict, path_prefix: str, result: ProfileValidationResult
) -> None:
    for step_name, step_config in steps.items():
        if not isinstance(step_config, dict):
            result.errors.append(
                ValidationMessage(
                    field=f"{path_prefix}.{step_name}",
                    message="Step config must be a dict",
                )
            )
            continue

        descriptor = STEP_REGISTRY.get(step_name)
        if descriptor is None:
            result.warnings.append(
                ValidationMessage(
                    field=f"{path_prefix}.{step_name}",
                    message=f"Unknown preprocessing step '{step_name}'. Valid: {sorted(STEP_REGISTRY.keys())}",
                )
            )
            continue

        _validate_params(step_config, descriptor.params, f"{path_prefix}.{step_name}", result)


def _validate_model_configs(
    models: dict, path_prefix: str, result: ProfileValidationResult
) -> None:
    for model_name, model_config in models.items():
        if not isinstance(model_config, dict):
            result.errors.append(
                ValidationMessage(
                    field=f"{path_prefix}.{model_name}",
                    message="Model config must be a dict",
                )
            )
            continue

        descriptor = MODEL_REGISTRY.get(model_name)
        if descriptor is None:
            result.warnings.append(
                ValidationMessage(
                    field=f"{path_prefix}.{model_name}",
                    message=f"Unknown OCR model '{model_name}'. Valid: {sorted(MODEL_REGISTRY.keys())}",
                )
            )
            continue

        _validate_params(model_config, descriptor.params, f"{path_prefix}.{model_name}", result)


def _validate_params(
    config: dict,
    param_descriptors: list,
    path: str,
    result: ProfileValidationResult,
) -> None:
    param_map = {p.name: p for p in param_descriptors}

    for key, value in config.items():
        if key in ("enabled",):
            continue

        desc = param_map.get(key)
        if desc is None:
            result.warnings.append(
                ValidationMessage(
                    field=f"{path}.{key}",
                    message=f"Unknown parameter '{key}'",
                )
            )
            continue

        if desc.options is not None and desc.type in ("select", "multiselect"):
            if desc.type == "multiselect":
                if isinstance(value, list):
                    for v in value:
                        if v not in desc.options:
                            result.errors.append(
                                ValidationMessage(
                                    field=f"{path}.{key}",
                                    message=f"Value '{v}' not in allowed options: {desc.options}",
                                )
                            )
                elif isinstance(value, str) and value not in desc.options:
                    result.errors.append(
                        ValidationMessage(
                            field=f"{path}.{key}",
                            message=f"Value '{value}' not in allowed options: {desc.options}",
                        )
                    )
            elif isinstance(value, str) and value not in desc.options:
                result.errors.append(
                    ValidationMessage(
                        field=f"{path}.{key}",
                        message=f"Value '{value}' not in allowed options: {desc.options}",
                    )
                )

        if desc.type == "number" and isinstance(value, (int, float)):
            if desc.min is not None and value < desc.min:
                result.errors.append(
                    ValidationMessage(
                        field=f"{path}.{key}",
                        message=f"Value {value} below minimum {desc.min}",
                    )
                )
            if desc.max is not None and value > desc.max:
                result.errors.append(
                    ValidationMessage(
                        field=f"{path}.{key}",
                        message=f"Value {value} above maximum {desc.max}",
                    )
                )


async def resolve_name_conflict(session: "AsyncSession", name: str) -> str:
    from ocr_manga_title.db.crud import get_profile_by_name

    candidate = name
    suffix = 1
    while await get_profile_by_name(session, candidate) is not None:
        suffix += 1
        candidate = f"{name} ({suffix})"
    return candidate
