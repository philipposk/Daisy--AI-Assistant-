#!/bin/bash
# Setup script for Daisy AI Assistant

set -e

echo "🚀 Setting up Daisy AI Assistant..."

# Create directories
mkdir -p ~/.daisy/{audio,screenshots,logs}

# Install MCP server dependencies
echo "📦 Installing MCP server dependencies..."
cd mcp-desktop-automation
npm install
cd ..

# Install Python dependencies
echo "📦 Installing Python dependencies..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed"
    exit 1
fi

python3 -m pip install --user -r agent-controller/requirements.txt

# Install tesseract for OCR (macOS)
if ! command -v tesseract &> /dev/null; then
    echo "📦 Installing tesseract for OCR..."
    if command -v brew &> /dev/null; then
        brew install tesseract
    else
        echo "⚠️  Please install tesseract manually: brew install tesseract"
    fi
fi

# Make scripts executable
chmod +x automation/android-studio-automation.sh
chmod +x automation/simple-notifier.py
chmod +x agent-controller/main.py
chmod +x mcp-desktop-automation/server.js

echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Configure Cursor to use the MCP server (see CURSOR_SETUP.md)"
echo "2. Run the agent controller: python3 agent-controller/main.py"
echo "3. Start using Cursor - the agent will automatically handle questions!"

