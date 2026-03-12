from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional, List
from app.models.video import VideoStatus


# Video schemas
class VideoCreate(BaseModel):
    title: Optional[str] = None
    original_filename: str
    mime_type: Optional[str] = None
    file_size_bytes: Optional[int] = None


class VideoResponse(BaseModel):
    id: UUID
    organization_id: UUID
    uploaded_by: Optional[UUID]
    title: Optional[str]
    original_filename: Optional[str]
    storage_key: str
    duration_seconds: Optional[int]
    file_size_bytes: Optional[int]
    mime_type: Optional[str]
    status: VideoStatus
    error_message: Optional[str]
    progress: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class VideoWithTranscript(VideoResponse):
    transcript: Optional["TranscriptResponse"] = None


class UploadUrlResponse(BaseModel):
    video_id: UUID
    upload_url: str
    storage_key: str


class CompleteUploadRequest(BaseModel):
    video_id: UUID


# Transcript schemas
class TranscriptSegment(BaseModel):
    start: float
    end: float
    text: str
    speaker: Optional[str] = None


class TranscriptResponse(BaseModel):
    id: UUID
    video_id: UUID
    full_text: Optional[str]
    segments: Optional[List[TranscriptSegment]]
    language: Optional[str]
    word_count: Optional[int]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TranscriptUpdate(BaseModel):
    full_text: Optional[str] = None
    segments: Optional[List[TranscriptSegment]] = None


# Progress event for SSE
class ProgressEvent(BaseModel):
    video_id: UUID
    status: VideoStatus
    progress: int
    message: Optional[str] = None
    error: Optional[str] = None


# Update forward references
VideoWithTranscript.model_rebuild()
