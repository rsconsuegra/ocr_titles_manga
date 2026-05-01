"""Settings API routes — credentials management and Ollama configuration."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ocr_manga_title.api.dependencies import get_db
from ocr_manga_title.services import credentials as cred
from ocr_manga_title.services.config_live import (
    get_ollama_base_url,
    get_ollama_default_model,
    get_ollama_default_vision_model,
    ping_ollama,
    write_ollama_base_url,
    write_ollama_models,
)
from ocr_manga_title.services.ollama import (
    is_ollama_configured,
    list_models,
    list_vision_models,
)
from ocr_manga_title.settings import OPENROUTER_API_KEY

router = APIRouter()

_ALLOWED_SERVICES = {"openrouter", "ollama"}


async def _validate_service(service: str = Path()) -> str:
    if service not in _ALLOWED_SERVICES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown service: {service}")
    return service


class OllamaUrlRequest(BaseModel):
    """Request body for updating the Ollama base URL and default models."""

    base_url: str
    default_model: str | None = None
    default_vision_model: str | None = None


class OllamaUrlResponse(BaseModel):
    """Response containing Ollama connection info and available models."""

    base_url: str
    default_model: str
    default_vision_model: str
    available_llm_models: list[dict[str, Any]]
    available_vision_models: list[dict[str, Any]]
    validated: bool
    message: str


class OllamaSettingsResponse(BaseModel):
    """Current Ollama configuration and available models."""

    base_url: str
    configured: bool
    default_model: str
    default_vision_model: str
    available_llm_models: list[dict[str, Any]]
    available_vision_models: list[dict[str, Any]]


class ApiKeyRequest(BaseModel):
    """Request body for submitting an API key."""

    api_key: str


class ApiKeyResponse(BaseModel):
    """Response with credential status information for a service."""

    service: str
    has_key: bool
    masked_key: str | None
    source: str | None
    is_active: bool


class ValidateResponse(BaseModel):
    """Response indicating whether a credential is valid."""

    valid: bool
    message: str


class CredentialDeleteResponse(BaseModel):
    """Response confirming credential deactivation."""

    deactivated: bool


async def _fetch_model_lists() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not is_ollama_configured():
        return [], []
    try:
        llm_models = await list_models()
        vision_models = await list_vision_models()
    except Exception:
        llm_models = []
        vision_models = []
    llm_list = [
        {
            "name": m.get("name", ""),
            "parameter_size": m.get("details", {}).get("parameter_size", ""),
            "quantization": m.get("details", {}).get("quantization", ""),
        }
        for m in llm_models
    ]
    vision_list = [
        {"name": m.get("name", ""), "size": m.get("size", 0)}
        for m in vision_models
    ]
    return llm_list, vision_list


@router.get("/ollama", response_model=OllamaSettingsResponse)
async def get_ollama_settings() -> OllamaSettingsResponse:
    """Retrieve current Ollama configuration and available models."""
    llm_list, vision_list = await _fetch_model_lists()
    return OllamaSettingsResponse(
        base_url=get_ollama_base_url(),
        configured=is_ollama_configured(),
        default_model=get_ollama_default_model(),
        default_vision_model=get_ollama_default_vision_model(),
        available_llm_models=llm_list,
        available_vision_models=vision_list,
    )


@router.put("/ollama", response_model=OllamaUrlResponse)
async def update_ollama_url(req: OllamaUrlRequest) -> OllamaUrlResponse:
    """Update the Ollama base URL and optional default models."""
    url = req.base_url.strip().rstrip("/")
    write_ollama_base_url(url)

    if req.default_model is not None or req.default_vision_model is not None:
        write_ollama_models(
            default_model=req.default_model,
            default_vision_model=req.default_vision_model,
        )

    ok, msg = await ping_ollama(url)
    llm_list, vision_list = await _fetch_model_lists()
    return OllamaUrlResponse(
        base_url=url,
        default_model=get_ollama_default_model(),
        default_vision_model=get_ollama_default_vision_model(),
        available_llm_models=llm_list,
        available_vision_models=vision_list,
        validated=ok,
        message=msg,
    )


@router.post("/ollama/ping", response_model=OllamaUrlResponse)
async def ping_ollama_endpoint(req: OllamaUrlRequest) -> OllamaUrlResponse:
    """Test connectivity to an Ollama instance and list its models."""
    url = req.base_url.strip().rstrip("/")
    ok, msg = await ping_ollama(url)
    llm_list: list[dict[str, Any]] = []
    vision_list: list[dict[str, Any]] = []
    if ok:
        llm_list, vision_list = await _fetch_model_lists()
    return OllamaUrlResponse(
        base_url=url,
        default_model=get_ollama_default_model(),
        default_vision_model=get_ollama_default_vision_model(),
        available_llm_models=llm_list,
        available_vision_models=vision_list,
        validated=ok,
        message=msg,
    )


@router.get("/credentials/{service}", response_model=ApiKeyResponse)
async def get_credential(service: str = Depends(_validate_service), db: AsyncSession = Depends(get_db)) -> ApiKeyResponse:
    """Retrieve credential status for a given service."""
    env_default = OPENROUTER_API_KEY if service == "openrouter" else ""
    info = await cred.get_credential_info(db, service, env_default)
    return ApiKeyResponse(**info)


@router.put("/credentials/{service}", response_model=ValidateResponse)
async def update_credential(req: ApiKeyRequest, service: str = Depends(_validate_service), db: AsyncSession = Depends(get_db)) -> ValidateResponse:
    """Store or update an API key for a service."""
    if service == "openrouter":
        valid, msg = await cred.validate_openrouter_key(req.api_key)
        if not valid:
            return ValidateResponse(valid=False, message=msg)

    await cred.store_key(db, service, req.api_key)
    await db.commit()
    return ValidateResponse(valid=True, message="Key saved successfully")


@router.delete("/credentials/{service}", response_model=CredentialDeleteResponse)
async def delete_credential(service: str = Depends(_validate_service), db: AsyncSession = Depends(get_db)) -> CredentialDeleteResponse:
    """Deactivate the stored API key for a service."""
    deactivated = await cred.deactivate_key(db, service)
    await db.commit()
    return CredentialDeleteResponse(deactivated=deactivated)


@router.post("/credentials/{service}/validate", response_model=ValidateResponse)
async def validate_credential(req: ApiKeyRequest, service: str = Depends(_validate_service)) -> ValidateResponse:
    """Validate an API key without storing it."""
    if service == "openrouter":
        valid, msg = await cred.validate_openrouter_key(req.api_key)
        return ValidateResponse(valid=valid, message=msg)
    return ValidateResponse(valid=False, message=f"No validator for service '{service}'")
