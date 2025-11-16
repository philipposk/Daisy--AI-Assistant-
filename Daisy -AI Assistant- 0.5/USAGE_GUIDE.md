# Daisy - Usage Guide

## Overview

Daisy is an automation system that allows Cursor (or any MCP-compatible AI) to:
- **Control your desktop** (mouse, keyboard, screenshots)
- **Automate development tools** (Xcode, Android Studio)
- **Handle questions automatically** based on your preferences
- **Notify you** when your input is needed

## Architecture

```
┌─────────────┐
│   Cursor    │ (Your AI assistant)
└──────┬──────┘
       │ Uses MCP Protocol
       ▼
┌──────────────────────┐
│  MCP Desktop Server  │ (Controls mouse/keyboard)
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│  Agent Controller    │ (Handles questions)
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│  Your Mac Desktop    │ (Xcode, Terminal, etc.)
└──────────────────────┘
```

## Setup

### 1. Install Dependencies

```bash
cd "/Users/phktistakis/Daisy -AI Assistant- 0.1"
./setup.sh
```

This installs:
- Node.js dependencies for MCP server
- Python dependencies (optional - for full OCR/voice features)
- Tesseract OCR (optional)

### 2. Configure Cursor

#### Option A: Via Cursor Settings UI
1. Open Cursor Settings
2. Go to "Features" → "Model Context Protocol" or "MCP"
3. Add server:
   - **Name**: `desktop-automation`
   - **Command**: `node`
   - **Args**: `["/Users/phktistakis/Daisy -AI Assistant- 0.1/mcp-desktop-automation/server.js"]`

#### Option B: Via Config File
Create/edit `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "desktop-automation": {
      "command": "node",
      "args": [
        "/Users/phktistakis/Daisy -AI Assistant- 0.1/mcp-desktop-automation/server.js"
      ]
    }
  }
}
```

### 3. Start Agent Controller

**Simple version** (no heavy dependencies):
```bash
python3 "/Users/phktistakis/Daisy -AI Assistant- 0.1/agent-controller/simple-controller.py"
```

**Full version** (with OCR, voice recognition):
```bash
python3 "/Users/phktistakis/Daisy -AI Assistant- 0.1/agent-controller/main.py"
```

**Run in background** (as a service):
```bash
# Install launchd service
cp launchd-service.plist ~/Library/LaunchAgents/com.daisy.agent-controller.plist
launchctl load ~/Library/LaunchAgents/com.daisy.agent-controller.plist
```

## Usage

### Basic Usage

1. **Start the agent controller** (see above)

2. **Ask Cursor to do things**:
   - "Take a screenshot"
   - "Open Xcode"
   - "Click the Run button in Xcode"
   - "Build and run the project"
   - "Open Android Studio and build the project"

3. **When Cursor asks a question**:
   - The agent controller will:
     - ✅ Check your preferences/rules
     - 🔊 Play the question as audio (using macOS `say`)
     - 🔔 Show a notification
     - ⏳ Wait for your response (if needed)

### Setting Up Automatic Decisions

#### Method 1: Interactive Learning

When the agent asks a question:
1. Type your answer
2. Type `remember this` if you want to save it as a rule
3. Enter the action to take for similar questions

#### Method 2: Manual Configuration

Edit `~/.daisy/preferences.json`:

```json
{
  "rules": [
    {
      "pattern": ".*do you want to continue.*",
      "action": "yes",
      "description": "Always continue when asked"
    },
    {
      "pattern": ".*which option.*",
      "action": "option_a",
      "description": "Always choose option A"
    },
    {
      "pattern": ".*step.*out of.*",
      "action": "continue",
      "description": "Continue multi-step processes"
    }
  ],
  "defaults": {
    "continue": "yes",
    "choice": "option_a"
  }
}
```

Patterns use regex syntax. Actions can be:
- `yes` / `no`
- `continue` / `stop`
- `option_a` / `option_b` / etc.
- Any custom text response

### Testing

#### Test MCP Server
In Cursor, try:
- "Take a screenshot of the screen"
- "Open the Terminal application"
- "What window is currently active?"

#### Test Agent Controller
Create a question file:
```bash
echo "Do you want to continue?" > ~/.daisy/question.txt
```

The controller will detect it, play audio, and wait for your response.

#### Test Automation
In Cursor:
- "Open Xcode and build the project at /path/to/project"
- "Take a screenshot of the Xcode window"
- "Click the Run button in Xcode"

## Advanced Features

### Screenshot + OCR Question Detection

The full agent controller can:
1. Take screenshots when Cursor shows a question
2. Use OCR to extract text from the screenshot
3. Automatically detect questions and handle them

This requires:
- Tesseract OCR: `brew install tesseract`
- Python packages from `requirements.txt`

### Voice Commands

The full agent controller supports voice input:
- When a question appears, speak your response
- The system will transcribe it and send back to Cursor

Requires:
- `SpeechRecognition` package
- Microphone access

### Background Operation

Run everything in the background:
1. Install launchd service (see above)
2. Agent controller runs automatically on login
3. Works even when you're using your computer normally

## Troubleshooting

### MCP Server Not Working
- Check Node.js is installed: `node --version`
- Check MCP server runs: `node mcp-desktop-automation/server.js`
- Check Cursor's MCP configuration

### Permissions Issues
You may need to grant:
- **Accessibility** access (for mouse/keyboard control)
- **Screen Recording** access (for screenshots)
- **Terminal/Command Line Tools** access

Grant in: System Settings → Privacy & Security → Accessibility / Screen Recording

### Agent Controller Not Detecting Questions
- Check if question file exists: `~/.daisy/question.txt`
- For full integration, you'd need to monitor Cursor's logs or API
- Current version is a framework you can extend

## Extending the System

### Add New Automation Actions

Edit `mcp-desktop-automation/server.js`:
- Add new tools to `ListToolsRequestSchema`
- Implement handlers in `CallToolRequestSchema`

### Customize Question Detection

Edit `agent-controller/main.py`:
- Modify `check_for_questions()` to monitor Cursor's output
- Add new question patterns in `extract_question_from_screenshot()`

### Add New Development Tools

Create automation scripts:
- `automation/vscode-automation.scpt` (for VS Code)
- `automation/intellij-automation.sh` (for IntelliJ)
- Add handlers in MCP server to call them

## Security Considerations

⚠️ **Important**: This system gives AI agents control over your computer!

- Only use with trusted AI assistants (Cursor)
- Review preferences before auto-approving actions
- Monitor the agent's behavior
- Use sandboxing if running untrusted code

## Next Steps

1. **Start simple**: Use `simple-controller.py` first
2. **Test automation**: Try basic commands in Cursor
3. **Add preferences**: Set up rules for common questions
4. **Extend as needed**: Add custom automation for your workflow

## Support

For issues or questions:
- Check logs: `~/.daisy/logs/`
- Review preferences: `~/.daisy/preferences.json`
- Test components individually

