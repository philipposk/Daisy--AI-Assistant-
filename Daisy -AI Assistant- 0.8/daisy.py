#!/usr/bin/env python3
"""
Daisy Assistant 0.8 - Main CLI entrypoint
Vertical slice: Voice → Brain → Actions
"""
import sys
import argparse
import time
from pathlib import Path
from typing import Optional
import speech_recognition as sr

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config import load_config, get_config
from services import VoiceService, BrainService, ActionService
from actions import ActionDispatcher
from persistence import PersistenceLayer
from schemas import ConversationMessage
from utils import setup_logger, AuditLogger

logger = setup_logger("daisy")


class DaisyPipeline:
    """Main pipeline orchestrating voice → brain → actions"""
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config = load_config(config_path)
        
        # Initialize services
        self.voice_service = VoiceService(self.config)
        self.brain_service = BrainService(self.config)
        self.action_service = ActionService(self.config)
        
        # Initialize audit logger
        audit_log_path = Path(self.config.paths.audit_log).expanduser()
        self.audit_logger = AuditLogger(audit_log_path) if self.config.enable_audit_logging else None
        
        # 0.8: build the confirmation provider (CLI by default; voice if configured).
        from services.confirmation import build_confirmation_provider
        self.confirmation_provider = build_confirmation_provider(self.config, self.voice_service)

        # Initialize dispatcher (with confirmation provider + shared persistence)
        # Persistence is wired below; we pass a closure so dispatcher picks it up.
        self.dispatcher = ActionDispatcher(
            self.config,
            self.audit_logger,
            confirmation_provider=self.confirmation_provider,
        )
        
        # Initialize persistence
        db_path = Path(self.config.paths.database_path).expanduser()
        self.persistence = PersistenceLayer(db_path)
        # Share with dispatcher so ActionService uses the same DB connection layer.
        self.dispatcher._persistence = self.persistence

        # 0.8: reminder scheduler runs in a daemon thread
        self.reminder_scheduler = None
        if self.config.reminder.enabled:
            from services.reminder_scheduler import ReminderScheduler
            self.reminder_scheduler = ReminderScheduler(
                reminders_path=Path(self.config.paths.reminders_file).expanduser(),
                voice_service=self.voice_service,
                poll_seconds=self.config.reminder.poll_seconds,
                notify_via_osascript=self.config.reminder.notify_via_osascript,
                speak_reminders=self.config.reminder.speak_reminders,
            )
            self.reminder_scheduler.start()
        
        # Conversation history
        self.conversation_history: list[ConversationMessage] = []
        self._load_recent_history()

        # Counter for periodic history flush (fix #4: avoid quadratic DB churn)
        self._messages_since_flush = 0
        self._flush_every_n_messages = 50
    
    def _load_recent_history(self):
        """Load recent conversation history from persistence"""
        try:
            self.conversation_history = self.persistence.get_recent_messages(
                limit=self.config.max_conversation_history
            )
        except Exception as e:
            logger.warning(f"Failed to load conversation history: {e}")
    
    def process_text(self, text: str) -> str:
        """
        Process text input through the pipeline
        Returns: Response text for TTS
        """
        # Create transcription result from text (fix #2: removed duplicate import)
        from schemas import TranscriptionResult
        transcript = TranscriptionResult(text=text)
        
        # Log transcription
        if self.audit_logger:
            self.audit_logger.log_transcription(transcript)
        
        # Add to conversation history
        user_msg = ConversationMessage(role="user", content=text)
        self.conversation_history.append(user_msg)
        self.persistence.save_conversation_message(user_msg)
        
        # Brain: Plan actions
        intent = self.brain_service.plan_actions(transcript, self.conversation_history)
        
        # Log intent
        if self.audit_logger:
            self.audit_logger.log_intent(intent)
        
        # Execute actions (skip conversation actions for now)
        action_results = []
        conversation_response = None
        
        for action in intent.actions:
            if action.action_type == "conversation":
                conversation_response = action.conversation
            else:
                # Execute structured actions
                results = self.dispatcher.dispatch_actions([action], auto_approve=not intent.requires_confirmation)
                action_results.extend(results)
        
        # Determine response
        if conversation_response:
            response = conversation_response
        elif action_results:
            # Build response from action results
            success_count = sum(1 for r in action_results if r.success)
            if success_count == len(action_results):
                response = "Done! " + ". ".join([r.output for r in action_results if r.output])
            else:
                response = "Some actions completed. " + ". ".join([
                    r.output if r.success else f"Error: {r.error}" 
                    for r in action_results if r.output or r.error
                ])
        else:
            response = "I understand, but I'm not sure what action to take. Can you clarify?"
        
        # Add assistant response to history
        assistant_msg = ConversationMessage(role="assistant", content=response)
        self.conversation_history.append(assistant_msg)
        self.persistence.save_conversation_message(assistant_msg)
        
        # Trim history if too long (fix #4: periodic flush instead of every-message)
        if len(self.conversation_history) > self.config.max_conversation_history:
            self.conversation_history = self.conversation_history[-self.config.max_conversation_history:]

        self._messages_since_flush += 2  # user + assistant
        if self._messages_since_flush >= self._flush_every_n_messages:
            try:
                self.persistence.clear_old_messages(keep_last_n=self.config.max_conversation_history)
            except Exception as e:
                logger.warning(f"Periodic flush failed: {e}")
            self._messages_since_flush = 0

        return response
    
    def process_audio_file(self, audio_path: Path) -> tuple[str, list]:
        """
        Process audio file through the pipeline
        Returns: (response_text, action_results)
        """
        # Voice: Transcribe
        transcript = self.voice_service.transcribe_audio_file(audio_path)
        
        # Process transcript
        response = self.process_text(transcript.text)
        
        return response, []
    
    def voice_loop(self):
        """Interactive voice conversation loop"""
        print("🎙️ Daisy Voice Assistant")
        print("Say something... (Ctrl+C to exit)\n")
        
        recognizer = sr.Recognizer()
        try:
            microphone = sr.Microphone()
        except Exception as e:
            print(f"❌ Microphone not available: {e}")
            print("   Falling back to text mode. Use: python daisy.py --text")
            return
        
        # Adjust for ambient noise
        with microphone as source:
            recognizer.adjust_for_ambient_noise(source)
        
        greeting = "Hi! I'm Daisy. How can I help you?"
        print(f"🤖 Daisy: {greeting}")
        # Fix #3: actually play the greeting audio (was silent in 0.6)
        try:
            greeting_audio = self.voice_service.text_to_speech(greeting)
            self.voice_service.play_audio(greeting_audio)
            try:
                greeting_audio.unlink()
            except Exception:
                pass
        except Exception as e:
            logger.warning(f"Failed to play greeting: {e}")

        while True:
            try:
                print("\n🎤 Listening...")
                with microphone as source:
                    audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
                
                print("🔄 Processing...")
                
                # Save audio temporarily for transcription
                import tempfile
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                    tmp_path = Path(tmp.name)
                
                try:
                    # Save audio
                    with open(tmp_path, 'wb') as f:
                        f.write(audio.get_wav_data())
                    
                    # Transcribe
                    transcript = self.voice_service.transcribe_audio_file(tmp_path)
                    print(f"👤 You: {transcript.text}")
                    
                    # Process
                    response = self.process_text(transcript.text)
                    
                    # Speak response
                    print(f"🤖 Daisy: {response}")
                    audio_file = self.voice_service.text_to_speech(response)
                    self.voice_service.play_audio(audio_file)
                    
                    # Cleanup
                    audio_file.unlink()
                    
                finally:
                    tmp_path.unlink()
                    
            except sr.WaitTimeoutError:
                continue
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                logger.error(f"Error in voice loop: {e}", exc_info=True)
                print(f"❌ Error: {e}")
    
    def text_loop(self):
        """Interactive text conversation loop"""
        # Check if stdin is available (not a background process)
        if not sys.stdin.isatty():
            print("❌ Error: stdin is not available. Cannot run in interactive text mode.")
            print("   This usually means the process is running in the background.")
            print("   Use --input flag for non-interactive mode, or run in a terminal.")
            return
        
        print("💬 Daisy Text Assistant")
        print("Type your message (Ctrl+C or 'quit' to exit)\n")
        
        greeting = "Hi! I'm Daisy. How can I help you?"
        print(f"🤖 Daisy: {greeting}")
        
        while True:
            try:
                user_input = input("\n👤 You: ").strip()
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("\n👋 Goodbye!")
                    break
                
                if not user_input:
                    continue
                
                response = self.process_text(user_input)
                print(f"🤖 Daisy: {response}")
                
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except EOFError:
                # stdin was closed (e.g., terminal disconnected, background process)
                print("\n\n⚠️  stdin closed. Exiting...")
                break
            except Exception as e:
                logger.error(f"Error in text loop: {e}", exc_info=True)
                print(f"❌ Error: {e}")
                # Add small delay to prevent tight loop on repeated errors
                time.sleep(0.1)


def main():
    """Main CLI entrypoint"""
    parser = argparse.ArgumentParser(description="Daisy AI Assistant")
    parser.add_argument("--text", action="store_true", help="Text mode (no microphone)")
    parser.add_argument("--audio", type=str, help="Process audio file and exit")
    parser.add_argument("--transcribe-only", type=str, help="Transcribe audio file and print only the transcription")
    parser.add_argument("--input", type=str, help="Process text input and exit")
    parser.add_argument("--config", type=str, help="Path to config file")
    
    args = parser.parse_args()
    
    config_path = Path(args.config).expanduser() if args.config else None
    
    try:
        pipeline = DaisyPipeline(config_path)
        
        if args.transcribe_only:
            # Just transcribe and print with timestamps
            audio_path = Path(args.transcribe_only).expanduser()
            if not audio_path.exists():
                print(f"❌ Audio file not found: {audio_path}")
                sys.exit(1)
            
            print(f"🎤 Transcribing: {audio_path.name}")
            transcript = pipeline.voice_service.transcribe_audio_file(audio_path)
            
            # Format with timestamps if available
            if transcript.segments:
                print("\n" + "="*80)
                print("TRANSCRIPTION (with timestamps):")
                print("="*80)
                
                def format_timestamp(seconds: float) -> str:
                    hours = int(seconds // 3600)
                    minutes = int((seconds % 3600) // 60)
                    secs = int(seconds % 60)
                    millis = int((seconds % 1) * 1000)
                    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
                
                for seg in transcript.segments:
                    start_str = format_timestamp(seg.start)
                    end_str = format_timestamp(seg.end)
                    print(f"\n{start_str} --> {end_str} [Speaker 0]")
                    print(seg.text)
                
                if transcript.language:
                    print(f"\nDetected language: {transcript.language}")
            else:
                # Fallback to plain text
                print("\n" + "="*60)
                print("TRANSCRIPTION:")
                print("="*60)
                print(transcript.text)
                if transcript.language:
                    print(f"\nDetected language: {transcript.language}")
                print("="*60)
        
        elif args.audio:
            # Process audio file
            audio_path = Path(args.audio).expanduser()
            if not audio_path.exists():
                print(f"❌ Audio file not found: {audio_path}")
                sys.exit(1)
            
            # Transcribe first
            print(f"🎤 Transcribing: {audio_path.name}")
            transcript = pipeline.voice_service.transcribe_audio_file(audio_path)
            print(f"\n👤 Transcription: {transcript.text}\n")
            if transcript.language:
                print(f"Detected language: {transcript.language}\n")
            
            # Process through pipeline
            response, results = pipeline.process_audio_file(audio_path)
            print(f"🤖 Daisy: {response}")
            if results:
                for result in results:
                    print(f"  - {result.output if result.success else result.error}")
        
        elif args.input:
            # Process text input
            response = pipeline.process_text(args.input)
            print(response)
        
        elif args.text:
            # Text mode
            pipeline.text_loop()
        
        else:
            # Voice mode (default)
            pipeline.voice_loop()
    
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

