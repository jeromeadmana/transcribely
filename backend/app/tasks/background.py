"""Simple background task runner without Celery/Redis dependency."""
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from uuid import UUID
from decimal import Decimal
import tempfile
import os

from sqlalchemy.orm import Session

from app.core.database import SyncSessionLocal
from app.models.video import Video, Transcript, UsageRecord, VideoStatus
from app.services.storage import storage_service
from app.services.transcription import transcription_service
from app.core.config import settings


# Thread pool for background tasks
executor = ThreadPoolExecutor(max_workers=2)


def update_video_status(db: Session, video_id: UUID, status: VideoStatus, progress: int = 0, error_message: str = None):
    """Update video status in database."""
    video = db.query(Video).filter(Video.id == video_id).first()
    if video:
        video.status = status
        video.progress = progress
        if error_message:
            video.error_message = error_message
        db.commit()


def process_video_sync(video_id: str):
    """Process uploaded video: extract audio and transcribe (synchronous)."""
    video_uuid = UUID(video_id)
    db = SyncSessionLocal()
    temp_video_path = None
    audio_path = None

    try:
        # Get video from database
        video = db.query(Video).filter(Video.id == video_uuid).first()
        if not video:
            raise ValueError(f"Video not found: {video_id}")

        # Update status to extracting audio
        update_video_status(db, video_uuid, VideoStatus.EXTRACTING_AUDIO, progress=10)

        # Get the video file path
        if settings.storage_type == "local":
            video_path = storage_service.get_file_path(video.storage_key)
        else:
            # Download from S3
            temp_video_path = tempfile.mktemp(suffix=os.path.splitext(video.storage_key)[1])
            storage_service.download_file(video.storage_key, temp_video_path)
            video_path = temp_video_path

        # Get video duration
        duration = transcription_service.get_video_duration(video_path)
        if duration:
            video.duration_seconds = int(duration)
            db.commit()

        update_video_status(db, video_uuid, VideoStatus.EXTRACTING_AUDIO, progress=20)

        # Extract audio
        audio_path = transcription_service.extract_audio(video_path)
        update_video_status(db, video_uuid, VideoStatus.TRANSCRIBING, progress=30)

        # Transcribe audio
        result = transcription_service.transcribe(audio_path)
        update_video_status(db, video_uuid, VideoStatus.TRANSCRIBING, progress=80)

        # Create transcript record
        transcript = Transcript(
            video_id=video_uuid,
            full_text=result["full_text"],
            segments=result["segments"],
            language=result["language"],
            word_count=result["word_count"],
        )
        db.add(transcript)

        # Record usage
        if duration:
            minutes_used = Decimal(str(duration / 60))
            usage = UsageRecord(
                organization_id=video.organization_id,
                video_id=video_uuid,
                minutes_used=minutes_used,
            )
            db.add(usage)

        # Update video status to completed
        video.status = VideoStatus.COMPLETED
        video.progress = 100
        db.commit()

        print(f"Successfully processed video {video_id}")

    except Exception as e:
        print(f"Error processing video {video_id}: {e}")
        db.rollback()
        update_video_status(db, video_uuid, VideoStatus.FAILED, error_message=str(e))

    finally:
        # Cleanup temporary files
        transcription_service.cleanup(temp_video_path, audio_path)
        db.close()


def process_video_background(video_id: str):
    """Submit video processing to background thread pool."""
    executor.submit(process_video_sync, video_id)
    print(f"Submitted video {video_id} for background processing")
