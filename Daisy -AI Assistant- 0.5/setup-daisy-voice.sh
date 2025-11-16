#!/bin/bash

echo "🌟 Setting up Daisy Personal Assistant..."

# Install Python dependencies
echo "📦 Installing Python packages..."
pip3 install --upgrade openai speechrecognition pyaudio pydub

# Set up audio permissions (macOS)
echo ""
echo "🔊 Audio Permissions"
echo "Please grant microphone access in System Preferences > Security & Privacy > Privacy > Microphone"
echo ""

# Create config if it doesn't exist
if [ ! -f ~/.daisy/config.json ]; then
    echo "⚙️  Creating default configuration..."
    mkdir -p ~/.daisy
    cat > ~/.daisy/config.json << EOF
{
  "openai_api_key": "",
  "llm_model": "gpt-4",
  "voice": "nova",
  "voice_speed": 1.0,
  "system_prompt": "You are Daisy, a friendly and helpful personal AI assistant. You have a warm, professional, and slightly conversational personality. You help with tasks, answer questions, and engage in natural conversations. Keep responses concise but friendly. Use natural speech patterns.",
  "auto_listen": true,
  "save_conversations": true
}
EOF
fi

# Check for API key
if grep -q '""' ~/.daisy/config.json 2>/dev/null || ! grep -q "openai_api_key" ~/.daisy/config.json 2>/dev/null; then
    echo "⚠️  OpenAI API key not found in config!"
    echo ""
    read -p "Do you want to add it now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "Enter your OpenAI API key: " api_key
        python3 << PYTHON
import json
from pathlib import Path
config_path = Path.home() / '.daisy' / 'config.json'
config = json.load(open(config_path)) if config_path.exists() else {}
config['openai_api_key'] = '$api_key'
json.dump(config, open(config_path, 'w'), indent=2)
print("✅ API key saved!")
PYTHON
    fi
else
    echo "✅ OpenAI API key found in configuration"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "To start Daisy:"
echo "  python3 agent-controller/daisy-assistant.py"
echo ""
echo "Or for text-only mode:"
echo "  python3 agent-controller/daisy-assistant.py --text"
echo ""

