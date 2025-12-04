"""
Base TTS Engine class for all TTS implementations
"""
import abc
import re
from typing import Optional, Dict, Any, List, Tuple


class TTSEngine(abc.ABC):
    """Abstract base class for TTS engines"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = config.get('name', 'Unknown Engine')
        self.description = config.get('description', '')

    @abc.abstractmethod
    def synthesize(self, text: str, voice_id: str, **kwargs) -> bytes:
        """
        Synthesize text to speech

        Args:
            text: Text to synthesize
            voice_id: Voice identifier
            **kwargs: Additional parameters (rate, volume, etc.)

        Returns:
            Audio data as bytes
        """
        pass

    @abc.abstractmethod
    def get_available_voices(self) -> list:
        """Get list of available voices for this engine"""
        pass

    @abc.abstractmethod
    def get_available_languages(self) -> list:
        """Get list of available languages for this engine"""
        pass

    def is_available(self) -> bool:
        """Check if this engine is available (dependencies installed)"""
        return True

    def split_into_sentences(self, text: str, language: str = 'en') -> List[str]:
        """Split text into sentences using language-specific rules"""

        # Language-specific sentence splitting patterns
        patterns = {
            'en': {
                'split_pattern': r'(?<=[.!?])\s+(?=[A-Z])|(?<=[.!?])$',
                'abbreviations': r'\b(Mr|Mrs|Dr|Ms|Jr|Sr|etc|e\.g|i\.e|vs)\.\s*$'
            },
            'vi': {
                'split_pattern': r'(?<=[.!?])\s+(?=[A-Z])|(?<=[.!?])$',
                'abbreviations': r'\b(Ông|Bà|Cô|Chị|Anh|Em)\.\s*$'
            },
            'ja': {
                'split_pattern': r'(?<=。|！|？)',
                'abbreviations': r''
            },
            'zh': {
                'split_pattern': r'(?<=。|！|？)',
                'abbreviations': r''
            },
            'ko': {
                'split_pattern': r'(?<=。|！|？)',
                'abbreviations': r''
            }
        }

        # Get language-specific pattern, default to English
        lang_config = patterns.get(language[:2], patterns['en'])

        # Split on sentence endings
        sentences = re.split(lang_config['split_pattern'], text.strip())

        # Filter out empty sentences and clean up
        sentences = [s.strip() for s in sentences if s.strip()]

        # Handle abbreviations for languages that have them
        if lang_config['abbreviations']:
            merged_sentences = []
            i = 0
            while i < len(sentences):
                current = sentences[i]
                # Check if current sentence ends with abbreviation
                if (i + 1 < len(sentences) and
                    re.search(lang_config['abbreviations'], current, re.IGNORECASE)):
                    current += ' ' + sentences[i + 1]
                    i += 1
                merged_sentences.append(current)
                i += 1
            sentences = merged_sentences

        return sentences

    def generate_srt_content(self, sentences: List[str], timings: List[Tuple[float, float]]) -> str:
        """Generate SRT file content"""
        srt_lines = []

        for i, (sentence, (start_time, end_time)) in enumerate(zip(sentences, timings), 1):
            srt_lines.append(str(i))
            srt_lines.append(f"{self._format_srt_time(start_time)} --> {self._format_srt_time(end_time)}")
            srt_lines.append(sentence)
            srt_lines.append("")  # Empty line between entries

        return "\n".join(srt_lines)

    def _format_srt_time(self, seconds: float) -> str:
        """Format seconds into SRT time format (HH:MM:SS,mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milliseconds = int((seconds % 1) * 1000)

        return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"

    def _get_audio_duration(self, audio_data: bytes, fallback_text: str = "") -> float:
        """
        Get duration from audio file data in seconds
        Supports WAV and MP3 formats, with fallback to text-based estimation
        """
        # Try WAV format first
        if len(audio_data) >= 44 and audio_data.startswith(b'RIFF'):
            try:
                # WAV header format:
                # Bytes 40-43: Data size
                # Bytes 24-27: Sample rate
                # Bytes 22-23: Channels
                # Bytes 34-35: Bits per sample

                data_size = int.from_bytes(audio_data[40:44], byteorder='little')
                sample_rate = int.from_bytes(audio_data[24:28], byteorder='little')
                channels = int.from_bytes(audio_data[22:23], byteorder='little')
                bits_per_sample = int.from_bytes(audio_data[34:35], byteorder='little')

                if sample_rate > 0 and channels > 0:
                    # Calculate duration: data_size / (sample_rate * channels * bits_per_sample / 8)
                    bytes_per_second = sample_rate * channels * (bits_per_sample // 8)
                    if bytes_per_second > 0:
                        duration = data_size / bytes_per_second
                        return max(0.1, duration)  # Minimum 0.1 seconds

            except (IndexError, ValueError, ZeroDivisionError):
                pass

        # Try MP3 format (basic frame counting)
        elif len(audio_data) >= 4 and (audio_data.startswith(b'ID3') or
                                       audio_data[0:2] in [b'\xff\xfb', b'\xff\xf3', b'\xff\xf2']):
            try:
                # Very basic MP3 duration estimation
                # This is approximate - real MP3 parsing is much more complex
                # MP3 frame size varies, but roughly 1 frame = ~26ms at 44.1kHz
                # This is a rough fallback
                mp3_data = audio_data
                if audio_data.startswith(b'ID3'):
                    # Skip ID3 tag (variable length, but roughly 128+ bytes)
                    id3_size = 128  # Approximate
                    if len(audio_data) > id3_size:
                        mp3_data = audio_data[id3_size:]

                # Rough estimation: ~38 frames per second for 128kbps MP3
                frame_count = len(mp3_data) // 417  # Approximate frame size
                duration = frame_count / 38.0
                return max(0.5, duration)  # Minimum 0.5 seconds for MP3

            except (IndexError, ValueError):
                pass

        # Fallback to text-based estimation (~15 chars/second is rough for speech)
        if fallback_text:
            duration = max(1.0, len(fallback_text) / 15.0)
            print(f"Using text-based duration estimation: {duration:.2f}s (fallback)")
            return duration

        # Absolute fallback
        return 1.0

    def synthesize_with_subtitles(self, text: str, voice_id: str, language: str = 'en', **kwargs) -> Tuple[bytes, str]:
        """
        Synthesize text and generate SRT subtitles

        For engines that support native subtitle generation (like Edge TTS),
        this uses the engine's built-in SubMaker. For other engines, it falls
        back to basic sentence splitting.

        Args:
            text: Text to synthesize
            voice_id: Voice identifier
            language: Language code for sentence splitting (e.g., 'en', 'vi', 'ja')

        Returns:
            Tuple of (audio_data, srt_content)
        """
        # Try engine-specific subtitle generation first (for Edge TTS)
        if hasattr(self, 'get_last_srt_content'):
            # Engine supports native subtitles (Edge TTS)
            audio_data = self.synthesize(text, voice_id, **kwargs)
            srt_content = self.get_last_srt_content()
            if srt_content:  # If native subtitles were generated
                return audio_data, srt_content

        # Fallback to basic sentence splitting (for other engines)
        sentences = self.split_into_sentences(text, language)
        audio_data = self.synthesize(text, voice_id, **kwargs)

        # Create basic SRT with estimated timings
        srt_lines = []
        current_time = 0.0

        for i, sentence in enumerate(sentences, 1):
            if not sentence.strip():
                continue

            # Estimate duration (rough calculation)
            duration = max(1.0, len(sentence) / 15.0)  # ~15 chars/second
            start_time = current_time
            end_time = current_time + duration

            srt_lines.append(str(i))
            srt_lines.append(f"{self._format_srt_time(start_time)} --> {self._format_srt_time(end_time)}")
            srt_lines.append(sentence)
            srt_lines.append("")

            current_time = end_time + 0.1  # Small gap

        srt_content = "\n".join(srt_lines)
        return audio_data, srt_content

