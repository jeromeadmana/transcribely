import os
import tempfile
import subprocess
from typing import Optional
from faster_whisper import WhisperModel

from app.core.config import settings


class TranscriptionService:
    _instance: Optional["TranscriptionService"] = None
    _model: Optional[WhisperModel] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _get_model(self) -> WhisperModel:
        """Lazy load the Whisper model."""
        if self._model is None:
            self._model = WhisperModel(
                model_size_or_path=settings.whisper_model,
                device=settings.whisper_device,
                compute_type=settings.whisper_compute_type,
            )
        return self._model

    def extract_audio(self, video_path: str, output_path: Optional[str] = None) -> str:
        """Extract audio from video file using FFmpeg."""
        if output_path is None:
            output_path = tempfile.mktemp(suffix=".mp3")

        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-vn",  # No video
            "-acodec", "libmp3lame",
            "-q:a", "2",  # High quality
            "-y",  # Overwrite output
            output_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg failed: {result.stderr}")

        return output_path

    def get_video_duration(self, video_path: str) -> Optional[float]:
        """Get video duration in seconds using FFprobe."""
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            try:
                return float(result.stdout.strip())
            except ValueError:
                return None
        return None

    def transcribe(self, audio_path: str, language: Optional[str] = None) -> dict:
        """Transcribe audio file using Whisper."""
        model = self._get_model()

        segments_list, info = model.transcribe(
            audio_path,
            beam_size=5,
            language=language,  # Auto-detect if None
            vad_filter=True,  # Voice activity detection
            vad_parameters=dict(
                min_silence_duration_ms=500,
            ),
        )

        # Convert generator to list and build result
        segments = []
        full_text_parts = []

        for segment in segments_list:
            segments.append({
                "start": round(segment.start, 2),
                "end": round(segment.end, 2),
                "text": segment.text.strip(),
                "speaker": None,  # Speaker diarization would go here
            })
            full_text_parts.append(segment.text.strip())

        full_text = " ".join(full_text_parts)
        word_count = len(full_text.split())

        return {
            "language": info.language,
            "language_probability": info.language_probability,
            "duration": info.duration,
            "full_text": full_text,
            "segments": segments,
            "word_count": word_count,
        }

    def cleanup(self, *paths: str) -> None:
        """Remove temporary files."""
        for path in paths:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass


# Singleton instance
transcription_service = TranscriptionService()
