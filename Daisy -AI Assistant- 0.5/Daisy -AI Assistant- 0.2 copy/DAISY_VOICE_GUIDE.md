# 🎙️ Daisy Voice Assistant Guide

## ✨ Features

Daisy now has full voice assistant capabilities:
- 🎤 **Natural female voice** using OpenAI TTS (Nova voice - warm and friendly)
- 🧠 **LLM-powered conversations** using GPT-4
- 💬 **Two-way voice conversations** with speech recognition
- 🧠 **Conversation memory** - remembers context throughout the conversation
- 📝 **Conversation history** - saves all conversations locally

## 🚀 Quick Start

### 1. Install Dependencies

```bash
./setup-daisy-voice.sh
```

Or manually:
```bash
pip3 install openai speechrecognition pyaudio pydub
```

### 2. Start Daisy

**Voice Conversation Mode** (recommended):
```bash
python3 agent-controller/daisy-assistant.py
```

**Text Mode** (if microphone not available):
```bash
python3 agent-controller/daisy-assistant.py --text
```

## 🎤 Voice Options

### OpenAI TTS Voices

The configuration uses **Nova** by default (warm, friendly female voice). Other options:

- **`nova`** - Warm, friendly female (default) ⭐ Recommended
- **`shimmer`** - Soft, gentle female voice
- **`alloy`** - Neutral, clear voice
- **`echo`** - Strong, confident voice
- **`fable`** - British accent
- **`onyx`** - Deep, authoritative voice

To change the voice, edit `~/.daisy/config.json`:
```json
{
  "voice": "shimmer",
  "voice_speed": 1.0
}
```

## 🧠 LLM Models

Default model is **GPT-4** for best quality. You can also use:
- `gpt-4` - Best quality (default)
- `gpt-4-turbo` - Faster, balanced
- `gpt-3.5-turbo` - Faster, cheaper

Edit `~/.daisy/config.json`:
```json
{
  "llm_model": "gpt-4-turbo"
}
```

## 💬 Usage

### Voice Mode

1. Start Daisy:
   ```bash
   python3 agent-controller/daisy-assistant.py
   ```

2. Daisy will greet you with voice
3. Speak naturally - she'll listen and respond
4. Say "quit", "exit", or "goodbye" to end

### Text Mode

1. Start in text mode:
   ```bash
   python3 agent-controller/daisy-assistant.py --text
   ```

2. Type your messages
3. Daisy responds with voice (if available)
4. Type "quit" to exit

## ⚙️ Configuration

Edit `~/.daisy/config.json`:

```json
{
  "openai_api_key": "your-key-here",
  "llm_model": "gpt-4",
  "voice": "nova",
  "voice_speed": 1.0,
  "system_prompt": "Custom personality prompt...",
  "auto_listen": true,
  "save_conversations": true
}
```

### Configuration Options

- **`voice`** - TTS voice name (nova, shimmer, alloy, etc.)
- **`voice_speed`** - Speech speed (0.25 to 4.0, default 1.0)
- **`llm_model`** - OpenAI model (gpt-4, gpt-4-turbo, gpt-3.5-turbo)
- **`system_prompt`** - Daisy's personality and behavior
- **`auto_listen`** - Automatically listen after speaking (true/false)
- **`save_conversations`** - Save conversation history (true/false)

## 🎯 Integration

### Use Daisy in Your Code

```python
from agent_controller.daisy_assistant import DaisyAssistant

# Initialize
assistant = DaisyAssistant()

# Get response to text input
response = assistant.respond_to_text("What's the weather today?")
print(response)  # Daisy will also speak this

# Access conversation history
for msg in assistant.conversation_history:
    print(f"{msg.role}: {msg.content}")
```

## 📁 File Locations

- **Configuration**: `~/.daisy/config.json`
- **Conversations**: `~/.daisy/conversations/`
- **Audio files**: `~/.daisy/audio/`
- **Logs**: `~/.daisy/logs/`

## 🔧 Troubleshooting

### Microphone Not Working

1. **Grant permissions**:
   - System Preferences > Security & Privacy > Privacy > Microphone
   - Enable access for Terminal or your Python app

2. **Test microphone**:
   ```bash
   python3 -c "import speech_recognition as sr; r = sr.Recognizer(); m = sr.Microphone(); print('Microphone found:', m.list_microphone_names())"
   ```

3. **Use text mode**:
   ```bash
   python3 agent-controller/daisy-assistant.py --text
   ```

### Audio Not Playing

- Check system volume
- Try different TTS voice
- Check `~/.daisy/audio/` for generated files

### API Key Issues

1. Check your API key in `~/.daisy/config.json`
2. Verify it's valid: https://platform.openai.com/api-keys
3. Ensure you have credits on your OpenAI account

### pyaudio Installation Issues (macOS)

```bash
# Install PortAudio first
brew install portaudio

# Then install pyaudio
pip3 install pyaudio
```

## 💡 Tips

1. **Better voice recognition**: Speak clearly, reduce background noise
2. **Privacy**: Conversations are saved locally, only sent to OpenAI API for processing
3. **Cost**: Using GPT-4 costs more than GPT-3.5-turbo. Monitor your usage at https://platform.openai.com/usage
4. **Personality**: Customize Daisy's personality via `system_prompt` in config
5. **Conversation history**: All conversations are saved in `~/.daisy/conversations/`

## 🔐 Security Note

⚠️ **Important**: Your API key is stored in plaintext in `~/.daisy/config.json`. 

For better security:
- Keep the config file private: `chmod 600 ~/.daisy/config.json`
- Consider using environment variable: `export OPENAI_API_KEY='your-key'`
- Don't commit the config file to version control

## 📝 Example Conversation

```
🌟 Daisy is ready!
🎤 Voice: nova (female)
🧠 Model: gpt-4

============================================================
💬 Daisy is ready to chat!
Speak naturally, or type 'quit' to exit
============================================================

🤖 Daisy: Hi! I'm Daisy, your personal assistant. How can I help you today?

🎤 Listening...
👤 You: What's the weather like today?

🔄 Thinking...
🤖 Daisy: I don't have access to real-time weather data, but I'd be happy to help you find it! Would you like me to search for the weather in your location?

🎤 Listening...
👤 You: Yes, please. I'm in San Francisco.

🔄 Thinking...
🤖 Daisy: I understand you'd like weather for San Francisco. However, I can't directly access the internet or real-time data. You could check a weather app or website, or I could help you write a script to fetch weather data if you'd like!
```

## 🎉 Enjoy!

Daisy is now your personal AI assistant with natural voice conversations. Have fun chatting with her!

