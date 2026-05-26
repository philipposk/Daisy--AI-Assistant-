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

        # Fix #5: separate OpenAI clients for STT and TTS (each may have its own key)
        # Backward compatible: if only one key is set, share it.
        stt_key = config.stt.openai_api_key
        tts_key = config.tts.openai_api_key or stt_key

        self.openai_client = None       # STT client
        self.tts_openai_client = None   # TTS client
        if OPENAI_AVAILABLE:
            if stt_key:
                try:
                    self.openai_client = OpenAI(api_key=stt_key)
                except Exception as e:
                    logger.warning(f"Failed to initialize OpenAI STT client: {e}")
            if tts_key:
                try:
                    self.tts_openai_client = (
                        self.openai_client
                        if tts_key == stt_key and self.openai_client
                        else OpenAI(api_key=tts_key)
                    )
                except Exception as e:
                    logger.warning(f"Failed to initialize OpenAI TTS client: {e}")

        # Fix #21: handle to currently-playing audio process (so 0.8 can interrupt for barge-in)
        self.current_playback: Optional[subprocess.Popen] = None
    
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
        # Fix #6: NamedTemporaryFile avoids the mktemp() race window
        tf = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        tf.close()
        temp_wav = Path(tf.name)

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
            # Fix #6: NamedTemporaryFile avoids mktemp race
            tf = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False)
            tf.close()
            output_path = Path(tf.name)
        
        try:
            if self.config.tts.provider == "openai" and self.tts_openai_client:
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
        client = self.tts_openai_client or self.openai_client
        if not client:
            raise RuntimeError("OpenAI client not initialized")

        response = client.audio.speech.create(
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
        """
        TTS using Piper (local).

        Fix #7: shell out to the `piper` binary. Config (added in 0.7) reads:
          tts.piper_binary  (default: "piper")
          tts.piper_model   (path to .onnx voice model; required)
        Output is WAV; if caller asked for .mp3 we attempt ffmpeg conversion,
        else we rename to whatever extension was requested.
        """
        piper_bin = getattr(self.config.tts, "piper_binary", None) or "piper"
        piper_model = getattr(self.config.tts, "piper_model", None)
        if not piper_model:
            raise RuntimeError(
                "Piper TTS requires tts.piper_model in config (path to .onnx voice model). "
                "Download a model from https://github.com/rhasspy/piper/blob/master/VOICES.md"
            )

        # Piper writes WAV; create alongside requested path
        tf = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        tf.close()
        wav_path = Path(tf.name)

        try:
            proc = subprocess.run(
                [piper_bin, "--model", str(Path(piper_model).expanduser()),
                 "--output_file", str(wav_path)],
                input=text,
                text=True,
                capture_output=True,
                check=True,
            )
        except FileNotFoundError as e:
            wav_path.unlink(missing_ok=True)
            raise RuntimeError(
                f"Piper binary not found ({piper_bin}). Install with `brew install piper` "
                f"or set tts.piper_binary in config."
            ) from e
        except subprocess.CalledProcessError as e:
            wav_path.unlink(missing_ok=True)
            raise RuntimeError(f"Piper TTS failed: {e.stderr or e}") from e

        # If output_path already wants WAV, just move
        if output_path.suffix.lower() == ".wav":
            wav_path.replace(output_path)
            return output_path

        # Try ffmpeg conversion; fall back to renaming the WAV
        try:
            subprocess.run(
                ["ffmpeg", "-y", "-i", str(wav_path), str(output_path)],
                check=True, capture_output=True,
            )
            wav_path.unlink(missing_ok=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            wav_path.replace(output_path)
        return output_path

    def _tts_system(self, text: str, output_path: Path) -> Path:
        """TTS using system `say` command (macOS)."""
        # Fix #6: NamedTemporaryFile (not mktemp)
        tf = tempfile.NamedTemporaryFile(suffix='.aiff', delete=False)
        tf.close()
        temp_aiff = Path(tf.name)

        # Fix #8: pull voice from config instead of hardcoding "Victoria".
        # Map known OpenAI voice names to macOS `say` voices when user hasn't customized.
        voice = self.config.tts.voice or "Victoria"
        openai_voice_map = {
            "nova": "Samantha", "shimmer": "Samantha", "alloy": "Alex",
            "echo": "Alex", "fable": "Daniel", "onyx": "Daniel",
        }
        say_voice = openai_voice_map.get(voice.lower(), voice)

        try:
            subprocess.run(
                ["say", "-v", say_voice, "-o", str(temp_aiff), text],
                check=True,
            )
        except subprocess.CalledProcessError:
            # Voice unknown to macOS — retry without -v
            subprocess.run(["say", "-o", str(temp_aiff), text], check=True)

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

    def play_audio(self, audio_path: Path, wait: bool = True) -> None:
        """
        Play audio file.

        Fix #21: spawn via Popen and store the handle on self.current_playback so
        0.8 can call stop_playback() for barge-in. Behaviour stays synchronous by
        default (wait=True) to preserve the 0.6 contract.
        """
        try:
            proc = subprocess.Popen(["afplay", str(audio_path)])
        except FileNotFoundError:
            # Non-macOS fallback
            proc = subprocess.Popen(["aplay", str(audio_path)])

        self.current_playback = proc
        if wait:
            try:
                proc.wait()
            finally:
                if self.current_playback is proc:
                    self.current_playback = None

    def stop_playback(self) -> None:
        """Stop any in-progress audio playback (used by 0.8 barge-in)."""
        proc = self.current_playback
        if proc and proc.poll() is None:
            try:
                proc.terminate()
            except Exception:
                pass
        self.current_playback = None

