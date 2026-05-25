"""
Voice Service - Handles Speech-to-Text and Text-to-Speech
Supports local HTTP endpoints with cloud fallback
"""
import os
import requests
import subprocess
import tempfile
from pathlib import Path
from typing import Optional
import speech_recognition as sr

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    OpenAI = None

try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False
    AudioSegment = None

from schemas import TranscriptionResult
from config import Config
from utils import get_logger

logger = get_logger("voice_service")


class VoiceService:
    """Service for STT and TTS operations"""
    
    def __init__(self, config: Config):
        self.config = config
        self.recognizer = sr.Recognizer()
        
        # Initialize OpenAI client if available
        self.openai_client = None
        if OPENAI_AVAILABLE and config.stt.openai_api_key:
            try:
                self.openai_client = OpenAI(api_key=config.stt.openai_api_key)
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI client: {e}")
    
    def transcribe_audio_file(self, audio_path: Path) -> TranscriptionResult:
        """
        Transcribe audio file using configured STT provider
        Falls back to alternatives if primary fails
        """
        # Try primary provider
        try:
            if self.config.stt.provider == "openai" and self.openai_client:
                return self._transcribe_openai(audio_path)
            elif self.config.stt.provider == "local_http" and self.config.stt.local_http_url:
                return self._transcribe_local_http(audio_path)
            elif self.config.stt.provider == "google":
                return self._transcribe_google(audio_path)
        except Exception as e:
            logger.warning(f"Primary STT provider failed: {e}")
            if not self.config.stt.fallback_enabled:
                raise
        
        # Fallback chain
        if self.config.stt.fallback_enabled:
            # Try OpenAI as fallback
            if self.config.stt.provider != "openai" and self.openai_client:
                try:
                    logger.info("Falling back to OpenAI STT")
                    return self._transcribe_openai(audio_path)
                except Exception as e:
                    logger.warning(f"OpenAI fallback failed: {e}")
            
            # Try Google as final fallback
            if self.config.stt.provider != "google":
                try:
                    logger.info("Falling back to Google STT")
                    return self._transcribe_google(audio_path)
                except Exception as e:
                    logger.error(f"All STT providers failed: {e}")
                    raise
        
        raise RuntimeError("No STT provider available")
    
    def _format_timestamp(self, seconds: float) -> str:
        """Format timestamp as HH:MM:SS,mmm"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    
    def _transcribe_openai(self, audio_path: Path, with_timestamps: bool = True) -> TranscriptionResult:
        """Transcribe using OpenAI Whisper"""
        if not self.openai_client:
            raise RuntimeError("OpenAI client not initialized")
        
        with open(audio_path, 'rb') as audio_file:
            # Use verbose_json to get segments with timestamps
            transcript = self.openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language=None,  # Auto-detect
                response_format="verbose_json" if with_timestamps else "json",
            )
        
        # Parse segments if available
        segments = None
        if with_timestamps and hasattr(transcript, 'segments') and transcript.segments:
            from schemas import TranscriptionSegment
            segments = []
            for i, seg in enumerate(transcript.segments, 1):
                # Handle both dict and object formats
                if isinstance(seg, dict):
                    segments.append(TranscriptionSegment(
                        id=i,
                        start=seg.get('start', 0),
                        end=seg.get('end', 0),
                        text=seg.get('text', '').strip(),
                    ))
                else:
                    # OpenAI returns objects with attributes
                    segments.append(TranscriptionSegment(
                        id=i,
                        start=getattr(seg, 'start', 0),
                        end=getattr(seg, 'end', 0),
                        text=getattr(seg, 'text', '').strip(),
                    ))
        
        return TranscriptionResult(
            text=transcript.text,
            language=getattr(transcript, 'language', None),
            segments=segments,
        )
    
    def _transcribe_local_http(self, audio_path: Path) -> TranscriptionResult:
        """Transcribe using local HTTP endpoint"""
        url = self.config.stt.local_http_url
        if not url:
            raise RuntimeError("Local HTTP URL not configured")
        
        with open(audio_path, 'rb') as audio_file:
            files = {'file': audio_file}
            response = requests.post(url, files=files, timeout=30)
            response.raise_for_status()
            data = response.json()
        
        return TranscriptionResult(
            text=data.get('text', ''),
            language=data.get('language'),
            confidence=data.get('confidence'),
        )
    
    def _convert_to_wav(self, audio_path: Path) -> Path:
        """
        Convert audio file to WAV format if needed.
        Returns path to WAV file (may be original or converted).
        """
        # Check if file is already in a supported format
        ext = audio_path.suffix.lower()
        if ext in ['.wav', '.aiff', '.aif', '.flac']:
            return audio_path
        
        # Need to convert
        if not PYDUB_AVAILABLE:
            raise RuntimeError(
                f"Cannot convert {ext} format to WAV. "
                "pydub is required for format conversion. "
                "Install with: pip install pydub"
            )
        
        logger.info(f"Converting {ext} file to WAV format...")
        temp_wav = Path(tempfile.mktemp(suffix='.wav'))
        
        try:
            audio = AudioSegment.from_file(str(audio_path))
            audio.export(str(temp_wav), format="wav")
            return temp_wav
        except Exception as e:
            if temp_wav.exists():
                temp_wav.unlink()
            raise RuntimeError(f"Failed to convert audio file: {e}")
    
    def _transcribe_google(self, audio_path: Path) -> TranscriptionResult:
        """Transcribe using Google Speech Recognition"""
        # Convert to WAV if needed (Google STT only supports WAV, AIFF, FLAC)
        converted_path = None
        try:
            converted_path = self._convert_to_wav(audio_path)
            
            with sr.AudioFile(str(converted_path)) as source:
                audio = self.recognizer.record(source)
            
            try:
                text = self.recognizer.recognize_google(audio)
                return TranscriptionResult(text=text)
            except sr.UnknownValueError:
                raise RuntimeError("Could not understand audio")
            except sr.RequestError as e:
                raise RuntimeError(f"Google STT request failed: {e}")
        finally:
            # Clean up converted file if we created one
            if converted_path and converted_path != audio_path and converted_path.exists():
                try:
                    converted_path.unlink()
                except Exception:
                    pass  # Ignore cleanup errors
    
    def text_to_speech(self, text: str, output_path: Optional[Path] = None) -> Path:
        """
        Convert text to speech using configured TTS provider
        Returns path to audio file
        """
        if output_path is None:
            import tempfile
            output_path = Path(tempfile.mktemp(suffix='.mp3'))
        
        try:
            if self.config.tts.provider == "openai" and self.openai_client:
                return self._tts_openai(text, output_path)
            elif self.config.tts.provider == "local_http" and self.config.tts.local_http_url:
                return self._tts_local_http(text, output_path)
            elif self.config.tts.provider == "piper":
                return self._tts_piper(text, output_path)
            else:
                # Fallback to system TTS
                return self._tts_system(text, output_path)
        except Exception as e:
            logger.warning(f"TTS failed, using system fallback: {e}")
            return self._tts_system(text, output_path)
    
    def _tts_openai(self, text: str, output_path: Path) -> Path:
        """TTS using OpenAI"""
        if not self.openai_client:
            raise RuntimeError("OpenAI client not initialized")
        
        response = self.openai_client.audio.speech.create(
            model="tts-1",
            voice=self.config.tts.voice,
            input=text,
        )
        
        response.stream_to_file(str(output_path))
        return output_path
    
    def _tts_local_http(self, text: str, output_path: Path) -> Path:
        """TTS using local HTTP endpoint"""
        url = self.config.tts.local_http_url
        if not url:
            raise RuntimeError("Local HTTP URL not configured")
        
        response = requests.post(url, json={"text": text}, timeout=30)
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            f.write(response.content)
        
        return output_path
    
    def _tts_piper(self, text: str, output_path: Path) -> Path:
        """TTS using Piper (local)"""
        # This would need piper installed - simplified for now
        raise NotImplementedError("Piper TTS not yet implemented")
    
    def _tts_system(self, text: str, output_path: Path) -> Path:
        """TTS using system say command (macOS)"""
        # Convert to aiff then to mp3 using ffmpeg if available
        import tempfile
        temp_aiff = Path(tempfile.mktemp(suffix='.aiff'))
        
        subprocess.run(
            ["say", "-v", "Victoria", "-o", str(temp_aiff), text],
            check=True,
        )
        
        # Try to convert to mp3
        try:
            subprocess.run(
                ["ffmpeg", "-i", str(temp_aiff), "-y", str(output_path)],
                check=True,
                capture_output=True,
            )
            temp_aiff.unlink()
        except (subprocess.CalledProcessError, FileNotFoundError):
            # If ffmpeg not available, just use aiff
            temp_aiff.rename(output_path)
        
        return output_path
    
    def play_audio(self, audio_path: Path) -> None:
        """Play audio file"""
        # Use afplay on macOS, or system default
        subprocess.run(["afplay", str(audio_path)], check=False)

