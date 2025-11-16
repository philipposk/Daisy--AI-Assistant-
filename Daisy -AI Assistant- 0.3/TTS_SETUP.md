# 🔊 TTS Setup Guide for Daisy

Daisy now supports multiple TTS (Text-to-Speech) engines for better voice quality. Here's how to set them up:

## 🎯 Quick Start

**Recommended: Piper TTS** (fast, high-quality, open-source, offline)

```bash
# Install Piper TTS on macOS
brew install piper-tts

# Download a good female voice model
# Visit: https://github.com/rhasspy/piper/releases
# Download: en_US-lessac-medium.onnx (or en_US-lessac-high.onnx for better quality)
# Place it in: ~/.local/share/piper/voices/
```

## 📋 Available TTS Engines

### 1. **Piper TTS** ⭐ Recommended
- **Pros**: Fast, high-quality, completely offline, open-source, no API costs
- **Cons**: Requires model download (~10-50MB per voice)
- **Installation**:
  ```bash
  brew install piper-tts
  ```
- **Voice Models**: Download from https://github.com/rhasspy/piper/releases
  - `en_US-lessac-medium` - Good quality, medium size
  - `en_US-lessac-high` - Better quality, larger size
  - `en_US-amy-medium` - Alternative female voice

### 2. **Coqui TTS**
- **Pros**: Very high quality, neural TTS, multiple voices
- **Cons**: Slower, requires more resources, larger download
- **Installation**:
  ```bash
  pip3 install TTS
  ```
- **First run will download models automatically**

### 3. **OpenAI TTS**
- **Pros**: Very high quality, natural voices, cloud-based
- **Cons**: Requires API key, costs money, requires internet
- **Already configured** if you have OpenAI API key

### 4. **macOS say** (Fallback)
- **Pros**: Always available, no installation needed
- **Cons**: Less natural sounding (robot-like)
- **Voices**: Samantha, Karen, Victoria, etc.

## ⚙️ Configuration

Edit `~/.daisy/config.json`:

```json
{
  "tts_engine": "piper",
  "piper_model": "en_US-lessac-medium",
  "coqui_model": "tts_models/en/ljspeech/tacotron2-DDC",
  "say_voice": "Samantha"
}
```

### TTS Engine Options:
- `"piper"` - Use Piper TTS (recommended)
- `"coqui"` - Use Coqui TTS
- `"openai"` - Use OpenAI TTS
- `"say"` - Use macOS say command

## 🎤 Speech Recognition

Daisy now uses **Groq Whisper** (same as Praiser) for much better speech recognition, especially for whispers and quiet speech.

**Setup**:
1. Get a Groq API key from https://console.groq.com
2. Add to `~/.daisy/config.json`:
   ```json
   {
     "groq_api_key": "your-groq-api-key-here"
   }
   ```
3. Or set environment variable:
   ```bash
   export GROQ_API_KEY="your-groq-api-key-here"
   ```

## 🔄 Automatic Fallback

Daisy will automatically fall back through TTS engines:
1. **Primary** (configured in `tts_engine`)
2. **Coqui TTS** (if primary fails)
3. **OpenAI TTS** (if available)
4. **macOS say** (always available as final fallback)

## 🧪 Testing

After setup, run Daisy:
```bash
python3 agent-controller/daisy-assistant.py
```

You should see:
```
🌟 Daisy is ready!
🧠 LLM Model: gpt-3.5-turbo
🔊 TTS Engine: piper
   ✅ Piper TTS: Available (fast, high-quality open-source)
🎤 Speech Recognition: Groq Whisper (whisper-large-v3-turbo)
   ✅ Excellent at understanding whispers and quiet speech
```

## 📚 More Information

- **Piper TTS**: https://github.com/rhasspy/piper
- **Coqui TTS**: https://github.com/coqui-ai/TTS
- **Groq API**: https://console.groq.com

