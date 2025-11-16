#!/usr/bin/env python3
"""
Agent Controller - Monitors Cursor and handles questions/decisions
This acts as a "grand agent" that coordinates between Cursor and desktop automation
"""

import json
import os
import subprocess
import time
import re
from pathlib import Path
from typing import Dict, List, Optional
import speech_recognition as sr
from gtts import gTTS
import playsound
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class CursorMonitor(FileSystemEventHandler):
    """Monitors Cursor's activity and extracts questions"""
    
    def __init__(self, controller):
        self.controller = controller
        self.cursor_log_path = Path.home() / "Library/Application Support/Cursor/logs"
        
    def on_modified(self, event):
        if event.is_directory:
            return
        # Check if it's a Cursor log file
        if 'main.log' in str(event.src_path):
            self.controller.check_for_questions()

class DecisionPreferences:
    """Manages user preferences for automatic decision-making"""
    
    def __init__(self, prefs_file: Path):
        self.prefs_file = prefs_file
        self.preferences = self.load_preferences()
    
    def load_preferences(self) -> Dict:
        if self.prefs_file.exists():
            with open(self.prefs_file, 'r') as f:
                return json.load(f)
        return {
            "rules": [],
            "defaults": {}
        }
    
    def save_preferences(self):
        with open(self.prefs_file, 'w') as f:
            json.dump(self.preferences, f, indent=2)
    
    def add_rule(self, pattern: str, action: str, description: str = ""):
        """Add a rule: when question matches pattern, take action"""
        rule = {
            "pattern": pattern,
            "action": action,
            "description": description
        }
        self.preferences["rules"].append(rule)
        self.save_preferences()
    
    def find_matching_rule(self, question: str) -> Optional[Dict]:
        """Find a rule that matches the question"""
        for rule in self.preferences["rules"]:
            if re.search(rule["pattern"], question, re.IGNORECASE):
                return rule
        return None
    
    def get_default_action(self, question_type: str) -> Optional[str]:
        """Get default action for a question type"""
        return self.preferences["defaults"].get(question_type)

class AgentController:
    """Main controller that coordinates everything"""
    
    def __init__(self):
        self.preferences = DecisionPreferences(
            Path.home() / ".daisy" / "preferences.json"
        )
        self.question_queue = []
        self.monitor = None
        self.setup_directories()
        
    def setup_directories(self):
        """Create necessary directories"""
        (Path.home() / ".daisy").mkdir(exist_ok=True)
        (Path.home() / ".daisy" / "audio").mkdir(exist_ok=True)
        (Path.home() / ".daisy" / "screenshots").mkdir(exist_ok=True)
    
    def check_for_questions(self):
        """Check Cursor's output for questions that need user input"""
        # This would integrate with Cursor's API or log files
        # For now, this is a placeholder - you'd need to implement
        # actual integration based on Cursor's output format
        pass
    
    def extract_question_from_screenshot(self, screenshot_path: str) -> Optional[str]:
        """Use OCR to extract question text from screenshot"""
        try:
            import pytesseract
            from PIL import Image
            
            image = Image.open(screenshot_path)
            text = pytesseract.image_to_string(image)
            
            # Look for question patterns
            question_patterns = [
                r"do you want (?:me to )?(?:to )?continue",
                r"how should (?:we|I) (?:proceed|continue)",
                r"which option (?:do|would) you (?:prefer|want)",
                r"step \d+ out of \d+",
                r"choose (?:option|path) [A-Z]",
            ]
            
            for pattern in question_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    return text  # Return full text context
            
            return None
        except Exception as e:
            print(f"Error extracting question: {e}")
            return None
    
    def text_to_speech(self, text: str):
        """Convert text to speech and play it"""
        try:
            audio_path = Path.home() / ".daisy" / "audio" / f"question_{int(time.time())}.mp3"
            tts = gTTS(text=text, lang='en', slow=False)
            tts.save(str(audio_path))
            playsound.playsound(str(audio_path))
            # Clean up
            audio_path.unlink()
        except Exception as e:
            print(f"Error with TTS: {e}")
            # Fallback to macOS say command
            subprocess.run(["say", text])
    
    def show_notification(self, title: str, message: str):
        """Show macOS notification"""
        script = f'''
        display notification "{message}" with title "{title}"
        '''
        subprocess.run(["osascript", "-e", script])
    
    def handle_question(self, question: str, context: Dict = None):
        """Handle a question from Cursor"""
        print(f"\n[QUESTION DETECTED] {question}")
        
        # Check for matching rule
        rule = self.preferences.find_matching_rule(question)
        if rule:
            print(f"[AUTO-DECISION] Applying rule: {rule['description']}")
            print(f"[ACTION] {rule['action']}")
            self.text_to_speech(f"Auto-applying decision: {rule['action']}")
            return rule['action']
        
        # Play question as audio
        audio_text = f"Cursor is asking: {question}"
        self.text_to_speech(audio_text)
        
        # Show notification
        self.show_notification(
            "Cursor Question",
            question[:100] + ("..." if len(question) > 100 else "")
        )
        
        # Wait for user input
        print("\nOptions:")
        print("1. Type your answer")
        print("2. Say 'remember this' to create a rule")
        print("3. Say 'auto' to let agent decide")
        
        # Here you'd integrate voice recognition or wait for text input
        # For now, returning None to indicate manual input needed
        return None
    
    def process_screenshot(self, screenshot_path: str):
        """Process a screenshot, extract question, and handle it"""
        question = self.extract_question_from_screenshot(screenshot_path)
        if question:
            return self.handle_question(question)
        return None
    
    def listen_for_voice_command(self) -> Optional[str]:
        """Listen for voice commands from user"""
        try:
            r = sr.Recognizer()
            with sr.Microphone() as source:
                print("Listening for your response...")
                audio = r.listen(source, timeout=5, phrase_time_limit=10)
            text = r.recognize_google(audio)
            print(f"Heard: {text}")
            return text
        except sr.WaitTimeoutError:
            return None
        except Exception as e:
            print(f"Error recognizing speech: {e}")
            return None
    
    def start_monitoring(self):
        """Start monitoring Cursor for questions"""
        print("Starting agent controller...")
        print("Monitoring Cursor for questions...")
        
        # In a real implementation, you'd monitor Cursor's logs or API
        # For now, this is a framework you can extend
        
        # Example: monitor a directory for screenshots
        event_handler = FileSystemEventHandler()
        event_handler.on_created = lambda e: self.process_screenshot(e.src_path) if e.src_path.endswith('.png') else None
        
        observer = Observer()
        observer.schedule(
            event_handler,
            str(Path.home() / ".daisy" / "screenshots"),
            recursive=False
        )
        observer.start()
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()

def main():
    controller = AgentController()
    controller.start_monitoring()

if __name__ == "__main__":
    main()

