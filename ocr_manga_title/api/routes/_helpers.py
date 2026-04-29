import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from ocr_manga_title.services.image import save_bytes
from ocr_manga_title.settings import ALLOWED_EXTENSIONS, MAX_FILE_SIZE, MAX_FILES, UPLOAD_DIR

UPLOAD_DIR_PATH = Path(UPLOAD_DIR)


def validate_file_count(files: list[UploadFile]) -> None:
    if len(files) == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least one file required",
        )
    if len(files) > MAX_FILES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum {MAX_FILES} files allowed",
        )


async def validate_and_save_file(file: UploadFile) -> Path:
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid format: {ext}. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large: {file.filename} (max 20MB)",
        )

    UPLOAD_DIR_PATH.mkdir(parents=True, exist_ok=True)
    file_id = uuid.uuid4()
    save_path = UPLOAD_DIR_PATH / f"{file_id}{ext}"
    save_path.write_bytes(content)
    return save_path


async def resolve_profile_snapshot(
    db: AsyncSession, profile_id: uuid.UUID | None
) -> dict | None:
    if profile_id is None:
        return None
    from ocr_manga_title.db.crud import get_profile
    from ocr_manga_title.services.config import build_run_config_snapshot

    profile = await get_profile(db, profile_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )
    return build_run_config_snapshot(profile)


def parse_llm_form_config(
    system_prompt: str,
    user_prompt: str,
    temperature: str,
    max_ocr_chars: str,
) -> dict | None:
    if not (system_prompt or user_prompt or temperature or max_ocr_chars):
        return None
    try:
        temp_val = float(temperature) if temperature else 0.1
        chars_val = int(max_ocr_chars) if max_ocr_chars else 0
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid numeric value for temperature or max_ocr_chars",
        )
    return {
        "system_prompt": system_prompt,
        "user_prompt_template": user_prompt or "{ocr_text}",
        "temperature": temp_val,
        "max_ocr_chars": chars_val,
    }


async def save_uploaded_image(
    file: UploadFile,
) -> tuple[bytes, str]:
    try:
        raw = await file.read()
    except OSError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid image: {e}",
        ) from e
    try:
        tmp_path = save_bytes(raw)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid image: {e}",
        ) from e
    return raw, tmp_path
