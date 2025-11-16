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
        
        # Initialize system prompt
        self.system_prompt = self.config.get(
            "system_prompt",
            """You are Daisy, a friendly and helpful personal AI assistant. 
You have a warm, professional, and slightly conversational personality.
You help with tasks, answer questions, and engage in natural conversations.
Keep responses concise but friendly. Use natural speech patterns."""
        )
        
        # Initialize conversation
        self.add_system_message(self.system_prompt)
        
        print("🌟 Daisy is ready!")
        voice = self.config.get('voice', 'shimmer')
        print(f"🎤 Voice: {voice} (human-like)")
        print(f"🧠 Model: {self.config.get('llm_model', 'gpt-3.5-turbo')}")
        tts_model = self.config.get('tts_model', 'tts-1-hd')
        print(f"🔊 TTS: {tts_model} (high quality)")
        print(f"💬 Fallback: macOS Samantha (natural female voice)")
        if self.groq_client:
            print(f"🔄 Groq fallback: Available")
            if self.groq_working_model:
                print(f"   Working model: {self.groq_working_model} (cached)")
    
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
            "groq_api_key": "",  # Optional Groq API key for fallback
            "llm_model": "gpt-3.5-turbo",  # Default to gpt-3.5-turbo (more accessible than gpt-4)
            "voice": "shimmer",  # shimmer is more expressive and human-like (nova is also good)
            "voice_speed": 0.95,  # Slightly slower for more natural speech (0.9-1.0 range)
            "tts_model": "tts-1-hd",  # Higher quality for more human-like voice
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
    
    def _process_text_for_natural_speech(self, text: str) -> str:
        """Process text to sound more human with natural pauses and emphasis"""
        # Handle None or non-string input
        if text is None:
            return "I'm sorry, I couldn't generate a response."
        if not isinstance(text, str):
            text = str(text)
        if not text.strip():
            return "I'm sorry, I couldn't understand that."
        
        # Add natural pauses after commas, periods, questions
        text = re.sub(r'([,.!?;:])', r'\1 ', text)  # Space after punctuation
        text = re.sub(r'\s+', ' ', text)  # Clean up multiple spaces
        
        # Add slight pauses for natural flow (use SSML-like pauses with commas)
        # Break up long sentences with natural pauses
        sentences = re.split(r'([.!?])', text)
        processed = []
        for i, part in enumerate(sentences):
            if part.strip():
                processed.append(part.strip())
                # Add pause after sentence endings
                if i < len(sentences) - 1 and sentences[i+1] in ['.', '!', '?']:
                    pass  # Natural pause will come from punctuation
        text = ' '.join(processed)
        
        # Make questions sound more natural
        text = re.sub(r'\?+', '?', text)  # Multiple ? to single
        
        return text.strip()
    
    def text_to_speech(self, text: str) -> Optional[bytes]:
        """Convert text to speech using OpenAI TTS with human-like female voice (interruptible)"""
        # Stop any currently playing audio
        self.stop_speaking()
        
        try:
            # Use shimmer voice for more natural, expressive sound (more human-like)
            voice = self.config.get("voice", "shimmer")  # shimmer is more expressive/natural
            # Slightly slower speed for more natural speech (0.95-1.0)
            speed = self.config.get("voice_speed", 0.95)
            # Use HD model for more human-like quality
            tts_model = self.config.get("tts_model", "tts-1-hd")
            
            # Process text for more natural speech patterns
            processed_text = self._process_text_for_natural_speech(text)
            
            # Check if we've cached quota exceeded for TTS
            now = time.time()
            if self.openai_quota_exceeded and (now - self.quota_check_time < self.QUOTA_CHECK_INTERVAL):
                # Skip OpenAI TTS, use macOS fallback directly
                # Set is_speaking flag BEFORE raising exception (so fallback can use it)
                self.is_speaking = True
                self.interrupt_event.clear()
                self.interrupt_detected = False
                raise Exception("Quota exceeded (cached)")
            
            # Use tts-1-hd for higher quality, more human-like voice
            response = self.client.audio.speech.create(
                model=tts_model,  # Higher quality for more natural, human-like voice
                voice=voice,
                input=processed_text,
                speed=speed
            )
            
            # Save audio file
            audio_dir = Path.home() / ".daisy" / "audio"
            audio_file = audio_dir / f"daisy_{int(time.time())}.mp3"
            
            # Write audio to file
            audio_data = b""
            for chunk in response.iter_bytes():
                audio_data += chunk
            
            with open(audio_file, 'wb') as f:
                f.write(audio_data)
            
            # Play audio using macOS afplay (interruptible)
            self.is_speaking = True
            # Reset interrupt flags before starting
            self.interrupt_event.clear()
            self.interrupt_detected = False
            self.current_audio_process = subprocess.Popen(
                ["afplay", str(audio_file)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE
            )
            
            # Poll while playing (so we can interrupt)
            while self.current_audio_process.poll() is None:
                if not self.is_speaking:
                    # Was interrupted - already stopped
                    break
                time.sleep(0.1)  # Check every 100ms
            
            self.is_speaking = False
            if self.current_audio_process:
                self.current_audio_process = None
            
            # Clean up after a delay (optional)
            threading.Timer(10.0, lambda: audio_file.unlink() if audio_file.exists() else None).start()
            
            return audio_data
            
        except Exception as e:
            error_str = str(e)
            # Check for quota errors
            if "429" in error_str or "quota" in error_str.lower() or "insufficient_quota" in error_str:
                self.openai_quota_exceeded = True
                self.quota_check_time = time.time()
                print("⚠️  OpenAI TTS quota exceeded - using macOS voice fallback")
            else:
                print(f"⚠️  TTS Error: {e} - using macOS voice fallback")
            
            # Always fallback to macOS say with female voice (interruptible)
            # Set is_speaking flag BEFORE opening audio stream (so VAD thread can detect it)
            self.is_speaking = True
            # Reset interrupt flags
            self.interrupt_event.clear()
            self.interrupt_detected = False
            
            processed_text = self._process_text_for_natural_speech(text)
            
            # Use the most natural female voice on macOS
            # Samantha is the most natural-sounding, Karen is more expressive
            # Try Samantha first (most human-like), fallback to Karen
            fallback_voice = "Samantha"
            
            # Use natural voice with human-like rate and pitch
            # Rate 165: natural conversational speed (not too fast, not too slow)
            # Pitch 52: natural female pitch (slightly higher = more expressive)
            # These settings create a more human-like, conversational tone
            # IMPORTANT: Don't redirect stderr - let errors show, and don't use DEVNULL for say command
            try:
                self.current_audio_process = subprocess.Popen(
                    ["say", "-v", fallback_voice, "-r", "165", processed_text],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE
                )
            except Exception as say_error:
                print(f"⚠️  Error with say command: {say_error}")
                # Try without rate parameter as fallback
                try:
                    self.current_audio_process = subprocess.Popen(
                        ["say", "-v", fallback_voice, processed_text],
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
                while self.current_audio_process.poll() is None:
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
                    
                    # Check for interrupt event or flags
                    if self.interrupt_event.is_set() or not self.is_speaking or self.interrupt_detected:
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
        """Listen for voice input and convert to text (can interrupt while Daisy is speaking)"""
        if not self.microphone:
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
            
            print("🔄 Processing speech...")
            # Check if we've cached quota exceeded for Whisper
            now = time.time()
            if self.openai_quota_exceeded and (now - self.quota_check_time < self.QUOTA_CHECK_INTERVAL):
                # Skip OpenAI Whisper, use Google directly
                print("💡 Using Google Speech (OpenAI quota exceeded - cached)")
                text = self.recognizer.recognize_google(audio)
            else:
                # Try OpenAI Whisper first (more accurate)
                try:
                    audio_data = io.BytesIO(audio.get_wav_data())
                    audio_data.name = "audio.wav"
                    transcript = self.client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_data,
                        language="en"
                    )
                    text = transcript.text
                    # Reset quota status if Whisper works
                    if self.openai_quota_exceeded:
                        self.openai_quota_exceeded = False
                        print("✅ OpenAI quota restored (Whisper working)")
                except Exception as e:
                    error_str = str(e)
                    # Check for quota errors
                    if "429" in error_str or "quota" in error_str.lower() or "insufficient_quota" in error_str:
                        # Cache quota exceeded
                        self.openai_quota_exceeded = True
                        self.quota_check_time = time.time()
                        print(f"⚠️  Whisper quota exceeded (cached for 1 hour), using Google: {error_str[:50]}")
                    else:
                        print(f"⚠️  Whisper failed, trying Google: {e}")
                    # Fallback to Google Speech Recognition
                    text = self.recognizer.recognize_google(audio)
            
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
    
    def get_llm_response(self, user_input: str) -> str:
        """Get response from LLM - try OpenAI first, then Groq fallback"""
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
                
                # Check for exit commands
                if user_input.lower() in ['quit', 'exit', 'goodbye', 'bye']:
                    farewell = "Goodbye! It was nice talking with you."
                    print(f"🤖 Daisy: {farewell}")
                    self.text_to_speech(farewell)
                    self.save_conversation()
                    break
                
                
                # Get LLM response
                print("\n🔄 Thinking...")
                response = self.get_llm_response(user_input)
                
                # Speak response (interruptible - say "stop" to interrupt)
                print(f"🤖 Daisy: {response}")
                print("💡 (Say 'STOP' loudly OR press ANY KEY to interrupt)")
                
                # Reset interrupt flags BEFORE starting audio
                self.interrupt_event.clear()
                self.interrupt_detected = False
                self.is_speaking = False  # Will be set to True in text_to_speech
                
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
                
                # Also set up a simple stdin monitor in main thread as backup
                # This will work even if the thread doesn't
                import sys
                import select
                
                # Small delay to let interrupt listeners start properly
                time.sleep(0.3)
                
                # Start speaking (can be interrupted by voice or keyboard)
                # Start audio in a separate checkable way
                self.text_to_speech(response)
                
                # While speaking, check for keyboard input in main thread (most reliable)
                if self.is_speaking:
                    print("⌨️  [Press ANY KEY to interrupt while speaking...]")
                    start_speak_time = time.time()
                    while self.is_speaking and (time.time() - start_speak_time < 300):  # Max 5 min
                        # Check if stdin has input (non-blocking)
                        if sys.stdin.isatty():
                            if select.select([sys.stdin], [], [], 0.1)[0]:
                                # User pressed a key - interrupt immediately
                                print(f"\n⌨️  [KEY DETECTED - Stopping immediately!]")
                                self.stop_speaking()
                                break
                        
                        # Also check interrupt flags
                        if self.interrupt_event.is_set() or self.interrupt_detected:
                            break
                        
                        # Check if audio process finished
                        if self.current_audio_process and self.current_audio_process.poll() is not None:
                            break
                        
                        time.sleep(0.05)  # Check every 50ms
                
                # Wait for interrupt listeners to finish
                if interrupt_voice.is_alive():
                    interrupt_voice.join(timeout=0.5)
                if keyboard_interrupt.is_alive():
                    keyboard_interrupt.join(timeout=0.5)
                
                self.show_notification("Daisy", response[:100])
                
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

