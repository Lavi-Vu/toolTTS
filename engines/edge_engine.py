"""
Edge TTS Engine implementation
"""
import asyncio
import io
from typing import Dict, Any, List, Tuple
from .base_engine import TTSEngine


class EdgeTTSEngine(TTSEngine):
    """Edge TTS engine implementation"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._edge_tts = None
        self._communicate = None
        self._list_voices = None
        self._submaker = None
        self._all_voices = []
        self._filtered_voices = []
        self._languages = []
        # Initialize Edge TTS components
        self.is_available()

    def is_available(self) -> bool:
        """Check if edge-tts is available"""
        try:
            import edge_tts
            self._edge_tts = edge_tts
            self._communicate = edge_tts.Communicate
            self._list_voices = edge_tts.list_voices
            self._submaker = edge_tts.SubMaker
            return True
        except ImportError:
            return False

    def _cache_voices(self):
        """Cache all voices from Edge TTS and filter by configured languages"""
        try:
            # Get all available voices from Edge TTS
            import asyncio

            # Create new event loop for async call
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                all_voices = loop.run_until_complete(self._list_voices())
            finally:
                loop.close()

            # Get configured language prefixes
            configured_languages = list(self.config.get('languages', {}).keys())

            # Filter voices by configured languages
            self._filtered_voices = []
            self._languages = []
            language_map = {}

            for voice in all_voices:
                voice_locale = voice.get('Locale', '')
                lang_prefix = voice_locale.split('-')[0] if '-' in voice_locale else voice_locale

                # Check if this language is configured
                if lang_prefix in configured_languages:
                    # Extract voice name from ShortName (remove Neural suffix)
                    short_name = voice['ShortName']
                    voice_name = short_name.split('-')[-1].replace('Neural', '').replace('RUS', '')

                    voice_info = {
                        'id': voice['ShortName'],
                        'name': voice_name,
                        'gender': voice.get('Gender', 'unknown').lower(),
                        'language': voice_locale,
                        'language_prefix': lang_prefix,
                        'locale_name': voice.get('LocaleName', voice_locale)
                    }
                    self._filtered_voices.append(voice_info)

                    # Build language info
                    if lang_prefix not in language_map:
                        lang_name = self.config.get('languages', {}).get(lang_prefix, f"{lang_prefix.upper()} Language")
                        language_map[lang_prefix] = {
                            'code': lang_prefix,
                            'name': lang_name,
                            'prefix': lang_prefix,
                            'full_locale': voice_locale
                        }

            # Convert language map to list
            self._languages = list(language_map.values())

            print(f"✓ Loaded {len(self._filtered_voices)} voices for {len(self._languages)} languages from Edge TTS")

        except Exception as e:
            print(f"Warning: Failed to cache voices from Edge TTS: {e}")
            # Create minimal fallback data
            configured_languages = list(self.config.get('languages', {}).keys())
            self._languages = []
            self._filtered_voices = []

            for lang_code in configured_languages:
                lang_name = self.config.get('languages', {}).get(lang_code, f"{lang_code.upper()} Language")
                self._languages.append({
                    'code': lang_code,
                    'name': lang_name,
                    'prefix': lang_code,
                    'full_locale': f"{lang_code}-US"
                })
                # Add fallback voice
                self._filtered_voices.append({
                    'id': f'{lang_code}-US-AriaNeural',
                    'name': 'Aria',
                    'gender': 'female',
                    'language': f"{lang_code}-US",
                    'language_prefix': lang_code,
                    'locale_name': lang_name
                })

    async def _synthesize_async(self, text: str, voice_id: str, **kwargs) -> Tuple[bytes, str]:
        """Asynchronous synthesis with native Edge TTS subtitles"""
        if not self.is_available():
            raise ImportError("edge-tts is not installed")

        rate = kwargs.get('rate', '+0%')
        volume = kwargs.get('volume', '+0%')

        communicate = self._communicate(text, voice_id)
        communicate.rate = rate
        communicate.volume = volume

        # Create SubMaker for subtitle generation
        submaker = self._submaker()

        audio_data = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]
            elif chunk["type"] in ("WordBoundary", "SentenceBoundary"):
                submaker.feed(chunk)

        # Get SRT content
        srt_content = submaker.get_srt()

        return audio_data, srt_content

    def synthesize(self, text: str, voice_id: str, **kwargs) -> bytes:
        """Synthesize text to speech (legacy method for compatibility)"""
        try:
            # Run async synthesis in event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            audio_data, srt_content = loop.run_until_complete(self._synthesize_async(text, voice_id, **kwargs))
            loop.close()
            # Store SRT content for later retrieval
            self._last_srt_content = srt_content
            return audio_data
        except Exception as e:
            raise RuntimeError(f"Edge TTS synthesis failed: {str(e)}")

    def synthesize_with_subtitles(self, text: str, voice_id: str, **kwargs) -> Tuple[bytes, str]:
        """Synthesize text to speech with native Edge TTS subtitles"""
        try:
            # Run async synthesis in event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            result = loop.run_until_complete(self._synthesize_async(text, voice_id, **kwargs))
            loop.close()
            return result
        except Exception as e:
            raise RuntimeError(f"Edge TTS synthesis with subtitles failed: {str(e)}")

    def get_available_voices(self) -> List[Dict[str, Any]]:
        """Get available voices, caching on first call"""
        if not self._filtered_voices:
            self._cache_voices()
        return self._filtered_voices

    def get_available_languages(self) -> List[Dict[str, Any]]:
        """Get available languages, caching on first call"""
        if not self._languages:
            self._cache_voices()
        return self._languages

    def get_last_srt_content(self) -> str:
        """Get SRT content from the last synthesis"""
        return getattr(self, '_last_srt_content', '')
