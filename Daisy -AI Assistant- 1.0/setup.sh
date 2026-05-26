#!/bin/bash
# Setup script for Daisy Assistant 0.6

set -e

echo "🌼 Setting up Daisy Assistant 0.6..."

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "✅ Found Python $PYTHON_VERSION"

# Create virtual environment (optional but recommended)
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
echo "📦 Upgrading pip..."
pip install --upgrade pip

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Install system dependencies (macOS)
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "🍎 Installing macOS dependencies..."
    
    # Check for Homebrew
    if ! command -v brew &> /dev/null; then
        echo "⚠️  Homebrew not found. Some features may not work."
        echo "   Install Homebrew: https://brew.sh"
    else
        # Install portaudio for pyaudio
        if ! brew list portaudio &> /dev/null; then
            echo "📦 Installing portaudio (for microphone support)..."
            brew install portaudio
        fi
        
        # Install ffmpeg for audio conversion (optional)
        if ! command -v ffmpeg &> /dev/null; then
            echo "💡 ffmpeg not found (optional, for audio conversion)"
            echo "   Install with: brew install ffmpeg"
        fi
    fi
fi

# Create config directory and default config
echo "⚙️  Setting up configuration..."
mkdir -p ~/.daisy
if [ ! -f ~/.daisy/config.yaml ]; then
    echo "📝 Creating default config..."
    python3 << EOF
from config import load_config, save_config
from pathlib import Path

config = load_config()
save_config(config, Path.home() / ".daisy" / "config.yaml")
print("✅ Config created at ~/.daisy/config.yaml")
EOF
else
    echo "✅ Config already exists at ~/.daisy/config.yaml"
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p ~/.daisy/notes
mkdir -p ~/.daisy/conversations
mkdir -p ~/.daisy/logs

echo ""
echo "✅ Setup complete!"
echo ""
echo "📝 Next steps:"
echo "1. Set your API keys in ~/.daisy/config.yaml or as environment variables:"
echo "   export OPENAI_API_KEY='your-key-here'"
echo "   export GROQ_API_KEY='your-key-here'  # Optional"
echo ""
echo "2. Run Daisy:"
echo "   python3 daisy.py              # Voice mode"
echo "   python3 daisy.py --text       # Text mode"
echo "   python3 daisy.py --input 'Hello'  # Process text and exit"
echo ""

