#!/bin/bash
# Download high-quality Piper TTS model for Daisy

echo "🎤 Downloading high-quality Piper TTS model..."
echo ""

# Create voices directory if it doesn't exist
mkdir -p ~/.local/share/piper/voices

# Download high-quality Lessac model (female voice)
echo "📥 Downloading en_US-lessac-high model..."
cd ~/.local/share/piper/voices

# Download model file
curl -L -o en_US-lessac-high.onnx \
  "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/high/en_US-lessac-high.onnx"

# Download config file
curl -L -o en_US-lessac-high.onnx.json \
  "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/high/en_US-lessac-high.onnx.json"

echo ""
if [ -f "en_US-lessac-high.onnx" ] && [ -f "en_US-lessac-high.onnx.json" ]; then
    echo "✅ High-quality Piper model downloaded successfully!"
    echo "   Location: ~/.local/share/piper/voices/en_US-lessac-high.onnx"
    echo ""
    echo "🎉 Daisy will now use high-quality voice!"
else
    echo "❌ Download failed. Please download manually from:"
    echo "   https://github.com/rhasspy/piper/releases"
    echo ""
    echo "   Or visit: https://huggingface.co/rhasspy/piper-voices/tree/main/en/en_US/lessac/high"
fi

