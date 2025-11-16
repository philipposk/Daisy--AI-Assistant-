#!/bin/bash

# Start Daisy Voice Assistant
# Usage: ./start-daisy.sh [--text]

cd "$(dirname "$0")"

echo "🌟 Starting Daisy Voice Assistant..."
echo ""

# Check if config exists
if [ ! -f ~/.daisy/config.json ]; then
    echo "⚠️  Configuration not found!"
    echo "Running setup..."
    ./setup-daisy-voice.sh
fi

# Check if API key is set
if grep -q '""' ~/.daisy/config.json 2>/dev/null || ! grep -q "openai_api_key" ~/.daisy/config.json 2>/dev/null; then
    echo "⚠️  OpenAI API key not found in config!"
    echo "Please set it in ~/.daisy/config.json or run ./setup-daisy-voice.sh"
    exit 1
fi

# Start Daisy
# Use 'python' if in conda environment, otherwise 'python3'
PYTHON_CMD=$(command -v python || command -v python3)

if [ "$1" == "--text" ]; then
    echo "📝 Starting in text mode..."
    $PYTHON_CMD agent-controller/daisy-assistant.py --text
else
    echo "🎤 Starting in voice mode..."
    echo "Make sure microphone permissions are granted!"
    $PYTHON_CMD agent-controller/daisy-assistant.py
fi

