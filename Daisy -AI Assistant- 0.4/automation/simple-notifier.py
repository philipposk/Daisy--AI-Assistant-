#!/usr/bin/env python3
"""
Simple notification wrapper for macOS
Provides text-to-speech and notifications without heavy dependencies
"""

import subprocess
import sys
import os

def say(text: str):
    """Use macOS built-in 'say' command for text-to-speech"""
    subprocess.run(["say", text])

def notify(title: str, message: str):
    """Use osascript for macOS notifications"""
    script = f'''
    display notification "{message}" with title "{title}"
    '''
    subprocess.run(["osascript", "-e", script])

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: simple-notifier.py <say|notify> [args...]")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "say":
        text = " ".join(sys.argv[2:])
        say(text)
    elif command == "notify":
        title = sys.argv[2] if len(sys.argv) > 2 else "Notification"
        message = " ".join(sys.argv[3:]) if len(sys.argv) > 3 else ""
        notify(title, message)
    else:
        print(f"Unknown command: {command}")

