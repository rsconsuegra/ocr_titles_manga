import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ocr_manga_title.api.dependencies import get_db
from ocr_manga_title.api.schemas.pipeline import PaginatedResponse
from ocr_manga_title.api.schemas.profiles import (
    ProfileCreateRequest,
    ProfileExportFile,
    ProfileImportResult,
    ProfileResponse,
    ProfileUpdateRequest,
    ProfileValidationWarning,
)
from ocr_manga_title.db.crud import (
    count_profiles,
    create_profile,
    delete_profile,
    get_profile,
    list_profiles,
    update_profile,
)
from ocr_manga_title.schemas import utcnow
from ocr_manga_title.services.profile_import import (
    resolve_name_conflict,
    validate_profile_data,
)

router = APIRouter()


@router.post("", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_profile_endpoint(
    body: ProfileCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> ProfileResponse:
    """Create a new OCR processing profile."""
    try:
        profile = await create_profile(
            db,
            name=body.name,
            description=body.description,
            preprocess_steps=body.preprocess_steps,
            ocr_models=body.ocr_models,
            enable_llm=body.enable_llm,
            llm_provider=body.llm_provider,
            llm_config=body.llm_config,
            is_default=body.is_default,
        )
    except IntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Profile '{body.name}' already exists",
        ) from e
    return ProfileResponse.model_validate(profile)


@router.get("", response_model=PaginatedResponse[ProfileResponse])
async def list_profiles_endpoint(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[ProfileResponse]:
    """List all profiles with pagination."""
    profiles = await list_profiles(db, limit=limit, offset=offset)
    total = await count_profiles(db)
    return PaginatedResponse(
        items=[ProfileResponse.model_validate(p) for p in profiles],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/validate", response_model=ProfileImportResult)
async def validate_import_endpoint(body: ProfileExportFile) -> ProfileImportResult:
    """Validate a profile export payload without importing it."""
    validation = validate_profile_data(body.profile.model_dump())

    return ProfileImportResult(
        warnings=[
            ProfileValidationWarning(field=w.field, message=w.message)
            for w in validation.warnings
        ],
        errors=[
            ProfileValidationWarning(field=e.field, message=e.message)
            for e in validation.errors
        ],
    )


@router.post("/import", response_model=ProfileImportResult)
async def import_profile_endpoint(
    body: ProfileExportFile,
    db: AsyncSession = Depends(get_db),
) -> ProfileImportResult:
    """Import a profile from an exported payload, resolving name conflicts."""
    validation = validate_profile_data(body.profile.model_dump())

    warnings = [
        ProfileValidationWarning(field=w.field, message=w.message)
        for w in validation.warnings
    ]
    errors = [
        ProfileValidationWarning(field=e.field, message=e.message)
        for e in validation.errors
    ]

    if not validation.is_valid:
        return ProfileImportResult(warnings=warnings, errors=errors)

    resolved_name = await resolve_name_conflict(db, body.profile.name)
    if resolved_name != body.profile.name:
        warnings.append(
            ProfileValidationWarning(
                field="name",
                message=f"Name '{body.profile.name}' already exists, renamed to '{resolved_name}'",
            )
        )

    try:
        profile = await create_profile(
            db,
            name=resolved_name,
            description=body.profile.description,
            preprocess_steps=body.profile.preprocess_steps,
            ocr_models=body.profile.ocr_models,
            enable_llm=body.profile.enable_llm,
            llm_provider=body.profile.llm_provider,
            llm_config=body.profile.llm_config,
            is_default=False,
        )
    except IntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Profile name conflict after resolution: {resolved_name}",
        ) from e

    return ProfileImportResult(
        profile=ProfileResponse.model_validate(profile),
        warnings=warnings,
        errors=[],
    )


@router.get("/{profile_id}", response_model=ProfileResponse)
async def get_profile_endpoint(
    profile_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> ProfileResponse:
    """Retrieve a single profile by ID."""
    profile = await get_profile(db, profile_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return ProfileResponse.model_validate(profile)


@router.put("/{profile_id}", response_model=ProfileResponse)
async def update_profile_endpoint(
    profile_id: uuid.UUID,
    body: ProfileUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> ProfileResponse:
    """Update fields on an existing profile."""
    kwargs = body.model_dump(exclude_none=True)
    profile = await update_profile(db, profile_id, **kwargs)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return ProfileResponse.model_validate(profile)


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile_endpoint(
    profile_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> None:
    """Delete a profile by ID."""
    deleted = await delete_profile(db, profile_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")


@router.post("/{profile_id}/set-default", response_model=ProfileResponse)
async def set_default_profile_endpoint(
    profile_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> ProfileResponse:
    """Set a profile as the default."""
    profile = await update_profile(db, profile_id, is_default=True)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return ProfileResponse.model_validate(profile)


@router.get("/{profile_id}/export")
async def export_profile_endpoint(
    profile_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    """Export a profile as a downloadable JSON file."""
    profile = await get_profile(db, profile_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    export = ProfileExportFile(
        exported_at=utcnow(),
        profile=ProfileCreateRequest(
            name=profile.name,
            description=profile.description,
            preprocess_steps=profile.preprocess_steps,
            ocr_models=profile.ocr_models,
            enable_llm=profile.enable_llm,
            llm_provider=profile.llm_provider,
            llm_config=profile.llm_config,
            is_default=False,
        ),
    )

    filename = f"{profile.name.replace(' ', '_').lower()}_profile.json"
    content = export.model_dump_json(indent=2)

    return JSONResponse(
        content=json.loads(content),
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
