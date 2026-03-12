import tempfile
import os
from uuid import UUID
from decimal import Decimal

from app.tasks.celery_app import celery_app
from app.core.database import SyncSessionLocal
from app.models.video import Video, Transcript, UsageRecord, VideoStatus
from app.services.storage import storage_service
from app.services.transcription import transcription_service


def update_video_status(db, video_id: UUID, status: VideoStatus, progress: int = 0, error_message: str = None):
    """Update video status in database."""
    video = db.query(Video).filter(Video.id == video_id).first()
    if video:
        video.status = status
        video.progress = progress
        if error_message:
            video.error_message = error_message
        db.commit()


@celery_app.task(bind=True, max_retries=3)
def process_video(self, video_id: str):
    """Process uploaded video: extract audio and transcribe."""
    video_uuid = UUID(video_id)
    db = SyncSessionLocal()
    video_path = None
    audio_path = None

    try:
        # Get video from database
        video = db.query(Video).filter(Video.id == video_uuid).first()
        if not video:
            raise ValueError(f"Video not found: {video_id}")

        # Update status to extracting audio
        update_video_status(db, video_uuid, VideoStatus.EXTRACTING_AUDIO, progress=10)

        # Download video from storage
        video_path = tempfile.mktemp(suffix=os.path.splitext(video.storage_key)[1])
        storage_service.download_file(video.storage_key, video_path)

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

    except Exception as e:
        db.rollback()
        update_video_status(db, video_uuid, VideoStatus.FAILED, error_message=str(e))
        raise self.retry(exc=e, countdown=60)

    finally:
        # Cleanup temporary files
        transcription_service.cleanup(video_path, audio_path)
        db.close()

    return {"video_id": video_id, "status": "completed"}
