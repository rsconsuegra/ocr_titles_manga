import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ocr_manga_title.api.dependencies import get_db
from ocr_manga_title.api.schemas.pipeline import PaginatedResponse
from ocr_manga_title.api.schemas.profiles import (
    ProfileCreateRequest,
    ProfileResponse,
    ProfileUpdateRequest,
)
from ocr_manga_title.db.crud import (
    count_profiles,
    create_profile,
    delete_profile,
    get_profile,
    list_profiles,
    update_profile,
)

router = APIRouter()


@router.post("", response_model=ProfileResponse, status_code=201)
async def create_profile_endpoint(
    body: ProfileCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        profile = await create_profile(
            db,
            name=body.name,
            description=body.description,
            preprocess_steps=body.preprocess_steps,
            ocr_models=body.ocr_models,
            enable_llm=body.enable_llm,
            is_default=body.is_default,
        )
    except Exception as e:
        if "unique" in str(e).lower() or "duplicate" in str(e).lower():
            raise HTTPException(
                status_code=409, detail=f"Profile '{body.name}' already exists"
            ) from e
        raise
    return ProfileResponse.model_validate(profile)


@router.get("", response_model=PaginatedResponse[ProfileResponse])
async def list_profiles_endpoint(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    profiles = await list_profiles(db, limit=limit, offset=offset)
    total = await count_profiles(db)
    return PaginatedResponse(
        items=[ProfileResponse.model_validate(p) for p in profiles],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{profile_id}", response_model=ProfileResponse)
async def get_profile_endpoint(
    profile_id: uuid.UUID, db: AsyncSession = Depends(get_db)
):
    profile = await get_profile(db, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return ProfileResponse.model_validate(profile)


@router.put("/{profile_id}", response_model=ProfileResponse)
async def update_profile_endpoint(
    profile_id: uuid.UUID,
    body: ProfileUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    kwargs = body.model_dump(exclude_none=True)
    profile = await update_profile(db, profile_id, **kwargs)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return ProfileResponse.model_validate(profile)


@router.delete("/{profile_id}", status_code=204)
async def delete_profile_endpoint(
    profile_id: uuid.UUID, db: AsyncSession = Depends(get_db)
):
    deleted = await delete_profile(db, profile_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Profile not found")


@router.post("/{profile_id}/set-default", response_model=ProfileResponse)
async def set_default_profile_endpoint(
    profile_id: uuid.UUID, db: AsyncSession = Depends(get_db)
):
    profile = await update_profile(db, profile_id, is_default=True)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return ProfileResponse.model_validate(profile)
