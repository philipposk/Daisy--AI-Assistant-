# 🎙️ How to Run Daisy

## ✅ Setup Complete!

All packages are installed and microphone is ready!

## 🚀 Run Daisy (Voice Mode)

Since you're using **conda**, use `python` instead of `python3`:

```bash
cd "/Users/phktistakis/Daisy -AI Assistant- 0.2"
python agent-controller/daisy-assistant.py
```

Or use the start script:
```bash
./start-daisy.sh
```

## 📝 Run Daisy (Text Mode)

If you want to type instead of speak:

```bash
python agent-controller/daisy-assistant.py --text
```

Or:
```bash
./start-daisy.sh --text
```

## 🎤 What to Expect

1. **Daisy will greet you** with her voice: *"Hi! I'm Daisy, your personal assistant. How can I help you today?"*

2. **You can speak naturally** - Daisy will listen and respond

3. **Say "quit", "exit", or "goodbye"** to end the conversation

## 🔐 Microphone Permissions

The first time you run Daisy, macOS may ask for microphone permission:
- Click **"Allow"** when prompted
- Or go to: System Preferences > Security & Privacy > Privacy > Microphone
- Enable Terminal or Python

## 💡 Tips

- **Speak clearly** for best recognition
- **Reduce background noise** if possible
- Daisy uses **OpenAI Whisper** for speech recognition (very accurate!)
- All conversations are saved in `~/.daisy/conversations/`

## 🎉 Enjoy!

Daisy is now fully functional with voice input and output!

