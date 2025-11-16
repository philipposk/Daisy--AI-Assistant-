# 🎤 Download Piper TTS Voice Models

## ✅ Voice Already Downloaded!

The recommended voice **en_US-lessac-medium** has been downloaded to:
```
~/.local/share/piper/voices/
```

Files:
- `en_US-lessac-medium.onnx` (60MB - the voice model)
- `en_US-lessac-medium.onnx.json` (4.8KB - the config)

## 📥 Where to Download More Voices

### **Option 1: Hugging Face (Recommended - Works Best)**

**Base URL:** https://huggingface.co/rhasspy/piper-voices/tree/main

**Direct download format:**
```
https://huggingface.co/rhasspy/piper-voices/resolve/main/{language}/{language_code}/{voice_name}/{quality}/{file}
```

**Examples:**
- **en_US-lessac-medium**: 
  - Model: https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx
  - Config: https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json

- **en_US-lessac-high** (better quality):
  - Model: https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/high/en_US-lessac-high.onnx
  - Config: https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/high/en_US-lessac-high.onnx.json

- **en_US-amy-medium** (different voice):
  - Model: https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx
  - Config: https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx.json

### **Option 2: Browse All Voices**

Visit: **https://huggingface.co/rhasspy/piper-voices/tree/main**

Navigate through:
- Language folders (en, es, fr, de, etc.)
- Language code folders (en_US, en_GB, etc.)
- Voice name folders (lessac, amy, etc.)
- Quality folders (medium, high)
- Download both `.onnx` and `.onnx.json` files

### **Option 3: Other Sources**

- **SpiritBox**: https://www.spiritbox.ca/voices.html (Free voices)
- **GraceDabbieri's GitHub**: https://github.com/GraceDabbieri/piper-tts-voices (Custom voices)
- **BryceBeattie.com**: https://brycebeattie.com/pages/piper-tts-voices.html

## 🚀 Quick Download Commands

### Download en_US-lessac-medium (Already done ✅)
```bash
cd ~/.local/share/piper/voices
curl -L -o en_US-lessac-medium.onnx "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx"
curl -L -o en_US-lessac-medium.onnx.json "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json"
```

### Download en_US-lessac-high (Better quality)
```bash
cd ~/.local/share/piper/voices
curl -L -o en_US-lessac-high.onnx "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/high/en_US-lessac-high.onnx"
curl -L -o en_US-lessac-high.onnx.json "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/high/en_US-lessac-high.onnx.json"
```

### Download en_US-amy-medium (Different voice)
```bash
cd ~/.local/share/piper/voices
curl -L -o en_US-amy-medium.onnx "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx"
curl -L -o en_US-amy-medium.onnx.json "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx.json"
```

## 📁 File Location

All voice files should be placed in:
```
~/.local/share/piper/voices/
```

Or:
```
/Users/phktistakis/.local/share/piper/voices/
```

## ⚙️ Change Voice in Config

Edit `~/.daisy/config.json`:

```json
{
  "piper_model": "en_US-lessac-medium"
}
```

Change to:
- `"en_US-lessac-high"` for better quality
- `"en_US-amy-medium"` for different voice
- Or any other voice you downloaded

## ✅ Verify Installation

Check your voices:
```bash
ls -lh ~/.local/share/piper/voices/
```

You should see your downloaded `.onnx` and `.onnx.json` files.

## 🎉 Ready!

Once voice files are in place, Daisy will automatically use Piper TTS with your chosen voice!
