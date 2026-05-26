# Starting Daisy Assistant

## Quick Start

### 1. Set Your API Key

You need an OpenAI API key to use Daisy. Set it as an environment variable:

```bash
export OPENAI_API_KEY='your-api-key-here'
```

Or add it to your `~/.zshrc` to make it permanent:
```bash
echo 'export OPENAI_API_KEY="your-api-key-here"' >> ~/.zshrc
source ~/.zshrc
```

### 2. Navigate to Daisy Directory

```bash
cd "/Users/phktistakis/Devoloper Projects/Daisy -AI Assistant-/Daisy -AI Assistant- 0.6"
```

### 3. Start Daisy

**Text Mode** (recommended for first try):
```bash
python3 daisy.py --text
```

**Voice Mode** (requires microphone):
```bash
python3 daisy.py
```

**One-shot Text** (process one message and exit):
```bash
python3 daisy.py --input "Create a note about Python"
```

## Usage Examples

Once Daisy is running, you can:

### Create Notes
- "Create a note about machine learning"
- "Take a note: Python async programming"
- "Save this: Meeting notes from today"

### Create Tasks
- "Add a task to review pull requests"
- "I need to call mom tomorrow"
- "Remind me to buy groceries"

### Create Reminders
- "Remind me to call mom at 3pm"
- "Set a reminder for the meeting tomorrow"

### Run Commands (if whitelisted)
- "Run ls -la"
- "Execute python script.py"

### General Conversation
- "Hello, how are you?"
- "What can you do?"
- "Tell me a joke"

## Exiting

- Type `quit`, `exit`, or `q` to exit
- Or press `Ctrl+C`

## Troubleshooting

### "No API key found"
- Make sure you've set `OPENAI_API_KEY` environment variable
- Check with: `echo $OPENAI_API_KEY`

### "Microphone not available"
- Use `--text` mode instead
- Or check macOS privacy settings for microphone access

### "LLM call failed"
- Check your API key is valid
- Check you have credits/quota on your OpenAI account
- Try again - sometimes it's a temporary issue

### "Import errors"
- Make sure you've installed dependencies: `pip install -r requirements.txt`

## Configuration

Edit `~/.daisy/config.yaml` to customize:
- LLM model (gpt-4, gpt-3.5-turbo, etc.)
- TTS voice
- Safety settings (whitelisted commands, etc.)
- File paths



