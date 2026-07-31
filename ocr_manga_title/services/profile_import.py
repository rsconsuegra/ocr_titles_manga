"""Profile validation and import conflict resolution."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ocr_manga_title.engine.registry import MODEL_REGISTRY
from ocr_manga_title.preprocess.registry import STEP_REGISTRY, ParamDescriptor

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class ValidationMessage:
    """A single validation message tied to a specific field."""

    field: str
    message: str


@dataclass
class ProfileValidationResult:
    """Aggregated validation outcome for profile data."""

    warnings: list[ValidationMessage] = field(default_factory=list)
    errors: list[ValidationMessage] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """Return True if there are no validation errors."""
        return len(self.errors) == 0


def validate_profile_data(profile_data: dict[str, Any]) -> ProfileValidationResult:
    """Validate raw profile data and return warnings and errors."""
    result = ProfileValidationResult()

    name = profile_data.get("name", "").strip()
    if not name:
        result.errors.append(
            ValidationMessage(field="name", message="Profile name is required")
        )

    _validate_step_configs(
        profile_data.get("preprocess_steps") or {},
        "preprocess_steps",
        result,
    )
    _validate_model_configs(
        profile_data.get("ocr_models") or {},
        "ocr_models",
        result,
    )

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
        _validate_llm_config(llm_config, result)

    return result


def _validate_llm_config(llm_config: Any, result: ProfileValidationResult) -> None:
    if not isinstance(llm_config, dict):
        result.errors.append(
            ValidationMessage(field="llm_config", message="llm_config must be a dict")
        )
        return

    _validate_numeric_field(
        llm_config,
        "temperature",
        result,
        coerce=float,
        min_val=0.0,
        max_val=2.0,
        type_error="Temperature must be a number",
    )
    _validate_numeric_field(
        llm_config,
        "max_ocr_chars",
        result,
        coerce=int,
        min_val=0,
        max_val=None,
        type_error="max_ocr_chars must be an integer",
    )
    _validate_type_field(
        llm_config,
        "llm_model",
        str,
        result,
        type_error="llm_model must be a string",
    )
    _validate_type_field(
        llm_config,
        "reasoning_enabled",
        bool,
        result,
        type_error="reasoning_enabled must be a boolean",
    )


def _validate_numeric_field(
    config: dict[str, Any],
    key: str,
    result: ProfileValidationResult,
    *,
    coerce: type,
    min_val: float | None,
    max_val: float | None,
    type_error: str,
) -> None:
    raw = config.get(key)
    if raw is None:
        return
    try:
        v = coerce(raw)
    except (TypeError, ValueError):
        result.errors.append(
            ValidationMessage(field=f"llm_config.{key}", message=type_error)
        )
        return
    if min_val is not None and v < min_val:
        result.errors.append(
            ValidationMessage(
                field=f"llm_config.{key}",
                message=f"{key} {v} is below minimum {min_val}",
            )
        )
    if max_val is not None and v > max_val:
        result.errors.append(
            ValidationMessage(
                field=f"llm_config.{key}",
                message=f"{key} {v} is above maximum {max_val}",
            )
        )


def _validate_type_field(
    config: dict[str, Any],
    key: str,
    expected: type,
    result: ProfileValidationResult,
    *,
    type_error: str,
) -> None:
    raw = config.get(key)
    if raw is not None and not isinstance(raw, expected):
        result.errors.append(
            ValidationMessage(field=f"llm_config.{key}", message=type_error)
        )


def _validate_step_configs(
    steps: dict[str, Any], path_prefix: str, result: ProfileValidationResult
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

        _validate_params(
            step_config, descriptor.params, f"{path_prefix}.{step_name}", result
        )


def _validate_model_configs(
    models: dict[str, Any], path_prefix: str, result: ProfileValidationResult
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

        _validate_params(
            model_config, descriptor.params, f"{path_prefix}.{model_name}", result
        )


def _validate_select(
    desc: ParamDescriptor,
    value: Any,
    field_path: str,
    result: ProfileValidationResult,
) -> None:
    options = desc.options
    if options is None:
        return
    if desc.type == "multiselect" and isinstance(value, list):
        for v in value:
            if v not in options:
                result.errors.append(
                    ValidationMessage(
                        field=field_path,
                        message=f"Value '{v}' not in allowed options: {options}",
                    )
                )
        return
    if isinstance(value, str) and value not in options:
        result.errors.append(
            ValidationMessage(
                field=field_path,
                message=f"Value '{value}' not in allowed options: {options}",
            )
        )


def _validate_number(
    desc: ParamDescriptor,
    value: Any,
    field_path: str,
    result: ProfileValidationResult,
) -> None:
    if not isinstance(value, (int, float)):
        return
    if desc.min is not None and value < desc.min:
        result.errors.append(
            ValidationMessage(
                field=field_path,
                message=f"Value {value} below minimum {desc.min}",
            )
        )
    if desc.max is not None and value > desc.max:
        result.errors.append(
            ValidationMessage(
                field=field_path,
                message=f"Value {value} above maximum {desc.max}",
            )
        )


_TypeValidator = Callable[[ParamDescriptor, Any, str, ProfileValidationResult], None]

_TYPE_VALIDATORS: dict[str, _TypeValidator] = {}


def _register(*types: str) -> Callable[[_TypeValidator], _TypeValidator]:
    def decorator(fn: _TypeValidator) -> _TypeValidator:
        for t in types:
            _TYPE_VALIDATORS[t] = fn
        return fn

    return decorator


_register("select", "multiselect")(_validate_select)
_register("number")(_validate_number)


def _validate_params(
    config: dict[str, Any],
    param_descriptors: list[Any],
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

        validator = _TYPE_VALIDATORS.get(desc.type)
        if validator is not None:
            validator(desc, value, f"{path}.{key}", result)


async def resolve_name_conflict(session: AsyncSession, name: str) -> str:
    """Append a numeric suffix to *name* until it is unique."""
    from ocr_manga_title.db.crud import get_profile_by_name

    candidate = name
    suffix = 1
    while await get_profile_by_name(session, candidate) is not None:
        suffix += 1
        candidate = f"{name} ({suffix})"
    return candidate
