"""Translation service using Lingva API (free Google Translate proxy)."""

import httpx
from typing import Optional

# Public Lingva instances (fallback list)
LINGVA_INSTANCES = [
    "https://lingva.ml",
    "https://translate.plausibility.cloud",
    "https://lingva.pussthecat.org",
]

# Supported languages (common ones)
SUPPORTED_LANGUAGES = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "ru": "Russian",
    "ja": "Japanese",
    "ko": "Korean",
    "zh": "Chinese",
    "ar": "Arabic",
    "hi": "Hindi",
    "nl": "Dutch",
    "pl": "Polish",
    "tr": "Turkish",
    "vi": "Vietnamese",
    "th": "Thai",
    "id": "Indonesian",
    "ms": "Malay",
    "fil": "Filipino",
}


class TranslationService:
    """Translate text using Lingva API."""

    def __init__(self):
        self.instances = LINGVA_INSTANCES
        self.timeout = 30.0

    async def translate(
        self,
        text: str,
        target_lang: str,
        source_lang: str = "auto",
    ) -> Optional[str]:
        """
        Translate text to target language.

        Args:
            text: Text to translate
            target_lang: Target language code (e.g., 'es', 'fr')
            source_lang: Source language code or 'auto' for detection

        Returns:
            Translated text or None if failed
        """
        if not text or not text.strip():
            return text

        # Try each instance until one works
        for instance in self.instances:
            try:
                result = await self._translate_with_instance(
                    instance, text, target_lang, source_lang
                )
                if result:
                    return result
            except Exception:
                continue

        return None

    async def _translate_with_instance(
        self,
        instance: str,
        text: str,
        target_lang: str,
        source_lang: str,
    ) -> Optional[str]:
        """Try translation with a specific Lingva instance."""
        # Lingva API endpoint: /api/v1/{source}/{target}/{text}
        # For longer text, use POST
        url = f"{instance}/api/v1/{source_lang}/{target_lang}/{text}"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # For short text, use GET
            if len(text) < 500:
                response = await client.get(url)
            else:
                # For longer text, chunk it
                return await self._translate_long_text(
                    client, instance, text, target_lang, source_lang
                )

            if response.status_code == 200:
                data = response.json()
                return data.get("translation")

        return None

    async def _translate_long_text(
        self,
        client: httpx.AsyncClient,
        instance: str,
        text: str,
        target_lang: str,
        source_lang: str,
    ) -> Optional[str]:
        """Translate long text by chunking."""
        # Split by sentences (rough approximation)
        chunks = self._split_text(text, max_length=400)
        translated_chunks = []

        for chunk in chunks:
            url = f"{instance}/api/v1/{source_lang}/{target_lang}/{chunk}"
            try:
                response = await client.get(url)
                if response.status_code == 200:
                    data = response.json()
                    translated_chunks.append(data.get("translation", chunk))
                else:
                    translated_chunks.append(chunk)
            except Exception:
                translated_chunks.append(chunk)

        return " ".join(translated_chunks)

    def _split_text(self, text: str, max_length: int = 400) -> list[str]:
        """Split text into chunks, trying to break at sentence boundaries."""
        if len(text) <= max_length:
            return [text]

        chunks = []
        current_chunk = ""

        # Split by sentences first
        sentences = text.replace(". ", ".|").replace("! ", "!|").replace("? ", "?|").split("|")

        for sentence in sentences:
            if len(current_chunk) + len(sentence) <= max_length:
                current_chunk += sentence + " "
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + " "

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    async def translate_segments(
        self,
        segments: list[dict],
        target_lang: str,
        source_lang: str = "auto",
    ) -> list[dict]:
        """
        Translate transcript segments.

        Args:
            segments: List of segments with 'text', 'start', 'end' keys
            target_lang: Target language code
            source_lang: Source language code or 'auto'

        Returns:
            Segments with translated text
        """
        translated_segments = []

        for segment in segments:
            translated_text = await self.translate(
                segment.get("text", ""),
                target_lang,
                source_lang,
            )

            translated_segments.append({
                "start": segment.get("start", 0),
                "end": segment.get("end", 0),
                "text": translated_text or segment.get("text", ""),
                "speaker": segment.get("speaker"),
            })

        return translated_segments

    def get_supported_languages(self) -> dict[str, str]:
        """Return supported language codes and names."""
        return SUPPORTED_LANGUAGES


# Singleton instance
translation_service = TranslationService()
