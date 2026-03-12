from typing import List
from uuid import UUID
import uuid as uuid_lib
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.api.deps import get_current_user_organization
from app.models.video import Video, VideoStatus
from app.schemas.video import (
    VideoResponse,
    VideoWithTranscript,
)
from app.services.storage import storage_service
from app.tasks.background import process_video_background


router = APIRouter(prefix="/videos", tags=["videos"])


@router.post("/upload", response_model=VideoResponse)
async def upload_video(
    file: UploadFile = File(...),
    title: str = Form(None),
    db: AsyncSession = Depends(get_db),
    auth: tuple = Depends(get_current_user_organization),
):
    """Upload a video file directly."""
    user, organization, membership = auth

    # Validate file type
    allowed_types = ["video/mp4", "video/quicktime", "video/x-msvideo", "video/x-matroska", "video/webm"]
    if file.content_type and file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_types)}",
        )

    # Generate storage key
    file_extension = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "mp4"
    storage_key = f"videos/{uuid_lib.uuid4()}.{file_extension}"

    # Read file content and save
    content = await file.read()
    file_size = len(content)

    # Save to local storage
    storage_service.save_uploaded_file(content, storage_key)

    # Create video record
    video = Video(
        organization_id=organization.id,
        uploaded_by=user.id,
        title=title or file.filename,
        original_filename=file.filename,
        storage_key=storage_key,
        file_size_bytes=file_size,
        mime_type=file.content_type,
        status=VideoStatus.UPLOADED,
    )
    db.add(video)
    await db.commit()
    await db.refresh(video)

    # Start background processing
    process_video_background(str(video.id))

    return VideoResponse.model_validate(video)


@router.get("", response_model=List[VideoResponse])
async def list_videos(
    db: AsyncSession = Depends(get_db),
    auth: tuple = Depends(get_current_user_organization),
    skip: int = 0,
    limit: int = 50,
):
    """List all videos in the organization."""
    user, organization, membership = auth

    result = await db.execute(
        select(Video)
        .where(Video.organization_id == organization.id)
        .order_by(Video.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    videos = result.scalars().all()

    return [VideoResponse.model_validate(v) for v in videos]


@router.get("/{video_id}", response_model=VideoWithTranscript)
async def get_video(
    video_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth: tuple = Depends(get_current_user_organization),
):
    """Get a specific video with its transcript."""
    user, organization, membership = auth

    result = await db.execute(
        select(Video)
        .options(selectinload(Video.transcript))
        .where(
            Video.id == video_id,
            Video.organization_id == organization.id,
        )
    )
    video = result.scalar_one_or_none()

    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found",
        )

    return VideoWithTranscript.model_validate(video)


@router.delete("/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_video(
    video_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth: tuple = Depends(get_current_user_organization),
):
    """Delete a video and its transcript."""
    user, organization, membership = auth

    result = await db.execute(
        select(Video).where(
            Video.id == video_id,
            Video.organization_id == organization.id,
        )
    )
    video = result.scalar_one_or_none()

    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found",
        )

    # Delete from storage
    storage_service.delete_file(video.storage_key)

    # Delete from database
    await db.delete(video)
    await db.commit()
