#!/usr/bin/env python3
"""
Daisy - Personal AI Assistant
Features:
- Natural woman's voice (OpenAI TTS)
- LLM-powered conversations (OpenAI GPT-4 or Anthropic Claude)
- Voice recognition for two-way conversation
- Context memory and personalization
"""

import json
import os
import subprocess
import time
import re
import base64
import requests
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import threading
from dataclasses import dataclass, asdict
from datetime import datetime
import sys

# Core dependencies
try:
    import speech_recognition as sr
    from openai import OpenAI
except ImportError:
    print("❌ Missing required packages. Installing...")
    import sys
    try:
        # Try installing without pyaudio first (it requires system library portaudio)
        subprocess.check_call([sys.executable, "-m", "pip", "install", "openai", "speechrecognition", "pydub"], 
                            stderr=subprocess.DEVNULL)
        print("✅ Core packages installed")
    except:
        # If that fails, install everything
        subprocess.check_call([sys.executable, "-m", "pip", "install", "openai", "speechrecognition", "pydub"])
    try:
        # Try installing pyaudio separately (may fail if portaudio not installed)
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyaudio"], 
                            stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        print("✅ pyaudio installed")
    except:
        print("⚠️  pyaudio not installed (requires portaudio). Voice input will use fallback method.")
        print("   To install: brew install portaudio, then: pip install pyaudio")
    import speech_recognition as sr
    from openai import OpenAI

try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False
    # pyaudio not required - speech_recognition can work without it

import io

# Groq SDK import (PROVEN WORKING - matches Praiser)
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    Groq = None

@dataclass
class ConversationMessage:
    """Represents a message in the conversation"""
    role: str  # 'user', 'assistant', 'system'
    content: str
    timestamp: str

class DaisyAssistant:
    """Personal AI Assistant with voice and conversation capabilities"""
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path.home() / ".daisy" / "config.json"
        self.config = self.load_config()
        self.setup_directories()
        
        # Initialize OpenAI client
        openai_api_key = os.getenv("OPENAI_API_KEY") or self.config.get("openai_api_key")
        self.client = None
        if openai_api_key:
            try:
                self.client = OpenAI(api_key=openai_api_key)
                print("✅ OpenAI client initialized")
            except Exception as e:
                print(f"⚠️  OpenAI client error: {e}")
        else:
            print("⚠️  OpenAI API key not found")
        
        # Initialize Groq client (PROVEN WORKING APPROACH - same as Praiser)
        groq_api_key = os.getenv("GROQ_API_KEY") or self.config.get("groq_api_key")
        self.groq_client = None
        self.groq_models_cache = None
        self.groq_models_cache_time = 0
        self.GROQ_CACHE_TTL = 3600  # 1 hour cache (same as Praiser)
        
        # Groq working model cache (remember which model works)
        # Try to load from config if available (persists across restarts)
        self.groq_working_model = self.config.get("groq_working_model")
        saved_check_time = self.config.get("groq_model_check_time", 0)
        # Only use saved time if it's recent (within last hour)
        now = time.time()
        if saved_check_time and (now - saved_check_time < 3600):
            self.groq_model_check_time = saved_check_time
        else:
            self.groq_model_check_time = 0
        self.GROQ_MODEL_CHECK_INTERVAL = 3600  # Re-check working model every hour
        
        if GROQ_AVAILABLE and groq_api_key:
            try:
                self.groq_client = Groq(api_key=groq_api_key)
                print("✅ Groq client initialized")
            except Exception as e:
                print(f"⚠️  Groq client error: {e}")
        elif GROQ_AVAILABLE and not groq_api_key:
            print("⚠️  Groq API key not found (optional fallback)")
        
        # Conversation history
        self.conversation_history: List[ConversationMessage] = []
        self.max_history = 50  # Keep last 50 messages
        
        # Voice recognition
        self.recognizer = sr.Recognizer()
        try:
            self.microphone = sr.Microphone()
            print("✅ Microphone available")
        except Exception as e:
            print(f"⚠️  Microphone not available: {e}")
            self.microphone = None
            if not PYAUDIO_AVAILABLE:
                print("   Note: Install portaudio for full voice support: brew install portaudio")
        self.is_listening = False
        
        # Audio playback control (for interruption)
        self.current_audio_process = None
        self.is_speaking = False
        
        # Interrupt handling (event-based for better responsiveness)
        self.interrupt_event = threading.Event()
        self.interrupt_detected = False
        
        # Quota check caching (avoid checking every request)
        self.openai_quota_exceeded = False
        self.quota_check_time = 0
        self.QUOTA_CHECK_INTERVAL = 3600  # Check once per hour (3600 seconds)
        
        # Interrupt cooldown to prevent immediate re-listening after interrupt
        self.interrupt_time = 0
        self.INTERRUPT_COOLDOWN = 3.0  # Ignore audio for 3 seconds after interrupt
        self.last_response_time = 0  # Track when we last responded
        self.RESPONSE_COOLDOWN = 5.0  # Ignore similar inputs for 5 seconds after responding
        
        # TTS engine selection
        self.tts_engine = self.config.get("tts_engine", "piper")  # piper, coqui, openai, say
        self.piper_available = self._check_piper_available()
        self.coqui_available = self._check_coqui_available()
        
        # Initialize system prompt (will be enhanced with language detection)
        self.base_system_prompt = self.config.get(
            "system_prompt",
            """You are Daisy, a friendly and helpful personal AI assistant. 
You have a warm, professional, and slightly conversational personality.
You help with tasks, answer questions, and engage in natural conversations.
Keep responses concise but friendly. Use natural speech patterns."""
        )
        
        # Language detection and TTS model selection
        self.current_language = "en"  # Track current language
        self.greek_piper_model = self.config.get("greek_piper_model", "el_GR-rapunzelina-low")
        self._audio_file_counter = 0  # Counter for unique audio filenames
        self._audio_file_lock = threading.Lock()  # Lock for thread-safe counter
        
        # Initialize conversation (will update with language detection)
        self.system_prompt = self.base_system_prompt
        self.add_system_message(self.system_prompt)
        
        print("🌟 Daisy is ready!")
        print(f"🧠 LLM Model: {self.config.get('llm_model', 'gpt-3.5-turbo')}")
        
        # Show TTS engine status
        tts_engine = self.config.get('tts_engine', 'piper')
        print(f"🔊 TTS Engine: {tts_engine}")
        if tts_engine == "piper":
            if self.piper_available:
                print(f"   ✅ Piper TTS: Available (fast, high-quality open-source)")
            else:
                print(f"   ⚠️  Piper TTS: Not installed (install: brew install piper-tts)")
        elif tts_engine == "coqui":
            if self.coqui_available:
                print(f"   ✅ Coqui TTS: Available (high-quality neural TTS)")
            else:
                print(f"   ⚠️  Coqui TTS: Not installed (install: pip install TTS)")
        elif tts_engine == "openai":
            print(f"   ✅ OpenAI TTS: Available (cloud-based, high quality)")
        else:
            print(f"   ✅ macOS say: Using {self.config.get('say_voice', 'Samantha')} voice")
        
        # Show speech recognition status
        if self.groq_client:
            print(f"🎤 Speech Recognition: Groq Whisper (whisper-large-v3-turbo)")
            print(f"   ✅ Excellent at understanding whispers and quiet speech")
            if self.groq_working_model:
                print(f"   💬 LLM Fallback: Groq {self.groq_working_model} (cached)")
        else:
            print(f"⚠️  Speech Recognition: Groq not available (using OpenAI/Google fallback)")
            print(f"   💡 Set GROQ_API_KEY for better speech recognition (like Praiser)")
    
    def load_config(self) -> Dict:
        """Load configuration"""
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                return json.load(f)
        return self.create_default_config()
    
    def create_default_config(self) -> Dict:
        """Create default configuration"""
        config = {
            "openai_api_key": "",
            "groq_api_key": "",  # Required for Groq Whisper (better speech recognition)
            "llm_model": "gpt-3.5-turbo",  # Default to gpt-3.5-turbo (more accessible than gpt-4)
            "tts_engine": "piper",  # piper (fast, open-source), coqui (high-quality), openai (cloud), say (macOS fallback)
            "voice": "shimmer",  # For OpenAI TTS: shimmer is more expressive and human-like (nova is also good)
            "voice_speed": 0.95,  # Slightly slower for more natural speech (0.9-1.0 range)
            "tts_model": "tts-1-hd",  # For OpenAI TTS: Higher quality for more human-like voice
            "piper_model": "en_US-lessac-high",  # Piper TTS model (download from https://github.com/rhasspy/piper/releases)
            "coqui_model": "tts_models/en/ljspeech/tacotron2-DDC",  # Coqui TTS model
            "say_voice": "Samantha",  # macOS say command voice (Samantha, Karen, etc.)
            "system_prompt": """You are Daisy, a friendly and helpful personal AI assistant. 
You have a warm, professional, and slightly conversational personality.
You help with tasks, answer questions, and engage in natural conversations.
Keep responses concise but friendly. Use natural speech patterns with pauses, 
variations in tone, and conversational flow. Speak like a real person would, 
with natural rhythm and emphasis.""",
            "conversation_mode": "continuous",
            "wake_word": "daisy",
            "auto_listen": True,
            "save_conversations": True,
        }
        self.save_config(config)
        return config
    
    def save_config(self, config: Optional[Dict] = None):
        """Save configuration"""
        if config:
            self.config = config
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def setup_directories(self):
        """Create necessary directories"""
        dirs = [
            Path.home() / ".daisy",
            Path.home() / ".daisy" / "conversations",
            Path.home() / ".daisy" / "audio",
            Path.home() / ".daisy" / "logs",
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)
    
    def add_message(self, role: str, content: str):
        """Add a message to conversation history"""
        message = ConversationMessage(
            role=role,
            content=content,
            timestamp=datetime.now().isoformat()
        )
        self.conversation_history.append(message)
        
        # Keep history within limit
        if len(self.conversation_history) > self.max_history:
            # Keep system message, remove oldest non-system messages
            system_msgs = [m for m in self.conversation_history if m.role == 'system']
            other_msgs = [m for m in self.conversation_history if m.role != 'system']
            self.conversation_history = system_msgs + other_msgs[-self.max_history+1:]
    
    def add_system_message(self, content: str):
        """Add system message"""
        self.add_message('system', content)
    
    def get_conversation_context(self) -> List[Dict]:
        """Get conversation context for LLM"""
        return [
            {"role": msg.role, "content": msg.content}
            for msg in self.conversation_history
        ]
    
    def fetch_groq_models(self) -> List[str]:
        """
        Fetch models dynamically from Groq API (PROVEN - matches Praiser implementation)
        No hardcoded models - API key determines what's available
        """
        # Check cache first (1 hour TTL like Praiser)
        now = time.time()
        if (self.groq_models_cache and 
            now - self.groq_models_cache_time < self.GROQ_CACHE_TTL):
            return self.groq_models_cache
        
        groq_api_key = os.getenv("GROQ_API_KEY") or self.config.get("groq_api_key")
        if not groq_api_key:
            return []
        
        try:
            # PROVEN WORKING: Direct HTTP call (same as Praiser)
            response = requests.get(
                "https://api.groq.com/openai/v1/models",
                headers={
                    "Authorization": f"Bearer {groq_api_key}",
                    "Content-Type": "application/json",
                },
                timeout=10
            )
            
            if not response.ok:
                raise Exception(f"Groq API error: {response.status_code}")
            
            data = response.json()
            all_models = [model["id"] for model in data.get("data", [])]
            
            # Filter out non-conversation models (TTS, guard, whisper, compound)
            exclude_patterns = ["tts", "whisper", "guard", "compound", "decommissioned"]
            conversation_models = [
                m for m in all_models
                if not any(pattern in m.lower() for pattern in exclude_patterns)
            ]
            
            # Smart sorting: Larger/newer models first (no hardcoded list)
            def model_priority(model: str) -> tuple:
                """Sort by size, version, type - dynamically"""
                m = model.lower()
                # Size (larger = better)
                size = 0
                for val in [120, 70, 32, 20, 17, 8]:
                    if str(val) in m or f"{val}b" in m:
                        size = val
                        break
                # Version (newer = better)
                version = 3 if "3.3" in m else (2 if "3.1" in m else (1 if "3" in m else 0))
                # Type (versatile > instant > others)
                type_score = 2 if "versatile" in m else (1 if "instant" in m else 0)
                return (-size, -version, -type_score)
            
            sorted_models = sorted(conversation_models, key=model_priority)
            
            # Cache result
            self.groq_models_cache = sorted_models
            self.groq_models_cache_time = now
            
            print(f"✅ Fetched {len(sorted_models)} Groq models dynamically")
            if sorted_models:
                print(f"   Top model: {sorted_models[0]}")
            return sorted_models
            
        except Exception as e:
            print(f"⚠️  Failed to fetch Groq models: {e}")
            return []
    
    def get_groq_response(self, messages: List[Dict]) -> str:
        """Get response from Groq - use cached working model (re-check every hour)"""
        if not self.groq_client:
            return "I'm sorry, Groq is not available."
        
        # Check if we have a cached working model
        now = time.time()
        use_cached_model = False
        
        if self.groq_working_model:
            # Check if cache is still valid (1 hour)
            # Handle case where check_time might be 0 or None
            check_time = self.groq_model_check_time or 0
            if check_time > 0 and (now - check_time < self.GROQ_MODEL_CHECK_INTERVAL):
                # Use cached working model directly - no searching!
                use_cached_model = True
                print(f"💡 Using cached Groq model: {self.groq_working_model}")
                
                # Try the cached model first
                try:
                    response = self.groq_client.chat.completions.create(
                        model=self.groq_working_model,
                        messages=messages,
                        temperature=0.7,
                        max_tokens=500
                    )
                    
                    assistant_message = response.choices[0].message.content
                    # Handle None or empty response
                    if not assistant_message or assistant_message.strip() == "":
                        assistant_message = "I'm sorry, I couldn't generate a response. Please try again."
                    elif not isinstance(assistant_message, str):
                        assistant_message = str(assistant_message)
                    
                    # Update cache time
                    self.groq_model_check_time = time.time()
                    self.config["groq_model_check_time"] = self.groq_model_check_time
                    self.save_config()
                    
                    self.add_message('assistant', assistant_message)
                    print(f"✅ Response from Groq ({self.groq_working_model})")
                    return assistant_message
                except Exception as e:
                    # Cached model failed - clear cache and search for new one
                    error_str = str(e)
                    if any(x in error_str.lower() for x in ["404", "model_not_found", "decommissioned"]):
                        print(f"⚠️  Cached model {self.groq_working_model} no longer available - searching for new one...")
                    else:
                        print(f"⚠️  Cached model {self.groq_working_model} failed - searching for new one...")
                    self.groq_working_model = None
                    use_cached_model = False
        
        # No cached model or cache expired - fetch and try models
        if not use_cached_model:
            # Fetch models dynamically (no hardcoding)
            models = self.fetch_groq_models()
            if not models:
                return "I'm sorry, no Groq models are available."
            
            last_error = None
            
            # Try each model until one works
            for model in models:
                try:
                    print(f"🔄 Trying Groq model: {model}")
                    
                    # PROVEN WORKING: Use Groq SDK for chat (same as Praiser)
                    response = self.groq_client.chat.completions.create(
                        model=model,
                        messages=messages,
                        temperature=0.7,
                        max_tokens=500
                    )
                    
                    assistant_message = response.choices[0].message.content
                    # Handle None or empty response
                    if not assistant_message or assistant_message.strip() == "":
                        assistant_message = "I'm sorry, I couldn't generate a response. Please try again."
                    elif not isinstance(assistant_message, str):
                        assistant_message = str(assistant_message)
                    
                    # Cache this working model for 1 hour (save to config)
                    self.groq_working_model = model
                    self.groq_model_check_time = time.time()
                    self.config["groq_working_model"] = model
                    self.config["groq_model_check_time"] = self.groq_model_check_time
                    self.save_config()
                    
                    self.add_message('assistant', assistant_message)
                    print(f"✅ Response from Groq ({model}) - cached for 1 hour")
                    return assistant_message
                        
                except Exception as e:
                    last_error = e
                    error_str = str(e)
                    
                    # Skip model if not found or decommissioned
                    if any(x in error_str.lower() for x in ["404", "model_not_found", "decommissioned"]):
                        print(f"⚠️  Model {model} not available, trying next...")
                        continue
                    # Try next on rate limit
                    if any(x in error_str.lower() for x in ["429", "rate_limit", "503", "over capacity"]):
                        print(f"⚠️  Model {model} rate limited, trying next...")
                        continue
                    # Other errors - still try next
                    print(f"⚠️  Model {model} error, trying next...")
                    continue
            
            # All models failed - clear working model cache
            self.groq_working_model = None
            self.groq_model_check_time = 0
            if "groq_working_model" in self.config:
                del self.config["groq_working_model"]
            if "groq_model_check_time" in self.config:
                del self.config["groq_model_check_time"]
            self.save_config()
            
            error_msg = f"I'm sorry, all Groq models failed. Last error: {str(last_error)[:100] if last_error else 'Unknown'}"
            self.add_message('assistant', error_msg)
            return error_msg
    
    def stop_speaking(self):
        """Immediately stop Daisy from speaking (interrupt)"""
        if not self.is_speaking:
            return
        
        self.is_speaking = False
        self.interrupt_detected = True
        self.interrupt_event.set()  # Signal interrupt event
        self.interrupt_time = time.time()  # Record interrupt time for cooldown
        print("\n🔇 [Stopping speech...]")
        
        # Kill the current audio process FIRST (most important)
        if self.current_audio_process and self.current_audio_process.poll() is None:
            try:
                # Terminate the process
                self.current_audio_process.terminate()
                try:
                    self.current_audio_process.wait(timeout=0.2)
                except:
                    pass
            except:
                pass
                
            # Force kill if still running
            if self.current_audio_process and self.current_audio_process.poll() is None:
                try:
                    self.current_audio_process.kill()
                    self.current_audio_process.wait(timeout=0.1)
                except:
                    pass
        
        # Kill ALL say processes (force kill with -9 signal) - do this multiple times
        for _ in range(2):  # Try twice to make sure
            try:
                subprocess.run(["pkill", "-9", "say"], check=False,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except:
                pass
            time.sleep(0.1)  # Small delay between attempts
        
        # Kill afplay processes too (force kill) - try multiple times
        for _ in range(2):
            try:
                subprocess.run(["pkill", "-9", "afplay"], check=False, 
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except:
                pass
            time.sleep(0.1)
        
        self.current_audio_process = None
        print("✅ [Speech stopped - ready to listen]")
    
    def _check_piper_available(self) -> bool:
        """Check if Piper TTS is available"""
        try:
            # Try importing directly (more reliable)
            try:
                from piper import PiperVoice
                print("✅ Piper TTS: Direct import successful")
                return True
            except ImportError as e:
                print(f"⚠️  Piper TTS: Direct import failed: {e}")
                pass
            
            # Fallback: check if piper command-line tool is available
            result = subprocess.run(
                ["which", "piper"],
                capture_output=True,
                check=False
            )
            if result.returncode == 0:
                print("✅ Piper TTS: Command-line tool found")
                return True
            
            # Also check if piper Python package is available via subprocess
            result = subprocess.run(
                ["python3", "-c", "import piper"],
                capture_output=True,
                check=False
            )
            if result.returncode == 0:
                print("✅ Piper TTS: Subprocess import successful")
                return True
            else:
                stderr = result.stderr.decode() if result.stderr else ""
                print(f"⚠️  Piper TTS: Subprocess import failed: {stderr[:100]}")
            return False
        except Exception as e:
            print(f"⚠️  Piper TTS: Check exception: {e}")
            return False
    
    def _check_coqui_available(self) -> bool:
        """Check if Coqui TTS is available"""
        try:
            result = subprocess.run(
                ["python3", "-c", "import TTS"],
                capture_output=True,
                check=False
            )
            return result.returncode == 0
        except:
            return False
    
    def _piper_tts(self, text: str) -> Optional[str]:
        """Generate speech using Piper TTS (fast, high-quality open-source TTS)"""
        try:
            audio_dir = Path.home() / ".daisy" / "audio"
            # Use thread-safe counter to ensure unique filenames even when multiple threads call simultaneously
            with self._audio_file_lock:
                self._audio_file_counter += 1
                counter = self._audio_file_counter
            audio_file = audio_dir / f"daisy_piper_{int(time.time())}_{counter}.wav"
            
            # Detect language and use appropriate model
            detected_lang = self.detect_language(text)
            if detected_lang == "el":
                # Use Greek model
                model_name = self.config.get("greek_piper_model", "el_GR-rapunzelina-low")
                print(f"🇬🇷 Using Greek Piper TTS model: {model_name}")
            else:
                # Use English model
                model_name = self.config.get("piper_model", "en_US-lessac-high")
                print(f"🇺🇸 Using English Piper TTS model: {model_name}")
            
            # Try Python piper package first (easier to use)
            try:
                from piper import PiperVoice
                
                # Try to find model in common locations
                possible_model_paths = [
                    (Path.home() / ".local" / "share" / "piper" / "voices" / f"{model_name}.onnx", 
                     Path.home() / ".local" / "share" / "piper" / "voices" / f"{model_name}.onnx.json"),
                    (Path.home() / ".local" / "share" / "piper" / "voices" / f"{model_name}" / "model.onnx",
                     Path.home() / ".local" / "share" / "piper" / "voices" / f"{model_name}" / "config.json"),
                    (Path("/usr/local/share/piper/voices") / f"{model_name}.onnx",
                     Path("/usr/local/share/piper/voices") / f"{model_name}.onnx.json"),
                    (Path("/opt/homebrew/share/piper/voices") / f"{model_name}.onnx",
                     Path("/opt/homebrew/share/piper/voices") / f"{model_name}.onnx.json"),
                ]
                
                model_path = None
                config_path = None
                for model, config in possible_model_paths:
                    if model.exists():
                        model_path = str(model)
                        if config.exists():
                            config_path = str(config)
                        else:
                            # Config might be in same directory with .json extension
                            config_path = str(model) + ".json"
                        break
                
                if model_path and Path(model_path).exists():
                    # Use Python package
                    voice = PiperVoice.load(model_path, config_path=config_path if Path(config_path).exists() else None)
                    # Synthesize returns iterable of AudioChunk
                    audio_chunks = voice.synthesize(text)
                    
                    # Collect all audio data first
                    all_audio_data = b""
                    sample_rate = None
                    sample_width = None
                    sample_channels = None
                    
                    for audio_chunk in audio_chunks:
                        # Get audio data and metadata from first chunk
                        if sample_rate is None:
                            sample_rate = audio_chunk.sample_rate
                            sample_width = audio_chunk.sample_width
                            sample_channels = audio_chunk.sample_channels
                        # AudioChunk has audio_int16_bytes attribute (not audio_bytes)
                        all_audio_data += audio_chunk.audio_int16_bytes
                    
                    # Write proper WAV file with headers
                    import wave
                    import struct
                    
                    with wave.open(str(audio_file), 'wb') as wav_file:
                        wav_file.setnchannels(sample_channels or 1)
                        wav_file.setsampwidth(sample_width or 2)
                        wav_file.setframerate(sample_rate or 22050)
                        wav_file.writeframes(all_audio_data)
                    
                    if audio_file.exists():
                        return str(audio_file)
                else:
                    # Model not found - will try command-line fallback
                    # Don't print error here - let command-line fallback handle it
                    pass
            except ImportError:
                pass  # Python package not available, try command-line
            except Exception as e:
                print(f"⚠️  Piper TTS Python package error: {e}")
                import traceback
                traceback.print_exc()
            
            # Fallback: Try piper command-line tool
            # Try to find model in common locations
            possible_model_paths = [
                Path.home() / ".local" / "share" / "piper" / "voices" / f"{model_name}.onnx",
                Path.home() / ".local" / "share" / "piper" / "voices" / f"{model_name}" / "model.onnx",
                Path("/usr/local/share/piper/voices") / f"{model_name}.onnx",
                Path("/opt/homebrew/share/piper/voices") / f"{model_name}.onnx",
            ]
            
            model_path = None
            for path in possible_model_paths:
                if path.exists():
                    model_path = str(path)
                    break
            
            # If no model file found, try using just the model name (piper might find it)
            if not model_path:
                print(f"⚠️  Piper model '{model_name}' not found in standard locations.")
                print(f"   Searched: {[str(p) for p in possible_model_paths]}")
                print(f"   Please download the model from: https://github.com/rhasspy/piper/releases")
                print(f"   Or install it using: python3 -m piper.download_voices {model_name}")
                model_path = model_name  # Try anyway - piper might find it
            
            # Try piper command with stdin
            process = subprocess.Popen(
                ["piper", "--model", model_path, "--output_file", str(audio_file)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate(input=text, timeout=30)
            
            if process.returncode == 0 and audio_file.exists():
                return str(audio_file)
            else:
                if stderr:
                    print(f"⚠️  Piper TTS error: {stderr[:200]}")
                return None
                
        except subprocess.TimeoutExpired:
            print("⚠️  Piper TTS timeout")
            return None
        except FileNotFoundError:
            print("⚠️  Piper TTS not found. Install with: pip3 install piper-tts")
            return None
        except Exception as e:
            print(f"⚠️  Piper TTS error: {e}")
            return None
    
    def _coqui_tts(self, text: str) -> Optional[str]:
        """Generate speech using Coqui TTS (high-quality neural TTS)"""
        try:
            from TTS.api import TTS
            
            audio_dir = Path.home() / ".daisy" / "audio"
            # Use thread-safe counter to ensure unique filenames
            with self._audio_file_lock:
                self._audio_file_counter += 1
                counter = self._audio_file_counter
            audio_file = audio_dir / f"daisy_coqui_{int(time.time())}_{counter}.wav"
            
            # Use a good quality female voice
            # tts_models/en/ljspeech/tacotron2-DDC is a good option
            model_name = self.config.get("coqui_model", "tts_models/en/ljspeech/tacotron2-DDC")
            
            tts = TTS(model_name=model_name)
            tts.tts_to_file(text=text, file_path=str(audio_file))
            
            if audio_file.exists():
                return str(audio_file)
            return None
            
        except Exception as e:
            print(f"⚠️  Coqui TTS error: {e}")
            return None
    
    def _process_text_for_natural_speech(self, text: str) -> str:
        """Minimal text cleaning - let TTS handle prosody naturally (like ChatGPT Voice)"""
        # Handle None or non-string input
        if text is None:
            return "I'm sorry, I couldn't generate a response."
        if not isinstance(text, str):
            text = str(text)
        if not text.strip():
            return "I'm sorry, I couldn't understand that."
        
        # Remove emojis - TTS engines try to read them as words (e.g., "smiley face")
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags (iOS)
            "\U00002702-\U000027B0"  # dingbats
            "\U000024C2-\U0001F251"  # enclosed characters
            "\U0001F900-\U0001F9FF"  # supplemental symbols
            "\U0001FA00-\U0001FA6F"  # chess symbols
            "\U0001FA70-\U0001FAFF"  # symbols and pictographs extended-A
            "\U00002600-\U000026FF"  # miscellaneous symbols
            "\U00002700-\U000027BF"  # dingbats
            "]+",
            flags=re.UNICODE
        )
        text = emoji_pattern.sub('', text)  # Remove all emojis
        
        # Remove markdown tables (lines with pipes)
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            # Skip markdown table rows (lines with multiple pipes)
            if line.count('|') >= 2:
                continue
            # Skip markdown table separators (lines with dashes and pipes)
            if re.match(r'^[\s\|:\-]+$', line):
                continue
            cleaned_lines.append(line)
        text = '\n'.join(cleaned_lines)
        
        # Remove markdown formatting
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # Remove **bold**
        text = re.sub(r'\*(.*?)\*', r'\1', text)  # Remove *italic*
        text = re.sub(r'__(.*?)__', r'\1', text)  # Remove __bold__
        text = re.sub(r'_(.*?)_', r'\1', text)  # Remove _italic_
        text = re.sub(r'~~(.*?)~~', r'\1', text)  # Remove ~~strikethrough~~
        text = re.sub(r'`(.*?)`', r'\1', text)  # Remove `code`
        text = re.sub(r'```[\s\S]*?```', '', text)  # Remove code blocks
        text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)  # Remove # headers
        
        # Remove special characters that TTS tries to read as words
        text = re.sub(r'[*#_~`|]', '', text)  # Remove *, #, _, ~, `, |
        
        # Remove bullet points and list markers
        text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)  # Remove - * + bullets
        text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)  # Remove numbered lists
        
        # Clean whitespace (but preserve natural spacing - don't manipulate punctuation)
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)  # Remove multiple blank lines
        text = re.sub(r'[ \t]+', ' ', text)  # Multiple spaces/tabs to single space
        
        # DON'T add pauses or manipulate punctuation - let TTS handle prosody naturally!
        # Modern TTS models (Piper, OpenAI TTS) handle prosody much better than regex manipulation
        
        return text.strip()
    
    def text_to_speech(self, text: str) -> Optional[bytes]:
        """Convert text to speech using best available TTS engine (interruptible)"""
        # Stop any currently playing audio
        self.stop_speaking()
        
        # Process text for more natural speech patterns
        processed_text = self._process_text_for_natural_speech(text)
        
        # Determine which TTS engine to use
        tts_engine = self.config.get("tts_engine", "piper")
        print(f"🔊 TTS Engine selected: {tts_engine} (piper_available: {self.piper_available})")
        
        # Try Piper TTS first (fast, high-quality, open-source)
        if tts_engine == "piper":
            if self.piper_available:
                print("🔊 Using Piper TTS...")
                audio_file = self._piper_tts(processed_text)
                if audio_file:
                    print(f"✅ Piper TTS generated audio: {audio_file}")
                    return self._play_audio_file(audio_file)
                else:
                    print("⚠️  Piper TTS failed, trying fallback...")
            else:
                print("⚠️  Piper TTS not available, trying fallback...")
        
        # Try Coqui TTS (high-quality neural TTS)
        if (tts_engine == "coqui" or (tts_engine == "piper" and not self.piper_available)) and self.coqui_available:
            audio_file = self._coqui_tts(processed_text)
            if audio_file:
                return self._play_audio_file(audio_file)
            else:
                print("⚠️  Coqui TTS failed, trying fallback...")
        
        # Try OpenAI TTS (only if explicitly set or if no other options available)
        if tts_engine == "openai":
            try:
                # Use shimmer voice for more natural, expressive sound (more human-like)
                voice = self.config.get("voice", "shimmer")  # shimmer is more expressive/natural
                # Slightly slower speed for more natural speech (0.95-1.0)
                speed = self.config.get("voice_speed", 0.95)
                # Use HD model for more human-like quality
                tts_model = self.config.get("tts_model", "tts-1-hd")
            
                # Check if we've cached quota exceeded for TTS
                now = time.time()
                if self.openai_quota_exceeded and (now - self.quota_check_time < self.QUOTA_CHECK_INTERVAL):
                    # Skip OpenAI TTS, use fallback directly
                    raise Exception("Quota exceeded (cached)")
                
                if not self.client:
                    raise Exception("OpenAI client not available")
            
                # Use tts-1-hd for higher quality, more human-like voice
                response = self.client.audio.speech.create(
                model=tts_model,  # Higher quality for more natural, human-like voice
                voice=voice,
                input=processed_text,
                speed=speed
                )
            
                # Save audio file
                audio_dir = Path.home() / ".daisy" / "audio"
                # Use thread-safe counter to ensure unique filenames
                with self._audio_file_lock:
                    self._audio_file_counter += 1
                    counter = self._audio_file_counter
                audio_file = audio_dir / f"daisy_{int(time.time())}_{counter}.mp3"
            
                    # Write audio to file
                audio_data = b""
                for chunk in response.iter_bytes():
                    audio_data += chunk
                
                with open(audio_file, 'wb') as f:
                    f.write(audio_data)
                
                return self._play_audio_file(str(audio_file))
                
            except Exception as e:
                error_str = str(e)
                # Check for quota errors
                if "429" in error_str or "quota" in error_str.lower() or "insufficient_quota" in error_str:
                    self.openai_quota_exceeded = True
                    self.quota_check_time = time.time()
                    print("⚠️  OpenAI TTS quota exceeded - using fallback")
                else:
                    print(f"⚠️  OpenAI TTS Error: {e} - using fallback")
        
        # Final fallback: macOS say command (but with better voice options)
        return self._say_tts_fallback(processed_text)
    
    def _play_audio_file(self, audio_file: str) -> Optional[bytes]:
        """Play an audio file and return audio data (interruptible)"""
        try:
            audio_path = Path(audio_file)
            if not audio_path.exists():
                return None
            
            # Play audio using macOS afplay (interruptible)
            self.is_speaking = True
            # Reset interrupt flags before starting
            self.interrupt_event.clear()
            self.interrupt_detected = False
            self.current_audio_process = subprocess.Popen(
                ["afplay", str(audio_path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE
            )
            
            # Set up keyboard interrupt detection (like 0.2.copy)
            import sys
            import select
            import termios
            import tty
            
            old_settings = None
            try:
                if sys.stdin.isatty():
                    old_settings = termios.tcgetattr(sys.stdin)
                    # Set to non-blocking raw mode for single character input
                    tty.setcbreak(sys.stdin.fileno())
            except:
                old_settings = None
            
            # Poll while playing (so we can interrupt) - check more frequently like 0.2.copy
            start_time = time.time()
            max_duration = 300  # Max 5 minutes per response
            
            try:
                # Always enter the loop - check process inside
                while self.current_audio_process and self.current_audio_process.poll() is None:
                    # Check for keyboard interrupt FIRST (works while audio is playing)
                    try:
                        if sys.stdin.isatty() and old_settings is not None:
                            # Check if any key was pressed (non-blocking, 50ms timeout)
                            ready, _, _ = select.select([sys.stdin], [], [], 0.05)
                            if ready:
                                # Key pressed - interrupt immediately
                                char = sys.stdin.read(1)
                                print(f"\n⌨️  [KEY PRESSED! - Stopping immediately...]")
                                self.stop_speaking()
                                break
                    except (OSError, ValueError, KeyboardInterrupt):
                        # Terminal errors - just use flags instead
                        pass
                    except Exception:
                        pass  # Ignore other errors
                    
                    # Check for interrupt event or flags - MUST check is_speaking flag
                    if not self.is_speaking or self.interrupt_event.is_set() or self.interrupt_detected:
                        # Was interrupted - stop audio process immediately
                        print("🔇 [Audio playback interrupted - stopping now]")
                        # Force kill the audio process
                        if self.current_audio_process and self.current_audio_process.poll() is None:
                            try:
                                self.current_audio_process.terminate()
                                time.sleep(0.05)  # Very short wait
                                if self.current_audio_process.poll() is None:
                                    self.current_audio_process.kill()
                                    time.sleep(0.05)
                            except:
                                pass
                        # Also kill all say/afplay processes immediately
                        try:
                            subprocess.run(["pkill", "-9", "say"], check=False,
                                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                            subprocess.run(["pkill", "-9", "afplay"], check=False,
                                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        except:
                            pass
                        break
                    
                    # Check if audio is taking too long (might be stuck)
                    if time.time() - start_time > max_duration:
                        print("⚠️  [Audio playback taking too long - stopping]")
                        self.stop_speaking()
                        break
                    
                    time.sleep(0.05)  # Check every 50ms (more frequent like 0.2.copy)
            finally:
                # Restore terminal settings
                if old_settings:
                    try:
                        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
                    except:
                        pass
            
            self.is_speaking = False
            self.interrupt_event.clear()  # Reset interrupt event for next time
            if self.current_audio_process:
                self.current_audio_process = None
            
            # Read audio data if it's an MP3 (for potential future use)
            audio_data = b""
            if audio_path.suffix == ".mp3":
                with open(audio_path, 'rb') as f:
                    audio_data = f.read()
            
            # Clean up audio file after a delay (optional)
            threading.Timer(10.0, lambda: audio_path.unlink() if audio_path.exists() else None).start()
            
            return audio_data
            
        except Exception as e:
            print(f"⚠️  Error playing audio file: {e}")
            import traceback
            traceback.print_exc()
            self.is_speaking = False
            if self.current_audio_process:
                try:
                    self.current_audio_process.terminate()
                except:
                    pass
                self.current_audio_process = None
            return None
    
    def _say_tts_fallback(self, text: str) -> Optional[bytes]:
        """Fallback to macOS say command with better voice options"""
        # Always fallback to macOS say with female voice (interruptible)
        # Set is_speaking flag BEFORE opening audio stream (so VAD thread can detect it)
        self.is_speaking = True
        # Reset interrupt flags
        self.interrupt_event.clear()
        self.interrupt_detected = False
        
        # Use the most natural female voice on macOS
        # Samantha is the most natural-sounding, Karen is more expressive
        # Try Samantha first (most human-like), fallback to Karen
        fallback_voice = self.config.get("say_voice", "Samantha")
        
        # Use natural voice with human-like rate and pitch
        # Rate 165: natural conversational speed (not too fast, not too slow)
        # Pitch 52: natural female pitch (slightly higher = more expressive)
        # These settings create a more human-like, conversational tone
        # IMPORTANT: Don't redirect stderr - let errors show, and don't use DEVNULL for say command
        try:
            self.current_audio_process = subprocess.Popen(
                ["say", "-v", fallback_voice, "-r", "165", text],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE
            )
        except Exception as say_error:
            print(f"⚠️  Error with say command: {say_error}")
            # Try without rate parameter as fallback
            try:
                self.current_audio_process = subprocess.Popen(
                    ["say", "-v", fallback_voice, text],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE
                )
            except Exception as say_error2:
                print(f"❌ Cannot use macOS say command: {say_error2}")
                self.is_speaking = False
                self.current_audio_process = None
                return None
        
        # Wait for audio to finish playing (interruptible)
        # Poll instead of blocking wait, so we can check for interrupts
        start_time = time.time()
        max_duration = 300  # Max 5 minutes per response
        
        # Also check for keyboard input in this loop (most reliable place)
        import sys
        import select
        
        # Set stdin to non-blocking mode for keyboard detection
        old_settings = None
        import termios
        import tty
        try:
            if sys.stdin.isatty():
                old_settings = termios.tcgetattr(sys.stdin)
                # Set to non-blocking raw mode for single character input
                tty.setcbreak(sys.stdin.fileno())
        except:
            old_settings = None
        
        try:
            # Always enter the loop - check process inside
            while self.current_audio_process and self.current_audio_process.poll() is None:
                # Check for keyboard interrupt FIRST (works while audio is playing)
                try:
                    if sys.stdin.isatty() and old_settings is not None:
                        # Check if any key was pressed (non-blocking, 50ms timeout)
                        ready, _, _ = select.select([sys.stdin], [], [], 0.05)
                        if ready:
                            # Key pressed - interrupt immediately
                            char = sys.stdin.read(1)
                            print(f"\n⌨️  [KEY PRESSED! - Stopping immediately...]")
                            self.stop_speaking()
                            break
                except (OSError, ValueError, KeyboardInterrupt):
                    # Terminal errors - just use flags instead
                    pass
                except Exception:
                    pass  # Ignore other errors
                
                # Check for interrupt event or flags - MUST check is_speaking flag first
                if not self.is_speaking or self.interrupt_event.is_set() or self.interrupt_detected:
                    # Was interrupted - stop audio process immediately
                    print("🔇 [Audio playback interrupted - stopping now]")
                    # Force kill the audio process
                    if self.current_audio_process and self.current_audio_process.poll() is None:
                        try:
                            self.current_audio_process.terminate()
                            time.sleep(0.05)  # Very short wait
                            if self.current_audio_process.poll() is None:
                                self.current_audio_process.kill()
                                time.sleep(0.05)
                        except:
                            pass
                    # Also kill all say/afplay processes immediately
                    try:
                        subprocess.run(["pkill", "-9", "say"], check=False,
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        subprocess.run(["pkill", "-9", "afplay"], check=False,
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    except:
                        pass
                    break
                
                # Check if audio is taking too long (might be stuck)
                if time.time() - start_time > max_duration:
                    print("⚠️  [Audio playback taking too long - stopping]")
                    self.stop_speaking()
                    break
                
                time.sleep(0.05)  # Check every 50ms (more frequent like 0.2.copy)
        finally:
            # Restore terminal settings
            if old_settings:
                try:
                    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
                except:
                    pass
        
        # Check if process completed successfully
        if self.current_audio_process and self.current_audio_process.returncode != 0:
            # Process failed - check stderr for errors
            try:
                stderr_output = self.current_audio_process.stderr.read().decode() if self.current_audio_process.stderr else ""
                if stderr_output:
                    print(f"⚠️  Audio playback error: {stderr_output[:100]}")
            except:
                pass
        
        self.is_speaking = False
        self.interrupt_event.clear()  # Reset interrupt event for next time
        if self.current_audio_process:
            self.current_audio_process = None
        return None
    
    def listen_for_voice(self, timeout: int = 5, interruptible: bool = True) -> Optional[str]:
        """Listen for voice input and convert to text using Groq Whisper (like Praiser) - can interrupt while Daisy is speaking"""
        if not self.microphone:
            return None
        
        # Check if we just interrupted - ignore audio for cooldown period
        now = time.time()
        if self.interrupt_time > 0 and (now - self.interrupt_time < self.INTERRUPT_COOLDOWN):
            remaining = self.INTERRUPT_COOLDOWN - (now - self.interrupt_time)
            print(f"⏸️  [Interrupt cooldown - ignoring audio for {remaining:.1f}s]")
            return None
        
        # If Daisy is speaking and interrupt detected, don't listen
        if self.is_speaking and self.interrupt_detected:
            print("🔇 [Interrupted]")
            return None
            
        try:
            with self.microphone as source:
                print("🎤 Listening...")
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=10)
            
            print("🔄 Processing speech with Groq Whisper...")
            
            # Use Groq Whisper (PROVEN WORKING - same as Praiser)
            # Groq Whisper is much better at understanding whispers and quiet speech
            if self.groq_client:
                try:
                    # Convert audio to format Groq expects
                    audio_data = io.BytesIO(audio.get_wav_data())
                    audio_data.name = "audio.wav"
                    
                    # Use whisper-large-v3-turbo (same model as Praiser uses)
                    transcript = self.groq_client.audio.transcriptions.create(
                        file=audio_data,
                        model="whisper-large-v3-turbo",
                        response_format="json",
                        temperature=0.2,  # Lower temperature for more accurate transcription
                    )
                    text = transcript.text
                    print(f"✅ Groq Whisper transcription successful")
                except Exception as e:
                    error_str = str(e)
                    print(f"⚠️  Groq Whisper failed: {error_str[:100]}")
                    # Fallback to Google Speech Recognition
                    try:
                        text = self.recognizer.recognize_google(audio)
                        print("💡 Using Google Speech (Groq fallback)")
                    except Exception as google_error:
                        print(f"❌ Google Speech also failed: {google_error}")
                        return None
            else:
                # No Groq client - try OpenAI Whisper as fallback
                if self.client:
                    try:
                        audio_data = io.BytesIO(audio.get_wav_data())
                        audio_data.name = "audio.wav"
                        transcript = self.client.audio.transcriptions.create(
                            model="whisper-1",
                            file=audio_data,
                            language="en"
                        )
                        text = transcript.text
                        print("💡 Using OpenAI Whisper (Groq not available)")
                    except Exception as e:
                        error_str = str(e)
                        print(f"⚠️  OpenAI Whisper failed: {error_str[:100]}")
                        # Final fallback to Google
                        try:
                            text = self.recognizer.recognize_google(audio)
                            print("💡 Using Google Speech (final fallback)")
                        except Exception as google_error:
                            print(f"❌ All speech recognition failed: {google_error}")
                            return None
                else:
                    # No API clients available - use Google
                    try:
                        text = self.recognizer.recognize_google(audio)
                        print("💡 Using Google Speech (no API clients)")
                    except Exception as google_error:
                        print(f"❌ Google Speech failed: {google_error}")
                        return None
            
            # Check if user wants to interrupt/stop Daisy
            text_lower = text.lower().strip()
            interrupt_commands = ["stop", "stop speaking", "stop talking", "quiet", "shush", "enough"]
            
            if interruptible and any(cmd in text_lower for cmd in interrupt_commands):
                # User wants to interrupt - stop speaking immediately
                self.stop_speaking()
                print("🔇 [Interrupted]")
                # Don't add this to conversation history, just return None to continue listening
                return None
            
            print(f"👤 You: {text}")
            # Debug: Show if this looks like it might be keyboard noise
            if len(text) < 5 and text.lower() in ['thank you', 'thanks', 'ok', 'okay', 'so']:
                print(f"⚠️  [Short common phrase detected - might be keyboard noise or echo]")
            return text
            
        except sr.WaitTimeoutError:
            print("⏱️  Listening timeout")
            return None
        except sr.UnknownValueError:
            print("❓ Could not understand audio")
            return None
        except Exception as e:
            print(f"❌ Error recognizing speech: {e}")
            return None
    
    def listen_while_speaking(self) -> Optional[str]:
        """Listen for interruptions while Daisy is speaking"""
        if not self.microphone or not self.is_speaking:
            return None
        
        try:
            # Quick listen for interrupt commands while speaking
            with self.microphone as source:
                try:
                    # Short timeout, just checking for "stop"
                    audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=2)
                    
                    # Try to recognize quickly
                    try:
                        text = self.recognizer.recognize_google(audio)
                        text_lower = text.lower().strip()
                        
                        # Check for interrupt commands
                        interrupt_commands = ["stop", "stop speaking", "stop talking", "quiet", "shush", "enough"]
                        if any(cmd in text_lower for cmd in interrupt_commands):
                            self.stop_speaking()
                            print("\n🔇 [Interrupted by voice command]")
                            return None
                    except:
                        # Didn't understand, that's ok
                        pass
                except sr.WaitTimeoutError:
                    # No voice detected, that's ok
                    pass
        except:
            # Error listening, that's ok - Daisy keeps speaking
            pass
        
        return None
    
    def detect_language(self, text: str) -> str:
        """Detect language from text - returns 'el' for Greek, 'en' for English, etc."""
        if not text:
            return "en"
        
        # Check for Greek characters (Greek Unicode ranges)
        greek_pattern = re.compile(r'[\u0370-\u03FF\u1F00-\u1FFF]')
        greek_char_count = len(greek_pattern.findall(text))
        total_chars = len(re.findall(r'[a-zA-Z\u0370-\u03FF\u1F00-\u1FFF]', text))
        
        # If significant Greek characters, it's Greek
        if total_chars > 0 and (greek_char_count / total_chars) > 0.3:
            return "el"  # Greek
        
        return "en"  # Default to English
    
    def update_system_prompt_for_language(self, language: str):
        """Update system prompt to match user's language"""
        if language == "el":
            # Greek system prompt
            self.system_prompt = """Είσαι η Daisy, μια φιλική και εξυπηρετική προσωπική βοηθός AI.
Έχεις μια ζεστή, επαγγελματική και ελαφρώς συνομιλητική προσωπικότητα.
Βοηθάς με εργασίες, απαντάς σε ερωτήσεις και συμμετέχεις σε φυσικές συνομιλίες.
Κρατά τις απαντήσεις σου συνοπτικές αλλά φιλικές. Χρησιμοποίησε φυσικά πρότυπα ομιλίας.

🚨 ΚΡΙΣΙΜΕΣ ΟΔΗΓΙΕΣ ΓΛΩΣΣΑΣ:
- ΠΡΕΠΕΙ να απαντάς ΟΛΟΚΛΗΡΩΤΙΚΑ στα ΕΛΛΗΝΙΚΑ - ΚΑΘΕ ΛΕΞΗ
- Χρησιμοποίησε ΣΩΣΤΗ ΕΛΛΗΝΙΚΗ ΓΡΑΜΜΑΤΙΚΗ - σωστές κλίσεις, άρθρα, προτάσεις
- Μίλα σαν ΕΛΛΗΝΑΣ - όχι μετάφραση, φυσική ελληνική ομιλία
- ΜΗΝ χρησιμοποιείς Αγγλικά - ΜΟΝΟ Ελληνικά"""
        else:
            # English system prompt
            self.system_prompt = self.base_system_prompt
        
        # Update system message in conversation
        if self.conversation_history and self.conversation_history[0].role == 'system':
            self.conversation_history[0].content = self.system_prompt
        else:
            # Remove old system message and add new one
            self.conversation_history = [msg for msg in self.conversation_history if msg.role != 'system']
            self.add_system_message(self.system_prompt)
    
    def stream_llm_response(self, user_input: str):
        """Stream LLM response chunk by chunk (for real-time TTS like ChatGPT Voice)"""
        # Detect language from user input
        detected_lang = self.detect_language(user_input)
        if detected_lang != self.current_language:
            self.current_language = detected_lang
            self.update_system_prompt_for_language(detected_lang)
            lang_name = "Greek" if detected_lang == "el" else "English"
            print(f"🌍 Language detected: {detected_lang.upper()} ({lang_name})")
        
        # Add user message
        self.add_message('user', user_input)
        messages = self.get_conversation_context()
        
        # Check if we've cached a quota exceeded status
        now = time.time()
        if self.openai_quota_exceeded:
            if now - self.quota_check_time < self.QUOTA_CHECK_INTERVAL:
                # Use cached status - skip OpenAI, go straight to Groq
                if self.groq_client:
                    print("💡 Using Groq (OpenAI quota exceeded - cached)")
                    yield from self.stream_groq_response(messages)
                    return
                else:
                    error_msg = "I'm sorry, I've exceeded my API quota. Please check your OpenAI account billing and usage limits."
                    self.add_message('assistant', error_msg)
                    yield error_msg
                    return
            else:
                # Cache expired - reset and try OpenAI again
                self.openai_quota_exceeded = False
                print("🔄 Cache expired - checking OpenAI quota again...")
        
        # Try OpenAI streaming first
        if self.client:
            try:
                model = self.config.get("llm_model", "gpt-3.5-turbo")
                stream = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=500,
                    stream=True  # Enable streaming
                )
                
                full_response = ""
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        full_response += content
                        yield content
                
                # Handle None or empty response
                if not full_response or full_response.strip() == "":
                    full_response = "I'm sorry, I couldn't generate a response. Please try again."
                    yield full_response
                elif not isinstance(full_response, str):
                    full_response = str(full_response)
                    yield full_response
                
                self.add_message('assistant', full_response)
                print(f"✅ Response from OpenAI ({model})")
                return
                
            except Exception as e:
                error_str = str(e)
                print(f"⚠️  OpenAI error: {error_str[:100]}")
                
                # Handle specific error cases
                if "404" in error_str or "model_not_found" in error_str:
                    print(f"❌ Model not found: {model}")
                    print(f"💡 Trying fallback model: gpt-3.5-turbo")
                    try:
                        stream = self.client.chat.completions.create(
                            model="gpt-3.5-turbo",
                            messages=messages,
                            temperature=0.7,
                            max_tokens=500,
                            stream=True
                        )
                        
                        full_response = ""
                        for chunk in stream:
                            if chunk.choices[0].delta.content:
                                content = chunk.choices[0].delta.content
                                full_response += content
                                yield content
                        
                        if not full_response or full_response.strip() == "":
                            full_response = "I'm sorry, I couldn't generate a response. Please try again."
                            yield full_response
                        elif not isinstance(full_response, str):
                            full_response = str(full_response)
                            yield full_response
                        
                        self.add_message('assistant', full_response)
                        self.config['llm_model'] = 'gpt-3.5-turbo'
                        self.save_config()
                        print(f"✅ Response from OpenAI (gpt-3.5-turbo fallback)")
                        return
                    except Exception as e2:
                        # Still failed, try Groq if available
                        if self.groq_client:
                            print("🔄 Falling back to Groq...")
                            yield from self.stream_groq_response(messages)
                            return
                        error_msg = "I'm sorry, I'm having trouble connecting to the AI service. Please check your API key and account status."
                        yield error_msg
                        self.add_message('assistant', error_msg)
                        return
                
                # Fallback to Groq on quota/401 errors
                elif any(x in error_str for x in ["429", "401", "quota", "insufficient_quota"]):
                    self.openai_quota_exceeded = True
                    self.quota_check_time = time.time()
                    
                    if self.groq_client:
                        print("🔄 Falling back to Groq (quota/API key error - cached for 1 hour)")
                        yield from self.stream_groq_response(messages)
                        return
                    error_msg = "I'm sorry, I've exceeded my API quota. Please check your OpenAI account billing and usage limits."
                    yield error_msg
                    self.add_message('assistant', error_msg)
                    return
                else:
                    # Other errors - try Groq if available
                    if self.groq_client:
                        print("🔄 Falling back to Groq...")
                        yield from self.stream_groq_response(messages)
                        return
                    error_msg = f"I'm sorry, I encountered an error: {str(e)}"
                    yield error_msg
                    self.add_message('assistant', error_msg)
                    return
        
        # Use Groq if OpenAI not available
        if self.groq_client:
            print("🔄 Using Groq (OpenAI not available)...")
            yield from self.stream_groq_response(messages)
            return
        
        error_msg = "I'm sorry, no AI service is available. Please check your API keys."
        yield error_msg
        self.add_message('assistant', error_msg)
    
    def stream_groq_response(self, messages: List[Dict]):
        """Stream Groq response chunk by chunk"""
        if not self.groq_client:
            error_msg = "I'm sorry, Groq is not available."
            yield error_msg
            self.add_message('assistant', error_msg)
            return
        
        # Check if we have a cached working model
        now = time.time()
        use_cached_model = False
        
        if self.groq_working_model:
            check_time = self.groq_model_check_time or 0
            if check_time > 0 and (now - check_time < self.GROQ_MODEL_CHECK_INTERVAL):
                use_cached_model = True
                print(f"💡 Using cached Groq model: {self.groq_working_model}")
                
                try:
                    stream = self.groq_client.chat.completions.create(
                        model=self.groq_working_model,
                        messages=messages,
                        temperature=0.7,
                        max_tokens=500,
                        stream=True  # Enable streaming
                    )
                    
                    full_response = ""
                    for chunk in stream:
                        if chunk.choices[0].delta.content:
                            content = chunk.choices[0].delta.content
                            full_response += content
                            yield content
                    
                    if not full_response or full_response.strip() == "":
                        full_response = "I'm sorry, I couldn't generate a response. Please try again."
                        yield full_response
                    elif not isinstance(full_response, str):
                        full_response = str(full_response)
                        yield full_response
                    
                    self.groq_model_check_time = time.time()
                    self.config["groq_model_check_time"] = self.groq_model_check_time
                    self.save_config()
                    
                    self.add_message('assistant', full_response)
                    print(f"✅ Response from Groq ({self.groq_working_model})")
                    return
                except Exception as e:
                    error_str = str(e)
                    if any(x in error_str.lower() for x in ["404", "model_not_found", "decommissioned"]):
                        print(f"⚠️  Cached model {self.groq_working_model} no longer available - searching for new one...")
                    else:
                        print(f"⚠️  Cached model {self.groq_working_model} failed - searching for new one...")
                    self.groq_working_model = None
                    use_cached_model = False
        
        # No cached model or cache expired - fetch and try models
        if not use_cached_model:
            models = self.fetch_groq_models()
            if not models:
                error_msg = "I'm sorry, no Groq models are available."
                yield error_msg
                self.add_message('assistant', error_msg)
                return
            
            last_error = None
            
            # Try each model until one works
            for model in models:
                try:
                    print(f"🔄 Trying Groq model: {model}")
                    
                    stream = self.groq_client.chat.completions.create(
                        model=model,
                        messages=messages,
                        temperature=0.7,
                        max_tokens=500,
                        stream=True  # Enable streaming
                    )
                    
                    full_response = ""
                    for chunk in stream:
                        if chunk.choices[0].delta.content:
                            content = chunk.choices[0].delta.content
                            full_response += content
                            yield content
                    
                    if not full_response or full_response.strip() == "":
                        full_response = "I'm sorry, I couldn't generate a response. Please try again."
                        yield full_response
                    elif not isinstance(full_response, str):
                        full_response = str(full_response)
                        yield full_response
                    
                    # Cache this working model for 1 hour
                    self.groq_working_model = model
                    self.groq_model_check_time = time.time()
                    self.config["groq_working_model"] = model
                    self.config["groq_model_check_time"] = self.groq_model_check_time
                    self.save_config()
                    
                    self.add_message('assistant', full_response)
                    print(f"✅ Response from Groq ({model}) - cached for 1 hour")
                    return
                        
                except Exception as e:
                    last_error = e
                    error_str = str(e)
                    
                    if any(x in error_str.lower() for x in ["404", "model_not_found", "decommissioned"]):
                        print(f"⚠️  Model {model} not available, trying next...")
                        continue
                    else:
                        # Other error - try next model
                        print(f"⚠️  Model {model} error: {error_str[:100]}, trying next...")
                        continue
            
            # All models failed
            if last_error:
                error_msg = f"I'm sorry, all Groq models failed. Last error: {str(last_error)}"
            else:
                error_msg = "I'm sorry, no Groq models are available."
            yield error_msg
            self.add_message('assistant', error_msg)
    
    def get_llm_response(self, user_input: str) -> str:
        """Get response from LLM - try OpenAI first, then Groq fallback"""
        # Detect language from user input
        detected_lang = self.detect_language(user_input)
        if detected_lang != self.current_language:
            self.current_language = detected_lang
            self.update_system_prompt_for_language(detected_lang)
            lang_name = "Greek" if detected_lang == "el" else "English"
            print(f"🌍 Language detected: {detected_lang.upper()} ({lang_name})")
        
        # Add user message
        self.add_message('user', user_input)
        messages = self.get_conversation_context()
        
        # Check if we've cached a quota exceeded status
        now = time.time()
        if self.openai_quota_exceeded:
            # If we cached quota exceeded, check if enough time has passed
            if now - self.quota_check_time < self.QUOTA_CHECK_INTERVAL:
                # Use cached status - skip OpenAI, go straight to Groq
                if self.groq_client:
                    print("💡 Using Groq (OpenAI quota exceeded - cached)")
                    return self.get_groq_response(messages)
                else:
                    error_msg = "I'm sorry, I've exceeded my API quota. Please check your OpenAI account billing and usage limits."
                    self.add_message('assistant', error_msg)
                    return error_msg
            else:
                # Cache expired - reset and try OpenAI again
                self.openai_quota_exceeded = False
                print("🔄 Cache expired - checking OpenAI quota again...")
        
        # Try OpenAI first
        if self.client:
            try:
                model = self.config.get("llm_model", "gpt-3.5-turbo")
                response = self.client.chat.completions.create(
                    model=model, messages=messages, temperature=0.7, max_tokens=500
                )
                assistant_message = response.choices[0].message.content
                
                # Handle None or empty response
                if not assistant_message or assistant_message.strip() == "":
                    assistant_message = "I'm sorry, I couldn't generate a response. Please try again."
                elif not isinstance(assistant_message, str):
                    assistant_message = str(assistant_message)
                
                self.add_message('assistant', assistant_message)
                print(f"✅ Response from OpenAI ({model})")
                return assistant_message
                
            except Exception as e:
                error_str = str(e)
                print(f"⚠️  OpenAI error: {error_str[:100]}")
                
                # Handle specific error cases
                if "404" in error_str or "model_not_found" in error_str:
                    print(f"❌ Model not found: {model}")
                    print(f"💡 Trying fallback model: gpt-3.5-turbo")
                    # Try with gpt-3.5-turbo as fallback
                    try:
                        response = self.client.chat.completions.create(
                            model="gpt-3.5-turbo",
                            messages=messages,
                            temperature=0.7,
                            max_tokens=500
                        )
                        assistant_message = response.choices[0].message.content
                        # Handle None or empty response
                        if not assistant_message or assistant_message.strip() == "":
                            assistant_message = "I'm sorry, I couldn't generate a response. Please try again."
                        elif not isinstance(assistant_message, str):
                            assistant_message = str(assistant_message)
                        
                        self.add_message('assistant', assistant_message)
                        self.config['llm_model'] = 'gpt-3.5-turbo'
                        self.save_config()
                        print(f"✅ Response from OpenAI (gpt-3.5-turbo fallback)")
                        return assistant_message
                    except Exception as e2:
                        # Still failed, try Groq if available
                        if self.groq_client:
                            print("🔄 Falling back to Groq...")
                            return self.get_groq_response(messages)
                        error_msg = "I'm sorry, I'm having trouble connecting to the AI service. Please check your API key and account status."
                # Fallback to Groq on quota/401 errors
                elif any(x in error_str for x in ["429", "401", "quota", "insufficient_quota"]):
                    # Cache the quota exceeded status (don't check again for 1 hour)
                    self.openai_quota_exceeded = True
                    self.quota_check_time = time.time()
                    
                    if self.groq_client:
                        print("🔄 Falling back to Groq (quota/API key error - cached for 1 hour)")
                        return self.get_groq_response(messages)
                    error_msg = "I'm sorry, I've exceeded my API quota. Please check your OpenAI account billing and usage limits."
                    print(f"❌ Quota exceeded - check your OpenAI account (cached for 1 hour)")
                else:
                    # Other errors - try Groq if available
                    if self.groq_client:
                        print("🔄 Falling back to Groq...")
                        return self.get_groq_response(messages)
                    error_msg = f"I'm sorry, I encountered an error: {str(e)}"
                
                print(f"❌ LLM Error: {e}")
                self.add_message('assistant', error_msg)
                return error_msg
        
        # Use Groq if OpenAI not available
        if self.groq_client:
            print("🔄 Using Groq (OpenAI not available)...")
            return self.get_groq_response(messages)
        
        error_msg = "I'm sorry, no AI service is available. Please check your API keys."
        self.add_message('assistant', error_msg)
        return error_msg
    
    def show_notification(self, title: str, message: str):
        """Show macOS notification"""
        script = f'''
        display notification "{message}" with title "{title}"
        '''
        subprocess.run(["osascript", "-e", script], check=False)
    
    def save_conversation(self):
        """Save conversation to file"""
        if not self.config.get("save_conversations", True):
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        conv_file = Path.home() / ".daisy" / "conversations" / f"conversation_{timestamp}.json"
        
        conversation_data = {
            "timestamp": timestamp,
            "messages": [asdict(msg) for msg in self.conversation_history]
        }
        
        with open(conv_file, 'w') as f:
            json.dump(conversation_data, f, indent=2)
    
    def speak_and_listen_loop(self):
        """Main conversation loop: speak, listen, respond"""
        print("\n" + "="*60)
        print("💬 Daisy is ready to chat!")
        print("Speak naturally, or type 'quit' to exit")
        print("="*60 + "\n")
        
        # Initial greeting
        greeting = "Hi! I'm Daisy, your personal assistant. How can I help you today?"
        print(f"🤖 Daisy: {greeting}")
        self.text_to_speech(greeting)
        self.add_message('assistant', greeting)
        
        auto_listen = self.config.get("auto_listen", True)
        
        while True:
            try:
                # Listen for input (check for interrupt commands)
                if auto_listen and self.microphone:
                    user_input = self.listen_for_voice(timeout=10, interruptible=True)
                    if not user_input:
                        continue
                else:
                    # Fallback to text input
                    user_input = input("\n👤 You (or 'quit'): ").strip()
                
                if not user_input:
                    continue
                
                # Ignore very short inputs (likely keyboard noise or accidental triggers)
                if len(user_input.strip()) < 3:
                    print(f"⏭️  [Ignoring very short input: '{user_input}']")
                    continue
                
                # Ignore inputs that look like keyboard escape sequences or control characters
                if re.search(r'[\x00-\x1f\x7f-\x9f]', user_input) or user_input.startswith('^'):
                    print(f"⏭️  [Ignoring keyboard control sequence: '{user_input[:20]}']")
                    continue
                
                # Filter out repetitive "thank you" responses right after interrupt or response
                now = time.time()
                time_since_interrupt = now - self.interrupt_time if self.interrupt_time > 0 else 999
                time_since_response = now - self.last_response_time if self.last_response_time > 0 else 999
                
                # Check if this is a "thank you" variant
                thank_you_variants = [
                    'thank you', 'thanks', 'thank you.', 'thanks.', 'thank you!', 'thanks!',
                    'thank you very much', 'thanks a lot', 'thank you so much', 'thanks so much',
                    'ty', 'thx', 'thank u', 'thnx'
                ]
                
                user_input_lower = user_input.lower().strip()
                is_thank_you = any(variant in user_input_lower for variant in thank_you_variants)
                
                # Filter "thank you" only if we JUST responded (to prevent immediate loops)
                # But be less aggressive - only skip if it's within 5 seconds AND we already responded to thank you
                if is_thank_you:
                    # Only skip if we responded very recently (5 seconds) AND already responded to thank you
                    if time_since_response < 5.0:
                        # Check if we already responded to "thank you" in the last response
                        if len(self.conversation_history) > 1:
                            last_assistant_msg = self.conversation_history[-1]
                            if last_assistant_msg.role == 'assistant':
                                last_content = last_assistant_msg.content.lower()
                                # Only skip if the last response was clearly a "you're welcome" type response
                                welcome_phrases = ['welcome', 'pleasure', 'glad to help', 'happy to help', 'anytime']
                                if any(phrase in last_content for phrase in welcome_phrases):
                                    print(f"⏭️  [Skipping 'thank you' - just said welcome {time_since_response:.1f}s ago]")
                                    continue
                    # Skip if we interrupted very recently (3 seconds)
                    if time_since_interrupt < 3.0:
                        print(f"⏭️  [Skipping 'thank you' - just interrupted {time_since_interrupt:.1f}s ago]")
                        continue
                    
                    # Also skip if we just responded recently (within 10 seconds) - likely noise/keyboard
                    if time_since_response < 10.0:
                        print(f"⏭️  [Skipping 'thank you' - responded {time_since_response:.1f}s ago (likely noise)]")
                        continue
                
                # Check for exit commands
                if user_input.lower() in ['quit', 'exit', 'goodbye', 'bye']:
                    farewell = "Goodbye! It was nice talking with you."
                    print(f"🤖 Daisy: {farewell}")
                    self.text_to_speech(farewell)
                    self.save_conversation()
                    break
                
                
                # Get LLM response with streaming (like ChatGPT Voice)
                print("\n🔄 Thinking...")
                print("💡 (Say 'STOP' loudly OR press ANY KEY to interrupt)")
                
                # Reset interrupt flags BEFORE starting
                self.interrupt_event.clear()
                self.interrupt_detected = False
                self.is_speaking = False
                
                # Start listening for voice interrupt BEFORE starting to speak
                interrupt_voice = threading.Thread(
                    target=self._listen_for_interrupt,
                    daemon=True,
                    name="VoiceInterruptListener"
                )
                interrupt_voice.start()
                
                # Start keyboard interrupt listener (non-blocking backup)
                keyboard_interrupt = threading.Thread(
                    target=self._keyboard_interrupt_listener,
                    daemon=True,
                    name="KeyboardInterruptListener"
                )
                keyboard_interrupt.start()
                
                # Small delay to let interrupt listeners start properly
                time.sleep(0.3)
                
                # Stream LLM response for display, then speak the ENTIRE response as ONE unit
                buffer = ""
                full_response = ""
                
                print("🤖 Daisy: ", end="", flush=True)
                
                try:
                    # Collect the full response (streaming for display only)
                    for chunk in self.stream_llm_response(user_input):
                        if self.interrupt_event.is_set() or self.interrupt_detected:
                            print("\n🔇 [Interrupted]")
                            break
                        
                        # Add chunk to buffer
                        buffer += chunk
                        full_response += chunk
                        print(chunk, end="", flush=True)
                    
                    print()  # New line after streaming
                    
                    # Speak the ENTIRE response as ONE unit (not sentence-by-sentence)
                    if not (self.interrupt_event.is_set() or self.interrupt_detected) and full_response.strip():
                        # Speak the complete response as one unit
                        self.text_to_speech(full_response)
                    
                except Exception as e:
                    print(f"\n❌ Streaming error: {e}")
                    # Fallback to non-streaming
                    full_response = self.get_llm_response(user_input)
                    print(f"🤖 Daisy: {full_response}")
                    self.text_to_speech(full_response)
                
                # Record response time to prevent immediate loops
                self.last_response_time = time.time()
                
                # Note: Since we're speaking sequentially, text_to_speech() is blocking
                # and will wait for each sentence to finish. The interrupt listeners
                # are already running and will stop speech if needed.
                
                # Wait for interrupt listeners to finish
                if interrupt_voice.is_alive():
                    interrupt_voice.join(timeout=0.5)
                if keyboard_interrupt.is_alive():
                    keyboard_interrupt.join(timeout=0.5)
                
                # Use full_response if we have it, otherwise use the last message
                display_response = full_response if full_response else (self.conversation_history[-1].content if self.conversation_history else "")
                self.show_notification("Daisy", display_response[:100])
                
                # Save conversation periodically
                if len(self.conversation_history) % 10 == 0:
                    self.save_conversation()
                
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                self.save_conversation()
                break
            except Exception as e:
                print(f"❌ Error in conversation loop: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(1)
    
    def _keyboard_interrupt_listener(self):
        """Background thread that listens for keyboard input to interrupt (Spacebar/Enter)"""
        import sys
        import select
        import tty
        import termios
        
        if not sys.stdin.isatty():
            # Not a terminal - can't listen for keyboard
            return
        
        # Try to monitor stdin for spacebar or Enter key presses
        old_settings = None
        try:
            old_settings = termios.tcgetattr(sys.stdin)
            tty.setcbreak(sys.stdin.fileno())
            
            print("⌨️  [Keyboard listener active - press Spacebar or Enter to interrupt]")
            
            while self.is_speaking and not self.interrupt_event.is_set():
                try:
                    # Check if there's input waiting (non-blocking with short timeout)
                    ready, _, _ = select.select([sys.stdin], [], [], 0.1)
                    if ready:
                        char = sys.stdin.read(1)
                        # Spacebar (32) or Enter (10/13) triggers interrupt
                        if char in [' ', '\n', '\r', '\x03']:  # Space, Enter, or Ctrl+C
                            print(f"\n⌨️  [Keyboard interrupt detected! Stopping...]")
                            self.stop_speaking()
                            break
                except (OSError, ValueError, KeyboardInterrupt) as e:
                    # Handle terminal errors gracefully
                    break
                except Exception as e:
                    # Other errors - continue trying
                    pass
        except Exception as e:
            # Can't set terminal mode - keyboard interrupt won't work
            print(f"⚠️  [Keyboard interrupt unavailable: {str(e)[:50]}]")
            pass
        finally:
            if old_settings:
                try:
                    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
                except:
                    pass
    
    def _listen_for_interrupt(self):
        """Background thread that uses direct pyaudio VAD to detect ANY user speech while Daisy is speaking"""
        # Use pyaudio directly for VAD - more reliable than speech_recognition during audio playback
        if not PYAUDIO_AVAILABLE:
            print("⚠️  [VAD: pyaudio not available - use keyboard to interrupt]")
            return
        
        print("🎤 [VAD active - start speaking anytime to interrupt]")
        
        import pyaudio
        
        # Try to import audioop (deprecated in Python 3.13+, but still works)
        try:
            import audioop
            USE_AUDIOOP = True
        except ImportError:
            # Fallback to manual RMS calculation if audioop not available
            USE_AUDIOOP = False
            import struct
        
        # Audio settings
        CHUNK = 512  # Small chunks for fast response
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 16000
        
        audio = None
        stream = None
        
        try:
            # Open audio stream ONCE at the start
            audio = pyaudio.PyAudio()
            
            # Find available input device (might help with conflicts)
            try:
                default_input = audio.get_default_input_device_info()
                device_index = default_input['index']
            except:
                device_index = None
            
            stream = audio.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=CHUNK
            )
            
            # Skip initial frames to avoid startup noise
            for _ in range(5):
                try:
                    stream.read(CHUNK, exception_on_overflow=False)
                except:
                    pass
            
            print("🎤 [VAD listener ready - monitoring for voice...]")
            
            # VAD state
            frame_count = 0
            energy_threshold = 6000  # Start higher to avoid false positives from Daisy's audio
            consecutive_voice = 0
            frames_needed = 3  # Need 3 consecutive frames (~96ms) to confirm voice
            
            # Main VAD loop - keep reading while Daisy is speaking
            # Wait a moment for is_speaking to be set
            wait_count = 0
            while wait_count < 10 and not self.is_speaking:
                time.sleep(0.05)
                wait_count += 1
            
            while self.is_speaking and not self.interrupt_event.is_set():
                try:
                    frame_count += 1
                    
                    # Check if audio process finished (only if it exists)
                    if self.current_audio_process is None:
                        # No audio process yet - wait a bit
                        time.sleep(0.05)
                        continue
                    elif self.current_audio_process.poll() is not None:
                        # Audio finished - exit
                        break
                    
                    # Check if interrupt already detected
                    if self.interrupt_detected:
                        break
                    
                    # Read audio chunk (non-blocking)
                    try:
                        audio_data = stream.read(CHUNK, exception_on_overflow=False)
                    except Exception as e:
                        # Stream error - retry with small delay
                        time.sleep(0.05)
                        continue
                    
                    # Calculate RMS energy for voice activity detection
                    if USE_AUDIOOP:
                        rms = audioop.rms(audio_data, 2)  # 2 = 16-bit samples
                    else:
                        # Manual RMS calculation if audioop not available
                        samples = struct.unpack('<' + ('h' * (len(audio_data) // 2)), audio_data)
                        rms = int((sum(x*x for x in samples) / len(samples)) ** 0.5)
                    
                    # Adaptive threshold: lower over time to detect user voice even with echo
                    if frame_count > 30:  # After ~960ms, lower threshold
                        energy_threshold = max(6000 * 0.5, 3500)
                    elif frame_count > 10:  # After ~320ms, start lowering
                        energy_threshold = max(6000 * 0.7, 4500)
                    
                    # Check for voice activity
                    if rms > energy_threshold:
                        consecutive_voice += 1
                        # Debug: show when voice detected
                        if consecutive_voice == 1:
                            print(f"🎤 [Voice activity detected (RMS: {rms}, threshold: {int(energy_threshold)})]")
                        
                        # If multiple consecutive frames with voice, interrupt immediately
                        if consecutive_voice >= frames_needed:
                            print(f"🔇 [User speaking detected! (RMS: {rms}) - Stopping immediately...]")
                            self.stop_speaking()
                            break
                    else:
                        # Reset counter if no voice detected
                        if consecutive_voice > 0:
                            consecutive_voice = 0
                    
                    # Small delay to avoid CPU spinning (VAD is fast enough)
                    time.sleep(0.01)  # 10ms = ~100 checks per second
                    
                except Exception as e:
                    # Error in VAD loop - log and continue
                    if frame_count < 5:  # Only log first few errors
                        print(f"⚠️  [VAD error: {str(e)[:50]}]")
                    time.sleep(0.05)
                    continue
                    
        except Exception as e:
            print(f"⚠️  [VAD setup error: {str(e)[:100]}]")
        finally:
            # Clean up audio stream
            if stream:
                try:
                    stream.stop_stream()
                    stream.close()
                except:
                    pass
            if audio:
                try:
                    audio.terminate()
                except:
                    pass
        
        print("🎤 [VAD listener stopped]")
    
    def respond_to_text(self, text: str) -> str:
        """Respond to text input (for integration with other systems)"""
        response = self.get_llm_response(text)
        self.text_to_speech(response)
        return response


def main():
    """Main entry point"""
    import sys
    
    try:
        assistant = DaisyAssistant()
        
        # Check for command line arguments
        if len(sys.argv) > 1:
            if sys.argv[1] == "--text":
                # Text mode
                print("\n" + "="*60)
                print("💬 Daisy - Text Mode")
                print("Type 'quit' to exit")
                print("="*60 + "\n")
                
                greeting = "Hi! I'm Daisy. How can I help you?"
                print(f"🤖 Daisy: {greeting}")
                assistant.text_to_speech(greeting)
                
                while True:
                    user_input = input("\n👤 You: ").strip()
                    if user_input.lower() in ['quit', 'exit']:
                        farewell = "Goodbye!"
                        print(f"🤖 Daisy: {farewell}")
                        assistant.text_to_speech(farewell)
                        break
                    response = assistant.respond_to_text(user_input)
                    print(f"🤖 Daisy: {response}")
            else:
                print("Usage: daisy-assistant.py [--text]")
                sys.exit(1)
        else:
            # Voice conversation mode
            assistant.speak_and_listen_loop()
            
    except ValueError as e:
        print(f"❌ Configuration Error: {e}")
        print("\nPlease set your OpenAI API key:")
        print("  export OPENAI_API_KEY='your-api-key-here'")
        print("\nOr add it to ~/.daisy/config.json:")
        print('  {"openai_api_key": "your-api-key-here"}')
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

