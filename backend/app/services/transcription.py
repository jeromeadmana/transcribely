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

        # First try with VAD filter for better results
        try:
            segments_gen, info = model.transcribe(
                audio_path,
                beam_size=5,
                language=language,  # Auto-detect if None
                vad_filter=True,  # Voice activity detection
                vad_parameters=dict(
                    min_silence_duration_ms=300,
                    speech_pad_ms=200,
                ),
            )
            # Convert generator to list immediately to catch errors
            segments_list = list(segments_gen)
        except Exception as e:
            # If VAD fails, try without it
            print(f"VAD transcription failed, retrying without VAD: {e}")
            segments_gen, info = model.transcribe(
                audio_path,
                beam_size=5,
                language=language,
                vad_filter=False,
            )
            segments_list = list(segments_gen)

        # Build result from segments
        segments = []
        full_text_parts = []

        for segment in segments_list:
            text = segment.text.strip()
            if text:  # Only add non-empty segments
                segments.append({
                    "start": round(segment.start, 2),
                    "end": round(segment.end, 2),
                    "text": text,
                    "speaker": None,  # Speaker diarization would go here
                })
                full_text_parts.append(text)

        full_text = " ".join(full_text_parts)
        word_count = len(full_text.split()) if full_text else 0

        # Handle case where no speech was detected
        if not segments:
            return {
                "language": info.language if hasattr(info, 'language') else "unknown",
                "language_probability": getattr(info, 'language_probability', 0.0),
                "duration": getattr(info, 'duration', 0.0),
                "full_text": "",
                "segments": [],
                "word_count": 0,
            }

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
