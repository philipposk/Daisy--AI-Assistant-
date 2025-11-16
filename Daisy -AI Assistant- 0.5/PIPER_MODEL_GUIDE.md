# 🎤 Piper TTS Model Quality Guide

## Current Setting: `en_US-lessac-medium`

### Why Medium Quality?

**Medium quality** (`-medium`) is used as a **balance** between:
- ✅ **Good audio quality** (22.05 kHz, natural-sounding)
- ✅ **Fast processing** (15-20M parameters, real-time capable)
- ✅ **Reasonable file size** (~10-15MB per model)

### Quality Tiers Comparison

| Quality | Sample Rate | Parameters | Speed | Quality | File Size | Best For |
|---------|-------------|------------|-------|---------|-----------|----------|
| **x-low** | 16 kHz | ~5M | ⚡⚡⚡ Very Fast | ⭐⭐ Basic | ~3MB | Embedded devices |
| **low** | 16 kHz | ~8M | ⚡⚡ Fast | ⭐⭐⭐ Good | ~5MB | Low-end devices |
| **medium** | 22.05 kHz | 15-20M | ⚡ Balanced | ⭐⭐⭐⭐ Very Good | ~10-15MB | **Most use cases** ⭐ |
| **high** | 22.05 kHz | 30-40M | 🐌 Slower | ⭐⭐⭐⭐⭐ Excellent | ~20-30MB | High-end devices |

## Available Female Voices (English)

### Medium Quality (Current)
- `en_US-lessac-medium` - Warm, natural female voice ⭐ **Current**
- `en_US-amy-medium` - Clear, professional female voice
- `en_US-jenny-medium` - Friendly, conversational female voice

### High Quality (Better Sound)
- `en_US-lessac-high` - **Best quality** version of Lessac (recommended upgrade)
- `en_US-amy-high` - High-quality Amy voice
- `en_US-jenny-high` - High-quality Jenny voice

### Low Quality (Faster)
- `en_US-lessac-low` - Faster, lower quality
- `en_US-amy-low` - Faster, lower quality

## Should You Upgrade to High Quality?

### ✅ **Upgrade to HIGH if:**
- You want the **best possible voice quality**
- Your Mac can handle slightly slower processing
- You don't mind ~20-30MB model files
- You want the most natural-sounding Daisy

### ⚠️ **Stay with MEDIUM if:**
- You want **fast response times**
- You're on a slower/older Mac
- You want smaller model files
- Current quality is good enough

## How to Change

### Option 1: Edit Config File
Edit `~/.daisy/config.json`:
```json
{
  "piper_model": "en_US-lessac-high"  // Change from -medium to -high
}
```

### Option 2: Download High Quality Model
1. Visit: https://github.com/rhasspy/piper/releases
2. Download: `en_US-lessac-high.onnx` and `en_US-lessac-high.onnx.json`
3. Place in: `~/.local/share/piper/voices/`
4. Update config as above

## Recommendation

For a **voice assistant like Daisy**, I recommend **HIGH quality** because:
- ✅ Better user experience (more natural)
- ✅ Modern Macs can handle it easily
- ✅ Quality matters more than speed for voice assistants
- ✅ The delay is minimal (~100-200ms more)

**Current**: `en_US-lessac-medium` (good balance)  
**Recommended**: `en_US-lessac-high` (best quality)

Would you like me to upgrade Daisy to use high-quality Piper models?

