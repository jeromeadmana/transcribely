import asyncio
import json
from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.config import settings
from app.api.deps import get_current_user_organization, get_user_organization_from_token_or_query
from app.models.video import Video, Transcript, VideoStatus
from app.schemas.video import TranscriptResponse, TranscriptUpdate, ProgressEvent
from app.services.translation import translation_service, SUPPORTED_LANGUAGES


router = APIRouter(prefix="/transcripts", tags=["transcripts"])


@router.get("/{video_id}", response_model=TranscriptResponse)
async def get_transcript(
    video_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth: tuple = Depends(get_current_user_organization),
):
    """Get transcript for a video."""
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

    if not video.transcript:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transcript not found",
        )

    return TranscriptResponse.model_validate(video.transcript)


@router.patch("/{video_id}", response_model=TranscriptResponse)
async def update_transcript(
    video_id: UUID,
    update_data: TranscriptUpdate,
    db: AsyncSession = Depends(get_db),
    auth: tuple = Depends(get_current_user_organization),
):
    """Update a transcript."""
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

    if not video.transcript:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transcript not found",
        )

    # Update fields
    if update_data.full_text is not None:
        video.transcript.full_text = update_data.full_text
        video.transcript.word_count = len(update_data.full_text.split())

    if update_data.segments is not None:
        video.transcript.segments = [s.model_dump() for s in update_data.segments]

    await db.commit()
    await db.refresh(video.transcript)

    return TranscriptResponse.model_validate(video.transcript)


@router.get("/{video_id}/progress")
async def get_progress(
    video_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth: tuple = Depends(get_current_user_organization),
):
    """Get real-time progress updates via Server-Sent Events."""
    user, organization, membership = auth

    # Verify video exists and belongs to organization
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

    async def event_generator():
        """Generate SSE events for video processing progress."""
        while True:
            # Refresh video status from database
            async with AsyncSession(db.get_bind()) as session:
                result = await session.execute(
                    select(Video).where(Video.id == video_id)
                )
                current_video = result.scalar_one_or_none()

                if not current_video:
                    break

                event = ProgressEvent(
                    video_id=current_video.id,
                    status=current_video.status,
                    progress=current_video.progress,
                    message=_get_status_message(current_video.status),
                    error=current_video.error_message,
                )

                yield f"data: {event.model_dump_json()}\n\n"

                # Stop if processing is complete or failed
                if current_video.status in [VideoStatus.COMPLETED, VideoStatus.FAILED]:
                    break

            await asyncio.sleep(1)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{video_id}/export")
async def export_transcript(
    video_id: UUID,
    format: str = "txt",
    db: AsyncSession = Depends(get_db),
    auth: tuple = Depends(get_current_user_organization),
):
    """Export transcript in various formats."""
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

    if not video.transcript:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transcript not found",
        )

    filename = f"{video.title or 'transcript'}"

    if format == "txt":
        content = video.transcript.full_text or ""
        return Response(
            content=content,
            media_type="text/plain",
            headers={"Content-Disposition": f'attachment; filename="{filename}.txt"'},
        )

    elif format == "json":
        content = json.dumps({
            "title": video.title,
            "language": video.transcript.language,
            "full_text": video.transcript.full_text,
            "segments": video.transcript.segments,
        }, indent=2)
        return Response(
            content=content,
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{filename}.json"'},
        )

    elif format == "srt":
        content = _generate_srt(video.transcript.segments or [])
        return Response(
            content=content,
            media_type="text/plain",
            headers={"Content-Disposition": f'attachment; filename="{filename}.srt"'},
        )

    elif format == "vtt":
        content = _generate_vtt(video.transcript.segments or [])
        return Response(
            content=content,
            media_type="text/vtt",
            headers={"Content-Disposition": f'attachment; filename="{filename}.vtt"'},
        )

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported format: {format}. Supported: txt, json, srt, vtt",
        )


def _get_status_message(status: VideoStatus) -> str:
    """Get human-readable status message."""
    messages = {
        VideoStatus.PENDING: "Waiting to process...",
        VideoStatus.UPLOADING: "Uploading video...",
        VideoStatus.UPLOADED: "Upload complete, starting processing...",
        VideoStatus.EXTRACTING_AUDIO: "Extracting audio from video...",
        VideoStatus.TRANSCRIBING: "Transcribing audio with AI...",
        VideoStatus.COMPLETED: "Transcription complete!",
        VideoStatus.FAILED: "Processing failed",
    }
    return messages.get(status, "Processing...")


def _format_timestamp_srt(seconds: float) -> str:
    """Format seconds as SRT timestamp (HH:MM:SS,mmm)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _format_timestamp_vtt(seconds: float) -> str:
    """Format seconds as VTT timestamp (HH:MM:SS.mmm)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


def _generate_srt(segments: list) -> str:
    """Generate SRT subtitle format."""
    lines = []
    for i, segment in enumerate(segments, 1):
        start = _format_timestamp_srt(segment.get("start", 0))
        end = _format_timestamp_srt(segment.get("end", 0))
        text = segment.get("text", "")
        lines.append(f"{i}")
        lines.append(f"{start} --> {end}")
        lines.append(text)
        lines.append("")
    return "\n".join(lines)


def _generate_vtt(segments: list) -> str:
    """Generate WebVTT subtitle format."""
    lines = ["WEBVTT", ""]
    for segment in segments:
        start = _format_timestamp_vtt(segment.get("start", 0))
        end = _format_timestamp_vtt(segment.get("end", 0))
        text = segment.get("text", "")
        lines.append(f"{start} --> {end}")
        lines.append(text)
        lines.append("")
    return "\n".join(lines)


@router.get("/{video_id}/subtitles.vtt")
async def get_subtitles(
    video_id: UUID,
    token: str = None,
    db: AsyncSession = Depends(get_db),
):
    """Get subtitles in WebVTT format for video player."""
    # Use token query param or header for auth (track elements can't send headers)
    auth = await get_user_organization_from_token_or_query(token, None, db)
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

    if not video.transcript or not video.transcript.segments:
        # Return empty VTT if no transcript
        return Response(
            content="WEBVTT\n\n",
            media_type="text/vtt",
            headers={
                "Access-Control-Allow-Origin": "*",
            },
        )

    content = _generate_vtt(video.transcript.segments)
    return Response(
        content=content,
        media_type="text/vtt",
        headers={
            "Access-Control-Allow-Origin": "*",
        },
    )


@router.get("/languages/supported")
async def get_supported_languages():
    """Get list of supported translation languages."""
    return [
        {"code": code, "name": name}
        for code, name in SUPPORTED_LANGUAGES.items()
    ]


@router.get("/{video_id}/translate")
async def translate_transcript(
    video_id: UUID,
    target_lang: str,
    db: AsyncSession = Depends(get_db),
    auth: tuple = Depends(get_current_user_organization),
):
    """
    Translate transcript to target language.
    Returns translated segments (does not modify original).
    """
    user, organization, membership = auth

    if target_lang not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported language: {target_lang}. Supported: {list(SUPPORTED_LANGUAGES.keys())}",
        )

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

    if not video.transcript or not video.transcript.segments:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transcript not found or has no segments",
        )

    # Get source language from transcript
    source_lang = video.transcript.language or "auto"

    # Translate segments
    translated_segments = await translation_service.translate_segments(
        video.transcript.segments,
        target_lang,
        source_lang,
    )

    # Generate full text from translated segments
    full_text = " ".join(seg["text"] for seg in translated_segments)

    return {
        "video_id": str(video_id),
        "source_language": source_lang,
        "target_language": target_lang,
        "target_language_name": SUPPORTED_LANGUAGES[target_lang],
        "full_text": full_text,
        "segments": translated_segments,
    }


@router.get("/{video_id}/translate/subtitles.vtt")
async def get_translated_subtitles(
    video_id: UUID,
    target_lang: str,
    token: str = None,
    db: AsyncSession = Depends(get_db),
):
    """Get translated subtitles in WebVTT format for video player."""
    auth = await get_user_organization_from_token_or_query(token, None, db)
    user, organization, membership = auth

    if target_lang not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported language: {target_lang}",
        )

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

    if not video.transcript or not video.transcript.segments:
        return Response(
            content="WEBVTT\n\n",
            media_type="text/vtt",
            headers={"Access-Control-Allow-Origin": "*"},
        )

    # Translate segments
    source_lang = video.transcript.language or "auto"
    translated_segments = await translation_service.translate_segments(
        video.transcript.segments,
        target_lang,
        source_lang,
    )

    content = _generate_vtt(translated_segments)
    return Response(
        content=content,
        media_type="text/vtt",
        headers={"Access-Control-Allow-Origin": "*"},
    )
