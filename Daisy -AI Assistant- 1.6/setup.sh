#!/bin/bash
# Setup script for Daisy Assistant 1.5

set -e

echo "🌼 Setting up Daisy Assistant 1.5..."

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
PYTHON_MAJOR=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1)
PYTHON_MINOR=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f2)

echo "✅ Found Python $PYTHON_VERSION"

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]); then
    echo "⚠️  Python 3.10+ recommended. Some features may not work on $PYTHON_VERSION."
fi

# Create virtual environment (optional but recommended)
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
echo "📦 Upgrading pip..."
pip install --upgrade pip --quiet

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt --quiet

# Install system dependencies (macOS)
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "🍎 Checking macOS dependencies..."

    # Check for Homebrew
    if ! command -v brew &> /dev/null; then
        echo "⚠️  Homebrew not found. Some features (mic, TTS) may not work."
        echo "   Install Homebrew: https://brew.sh"
    else
        # Install portaudio for pyaudio
        if ! brew list portaudio &> /dev/null 2>&1; then
            echo "📦 Installing portaudio (microphone support)..."
            brew install portaudio
        else
            echo "✅ portaudio already installed"
        fi

        # ffmpeg (optional, for audio conversion)
        if ! command -v ffmpeg &> /dev/null; then
            echo "💡 ffmpeg not found (optional). Install: brew install ffmpeg"
        fi
    fi

    # Check macOS permissions
    echo ""
    echo "🔐 Checking macOS permissions..."
    python3 -c "
import sys
sys.path.insert(0, '.')
try:
    from services.permissions import check_permissions, summary_line
    perms = check_permissions()
    print('  ' + summary_line(perms))
except Exception as e:
    print(f'  ⚠️  Could not check permissions: {e}')
"
fi

# Create config directory and default config
echo ""
echo "⚙️  Setting up configuration..."
mkdir -p ~/.daisy/notes ~/.daisy/conversations ~/.daisy/logs

if [ ! -f ~/.daisy/config.yaml ]; then
    echo "📝 Creating default config at ~/.daisy/config.yaml ..."
    python3 -c "
import sys, yaml
sys.path.insert(0, '.')
from config import load_config
cfg = load_config()
# Write minimal config
import yaml
from pathlib import Path
Path.home().joinpath('.daisy', 'config.yaml').write_text(
    '# Daisy 1.5 config — edit as needed\n'
    '# Set API keys here OR store them in macOS Keychain:\n'
    '#   python3 -c \"from services.keychain import set_secret; set_secret(\\\"OPENAI_API_KEY\\\", \\\"sk-...\\\")\" \n'
    '\n'
    'llm:\n'
    '  provider: openai   # openai | anthropic | groq | local_http\n'
    '  model: gpt-4o-mini\n'
    '\n'
    'stt:\n'
    '  provider: openai   # openai | local_http | whisper\n'
    '\n'
    'tts:\n'
    '  provider: openai   # openai | piper | kokoro | system\n'
    '  voice: nova\n'
    '\n'
    'reminder:\n'
    '  enabled: true\n'
    '\n'
    'paths:\n'
    '  notes_directory: ~/.daisy/notes\n'
    '  tasks_file: ~/.daisy/tasks.md\n'
    '  reminders_file: ~/.daisy/reminders.json\n'
    '  audit_log: ~/.daisy/audit.log\n'
    '  database_path: ~/.daisy/daisy.db\n'
)
print('✅ Config created')
"
else
    echo "✅ Config already exists at ~/.daisy/config.yaml"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📝 Quick start"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. Add your API key (recommended: macOS Keychain):"
echo "   python3 -c \"from services.keychain import set_secret; set_secret('OPENAI_API_KEY', 'sk-...')\""
echo "   OR set env var: export OPENAI_API_KEY='sk-...'"
echo ""
echo "2. Start Daisy:"
echo "   python3 daisy_app.py --port 5188 --no-ui   # Backend only (headless)"
echo "   python3 daisy_app.py --port 5188            # With webview window"
echo "   python3 daisy_menubar.py                    # Menu-bar app"
echo ""
echo "3. Open the UI:"
echo "   http://localhost:5188/"
echo ""
echo "4. (Optional) Auto-start on login:"
echo "   python3 tools/launchd_setup.py install"
echo ""
echo "5. Run tests:"
echo "   python3 tests/run_tests.py"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
