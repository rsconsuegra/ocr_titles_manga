"""Encrypted credential storage for external API services.

Uses Fernet symmetric encryption (via ``SERVER_SECRET`` env var) to store
API keys in the database.  At runtime the active key is resolved by checking
the DB first and falling back to the environment variable default.
"""

from __future__ import annotations

import base64
import hashlib
import logging
import uuid

from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ocr_manga_title.db.models import ApiCredential
from ocr_manga_title.settings import SERVER_SECRET

logger = logging.getLogger(__name__)


def _fernet() -> Fernet:
    if not SERVER_SECRET:
        raise RuntimeError("SERVER_SECRET is not configured. Set it in .env.")
    key = hashlib.sha256(SERVER_SECRET.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt_value(plain: str) -> str:
    return _fernet().encrypt(plain.encode()).decode()


def decrypt_value(token: str) -> str:
    return _fernet().decrypt(token.encode()).decode()


def mask_key(key: str) -> str:
    if len(key) <= 8:
        return "****"
    return key[:4] + "*" * (len(key) - 8) + key[-4:]


async def get_active_key(session: AsyncSession, service_name: str, env_default: str) -> str | None:
    """Return the decrypted active API key for *service_name*, or *env_default*."""
    stmt = select(ApiCredential).where(
        ApiCredential.service_name == service_name,
        ApiCredential.is_active.is_(True),
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row:
        try:
            return decrypt_value(row.encrypted_api_key)
        except Exception:
            logger.warning("Failed to decrypt stored key for %s, falling back to env", service_name)
    return env_default or None


async def store_key(session: AsyncSession, service_name: str, api_key: str) -> ApiCredential:
    """Encrypt and upsert an API key for *service_name*."""
    encrypted = encrypt_value(api_key)
    stmt = select(ApiCredential).where(ApiCredential.service_name == service_name)
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row:
        row.encrypted_api_key = encrypted
        row.is_active = True
    else:
        row = ApiCredential(
            id=uuid.uuid4(),
            service_name=service_name,
            encrypted_api_key=encrypted,
            is_active=True,
        )
        session.add(row)
    await session.flush()
    return row


async def deactivate_key(session: AsyncSession, service_name: str) -> bool:
    """Deactivate the stored key (revert to env default)."""
    stmt = select(ApiCredential).where(ApiCredential.service_name == service_name)
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row:
        await session.delete(row)
        await session.flush()
        return True
    return False


async def get_credential_info(session: AsyncSession, service_name: str, env_default: str) -> dict:
    """Return credential status for the UI (masked key, source, active)."""
    stmt = select(ApiCredential).where(
        ApiCredential.service_name == service_name,
        ApiCredential.is_active.is_(True),
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row:
        try:
            decrypted = decrypt_value(row.encrypted_api_key)
            return {
                "service": service_name,
                "has_key": True,
                "masked_key": mask_key(decrypted),
                "source": "database",
                "is_active": True,
            }
        except Exception:
            pass
    has_env = bool(env_default)
    return {
        "service": service_name,
        "has_key": has_env,
        "masked_key": mask_key(env_default) if has_env else None,
        "source": "env" if has_env else None,
        "is_active": False,
    }


async def validate_openrouter_key(api_key: str) -> tuple[bool, str]:
    """Test an OpenRouter API key by making a lightweight models request."""
    import httpx

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://openrouter.ai/api/v1/models",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            if resp.status_code == 200:
                return True, "Key validated successfully"
            if resp.status_code == 401:
                return False, "Invalid API key (401 Unauthorized)"
            return False, f"Unexpected status: {resp.status_code}"
    except Exception as e:
        return False, f"Connection error: {e}"
