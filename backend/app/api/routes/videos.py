from typing import List
from uuid import UUID
import uuid as uuid_lib
import tempfile
import os
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request
from fastapi.responses import StreamingResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.config import settings
from app.api.deps import get_current_user_organization, get_user_organization_from_token_or_query
from app.models.video import Video, VideoStatus
from app.schemas.video import (
    VideoResponse,
    VideoWithTranscript,
)
from app.services.usage import usage_service
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

    # Check monthly quota before upload
    can_transcribe, quota_error = await usage_service.check_can_transcribe_async(
        db, organization.id
    )
    if not can_transcribe:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=quota_error,
        )

    # Validate file type
    allowed_types = ["video/mp4", "video/quicktime", "video/x-msvideo", "video/x-matroska", "video/webm"]
    if file.content_type and file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_types)}",
        )

    # Check file size before reading entire file
    max_size = settings.max_upload_size_mb * 1024 * 1024  # Convert to bytes

    # Read in chunks to validate size without loading entire file
    chunks = []
    total_size = 0
    chunk_size = 1024 * 1024  # 1MB chunks

    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        total_size += len(chunk)
        if total_size > max_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum size is {settings.max_upload_size_mb}MB",
            )
        chunks.append(chunk)

    content = b"".join(chunks)
    file_size = total_size

    # Save to temporary file (required for FFmpeg processing)
    file_extension = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "mp4"
    temp_dir = tempfile.gettempdir()
    temp_filename = f"{uuid_lib.uuid4()}.{file_extension}"
    temp_path = os.path.join(temp_dir, temp_filename)

    # Write video to temp file
    with open(temp_path, "wb") as f:
        f.write(content)

    # Create video record (storage_key now points to temp file)
    video = Video(
        organization_id=organization.id,
        uploaded_by=user.id,
        title=title or file.filename,
        original_filename=file.filename,
        storage_key=temp_path,  # Temporary path, will be deleted after processing
        file_size_bytes=file_size,
        mime_type=file.content_type,
        status=VideoStatus.UPLOADED,
    )
    db.add(video)
    await db.commit()
    await db.refresh(video)

    # Start background processing (will delete temp file after transcription)
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

    # Validate pagination limits
    if limit > 100:
        limit = 100
    if skip < 0:
        skip = 0

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
    """Delete a video record and its transcript."""
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

    # Try to delete temp file if it still exists (usually already deleted after transcription)
    if video.storage_key and os.path.exists(video.storage_key):
        try:
            os.remove(video.storage_key)
        except OSError:
            pass

    # Delete from database
    await db.delete(video)
    await db.commit()


@router.get("/{video_id}/stream")
async def stream_video(
    video_id: UUID,
    request: Request,
    token: str = None,
    db: AsyncSession = Depends(get_db),
):
    """Video streaming is not available - videos are processed in memory and deleted.

    This endpoint is kept for API compatibility but returns 410 Gone.
    """
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Video files are not stored. Only transcripts are persisted.",
    )
