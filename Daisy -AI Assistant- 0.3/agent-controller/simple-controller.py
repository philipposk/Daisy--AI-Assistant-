#!/usr/bin/env python3
"""
Simplified Agent Controller - Uses only macOS built-in tools
No heavy dependencies required
"""

import json
import subprocess
import time
import re
from pathlib import Path
from typing import Dict, Optional
import sys

class SimpleController:
    """Simplified controller using only macOS built-in tools"""
    
    def __init__(self):
        self.prefs_file = Path.home() / ".daisy" / "preferences.json"
        self.preferences = self.load_preferences()
        self.setup_directories()
    
    def setup_directories(self):
        """Create necessary directories"""
        (Path.home() / ".daisy").mkdir(exist_ok=True)
        self.prefs_file.parent.mkdir(exist_ok=True)
    
    def load_preferences(self) -> Dict:
        """Load user preferences for automatic decisions"""
        if self.prefs_file.exists():
            with open(self.prefs_file, 'r') as f:
                return json.load(f)
        return {
            "rules": [
                {
                    "pattern": ".*continue.*",
                    "action": "yes",
                    "description": "Always continue when asked"
                },
                {
                    "pattern": ".*step.*out of.*",
                    "action": "continue",
                    "description": "Continue multi-step processes"
                }
            ],
            "defaults": {
                "continue": "yes",
                "choice": "option_a"
            }
        }
    
    def save_preferences(self):
        """Save preferences to file"""
        with open(self.prefs_file, 'w') as f:
            json.dump(self.preferences, f, indent=2)
    
    def find_matching_rule(self, question: str) -> Optional[str]:
        """Find a matching rule and return its action"""
        for rule in self.preferences.get("rules", []):
            if re.search(rule["pattern"], question, re.IGNORECASE):
                return rule["action"]
        return None
    
    def text_to_speech(self, text: str):
        """Convert text to speech using macOS 'say' command"""
        try:
            subprocess.run(["say", text], check=True)
        except Exception as e:
            print(f"Error with TTS: {e}")
    
    def show_notification(self, title: str, message: str):
        """Show macOS notification"""
        script = f'''
        display notification "{message}" with title "{title}"
        '''
        try:
            subprocess.run(["osascript", "-e", script], check=True)
        except Exception as e:
            print(f"Error showing notification: {e}")
    
    def detect_run_instruction(self, text: str) -> Optional[Dict]:
        """Detect if text contains a 'run code' instruction"""
        run_patterns = [
            r"(?:go|please|can you|will you)?\s*(?:run|execute|test|build)\s+(?:this|the|that)?\s*(?:code|project|app|program|script)?",
            r"(?:open|launch|start)\s+(?:xcode|android studio|the project)",
            r"(?:click|press)\s+(?:run|build|test)\s+(?:button)?",
            r"(?:build|run|test)\s+(?:and|then)?\s*(?:run|build|test)?",
            r"go\s+(?:and|to)?\s*(?:run|execute)",
        ]
        
        for pattern in run_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return self.parse_run_instruction(text)
        return None
    
    def parse_run_instruction(self, text: str) -> Dict:
        """Parse what needs to be executed"""
        instruction = {
            "type": "unknown",
            "app": None,
            "action": None,
            "command": None
        }
        
        text_lower = text.lower()
        
        # Detect Xcode
        if "xcode" in text_lower or ".xcodeproj" in text_lower or "ios" in text_lower:
            instruction["type"] = "xcode"
            instruction["app"] = "Xcode"
            if "build" in text_lower:
                instruction["action"] = "build"
            elif "run" in text_lower or "execute" in text_lower:
                instruction["action"] = "run"
            else:
                instruction["action"] = "run"  # Default to run
        
        # Detect Android Studio
        elif "android" in text_lower or "gradle" in text_lower:
            instruction["type"] = "android"
            instruction["app"] = "Android Studio"
            if "build" in text_lower:
                instruction["action"] = "build"
            elif "run" in text_lower:
                instruction["action"] = "run"
        
        # Detect terminal command
        elif any(word in text_lower for word in ["terminal", "command", "bash", "shell", "npm", "python", "node"]):
            instruction["type"] = "terminal"
            # Try to extract command
            if "npm" in text_lower:
                instruction["command"] = "npm start"
            elif "python" in text_lower or "python3" in text_lower:
                instruction["command"] = "python3"
            elif "node" in text_lower:
                instruction["command"] = "node"
            else:
                instruction["command"] = None
        
        return instruction
    
    def execute_instruction(self, instruction: Dict) -> bool:
        """Execute the detected instruction"""
        try:
            if instruction["type"] == "xcode":
                return self.execute_xcode_instruction(instruction)
            elif instruction["type"] == "android":
                return self.execute_android_instruction(instruction)
            elif instruction["type"] == "terminal":
                return self.execute_terminal_instruction(instruction)
            return False
        except Exception as e:
            print(f"Error executing instruction: {e}")
            return False
    
    def execute_xcode_instruction(self, instruction: Dict) -> bool:
        """Execute Xcode-related instruction"""
        try:
            # Open Xcode
            script = '''
            tell application "Xcode"
                activate
            end tell
            '''
            subprocess.run(["osascript", "-e", script], check=True)
            time.sleep(2)  # Wait for Xcode to open
            
            # Execute action
            if instruction["action"] == "build":
                key_script = '''
                tell application "System Events"
                    tell process "Xcode"
                        keystroke "b" using {command down}
                    end tell
                end tell
                '''
            elif instruction["action"] == "run":
                key_script = '''
                tell application "System Events"
                    tell process "Xcode"
                        keystroke "r" using {command down}
                    end tell
                end tell
                '''
            else:
                return False
            
            subprocess.run(["osascript", "-e", key_script], check=True)
            self.text_to_speech(f"Executed Xcode {instruction['action']}")
            self.show_notification("Daisy Automation", f"Ran Xcode {instruction['action']}")
            return True
        except Exception as e:
            print(f"Error in Xcode execution: {e}")
            return False
    
    def execute_android_instruction(self, instruction: Dict) -> bool:
        """Execute Android Studio instruction"""
        try:
            script = '''
            tell application "Android Studio"
                activate
            end tell
            '''
            subprocess.run(["osascript", "-e", script], check=True)
            self.text_to_speech(f"Opened Android Studio")
            return True
        except Exception as e:
            print(f"Error in Android execution: {e}")
            return False
    
    def execute_terminal_instruction(self, instruction: Dict) -> bool:
        """Execute terminal command"""
        if instruction["command"]:
            try:
                result = subprocess.run(
                    instruction["command"].split(),
                    capture_output=True,
                    text=True
                )
                print(f"Command output: {result.stdout}")
                return True
            except Exception as e:
                print(f"Error executing command: {e}")
                return False
        return False
    
    def handle_question(self, question: str) -> Optional[str]:
        """Handle a question - check rules, detect run instructions, notify user, return action"""
        print(f"\n{'='*60}")
        print(f"[QUESTION] {question}")
        print(f"{'='*60}")
        
        # NEW: Check for run code instructions first
        run_instruction = self.detect_run_instruction(question)
        if run_instruction and run_instruction["type"] != "unknown":
            print(f"[AUTO-EXECUTE] Detected run instruction: {run_instruction}")
            self.text_to_speech(f"Automatically executing {run_instruction['type']} {run_instruction.get('action', 'command')}")
            self.show_notification("Daisy Automation", f"Running {run_instruction['type']} {run_instruction.get('action', '')}")
            
            if self.execute_instruction(run_instruction):
                print(f"✅ Successfully executed: {run_instruction}")
                return "executed"
            else:
                print(f"⚠️ Failed to execute: {run_instruction}")
        
        # Check for matching rule
        action = self.find_matching_rule(question)
        if action:
            print(f"[AUTO-DECISION] Applying rule: {action}")
            self.text_to_speech(f"Auto-applying decision: {action}")
            return action
        
        # Notify user
        self.text_to_speech(f"Cursor is asking: {question}")
        self.show_notification("Cursor Question", question[:100])
        
        print("\n[MANUAL INPUT REQUIRED]")
        print("Type your response, or press Enter to skip:")
        try:
            response = input("> ").strip()
            if response.lower() == "remember this":
                self.remember_response(question)
                return None
            return response if response else None
        except KeyboardInterrupt:
            return None
    
    def remember_response(self, question: str):
        """Ask user to create a rule for this question"""
        print("\nWhat action should I take for similar questions?")
        print("Examples: 'yes', 'continue', 'option_a', 'skip'")
        action = input("Action: ").strip()
        
        if action:
            rule = {
                "pattern": self.extract_keywords(question),
                "action": action,
                "description": f"Auto-response for: {question[:50]}"
            }
            self.preferences["rules"].append(rule)
            self.save_preferences()
            print(f"✅ Rule saved: {rule['pattern']} → {action}")
    
    def extract_keywords(self, text: str) -> str:
        """Extract keywords from text for pattern matching"""
        # Simple keyword extraction
        words = re.findall(r'\b\w+\b', text.lower())
        # Filter common words
        common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'from', 'do', 'you', 'we', 'should', 'would', 'want', 'this', 'that'}
        keywords = [w for w in words if w not in common_words and len(w) > 3]
        # Create regex pattern
        return '.*' + '.*'.join(keywords[:5]) + '.*'
    
    def monitor_cursor_output(self):
        """Monitor for Cursor questions (simplified - would need actual Cursor integration)"""
        print("🔍 Monitoring for Cursor questions...")
        print("💡 This is a simplified version. For full integration, see main.py")
        print("📝 To test, create a file at ~/.daisy/question.txt with a question")
        print("⏳ Waiting for questions...\n")
        
        question_file = Path.home() / ".daisy" / "question.txt"
        last_modified = 0
        
        while True:
            try:
                if question_file.exists():
                    current_modified = question_file.stat().st_mtime
                    if current_modified > last_modified:
                        last_modified = current_modified
                        question = question_file.read_text().strip()
                        if question:
                            action = self.handle_question(question)
                            if action:
                                # Write response back
                                response_file = Path.home() / ".daisy" / "response.txt"
                                response_file.write_text(action)
                                print(f"✅ Response written: {action}")
                time.sleep(1)
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(5)

def main():
    controller = SimpleController()
    controller.monitor_cursor_output()

if __name__ == "__main__":
    main()

