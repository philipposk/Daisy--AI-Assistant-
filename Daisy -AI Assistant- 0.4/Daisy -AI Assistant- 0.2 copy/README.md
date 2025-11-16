# Daisy - AI Assistant Automation System

A comprehensive automation system that allows AI agents (like Cursor) to control your development workflow, including:
- 🖥️ **Desktop automation** (mouse, keyboard, screenshots)
- 🔧 **Development tools** (Xcode, Android Studio, Terminal)
- 🤖 **Automatic decision-making** based on your preferences
- 🔊 **Audio notifications** for questions (text-to-speech)
- 🔔 **System notifications** when your input is needed
- ⚙️ **Background operation** - works while you use your computer

## 🎯 What Problem Does This Solve?

You know the workflow:
1. You ask Cursor to do something
2. Cursor generates code and gives instructions
3. You have to manually: open Xcode → click buttons → run code
4. When Cursor asks questions, you have to stop and answer
5. This breaks your flow!

**Daisy automates steps 3-4** so Cursor can:
- Open apps, click buttons, run commands automatically
- Handle questions based on your preferences
- Notify you (with audio) only when your input is needed

## 🏗️ Architecture

```
┌─────────────┐
│   Cursor    │ (Your AI assistant)
└──────┬──────┘
       │ Uses MCP Protocol
       ▼
┌──────────────────────┐
│  MCP Desktop Server  │ (Controls mouse/keyboard/apps)
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│  Agent Controller    │ (Handles questions, auto-decisions)
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│  Your Mac Desktop    │ (Xcode, Android Studio, etc.)
└──────────────────────┘
```

## 📦 Components

1. **MCP Server** (`mcp-desktop-automation/`) - Provides desktop control via Model Context Protocol
2. **Agent Controller** (`agent-controller/`) - Monitors Cursor and handles questions/decisions
3. **Automation Scripts** (`automation/`) - Mac-specific automation (AppleScript, Python)
4. **Preferences System** (`~/.daisy/preferences.json`) - Stores your rules for auto-decisions

## 🚀 Quick Start

**See `QUICKSTART.md` for a 3-step setup guide.**

Or follow these steps:

1. **Run setup**:
   ```bash
   cd "/Users/phktistakis/Daisy -AI Assistant- 0.1"
   ./setup.sh
   ```

2. **Configure Cursor** to use MCP server (see `CURSOR_SETUP.md`)

3. **Start agent controller**:
   ```bash
   python3 agent-controller/simple-controller.py
   ```

4. **Test in Cursor**:
   - "Take a screenshot"
   - "Open Xcode"

## 📚 Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - 3-step setup guide
- **[USAGE_GUIDE.md](USAGE_GUIDE.md)** - Detailed usage instructions
- **[CURSOR_SETUP.md](CURSOR_SETUP.md)** - How to configure Cursor

## 🔧 Features

### Desktop Automation
- Screenshots (full screen or specific windows)
- Mouse clicks (by position or UI element text)
- Keyboard input and key combinations
- Open applications
- Find and interact with UI elements

### Development Tools
- Xcode automation (build, run, clean)
- Android Studio automation
- Terminal command execution
- Custom automation scripts

### Intelligent Question Handling
- **Auto-decisions** based on your preferences
- **Audio notifications** (macOS `say` command)
- **System notifications** for important questions
- **Learning system** - remembers your choices

### Background Operation
- Runs in background (doesn't interfere with normal use)
- Only activates when Cursor requests it
- Can run as a launchd service

## 🛡️ Security

⚠️ **This system gives AI agents control over your computer!**

- Only use with trusted AI assistants (Cursor)
- Review preferences before auto-approving actions
- Monitor the agent's behavior
- Use sandboxing if running untrusted code

## 🔄 How It Works

1. **You ask Cursor** → "Build and run my Xcode project"
2. **Cursor uses MCP tools** → Calls `open_application("Xcode")`, `key_press(["cmd", "r"])`, etc.
3. **MCP server executes** → Opens Xcode, presses Cmd+R
4. **If Cursor asks a question** → Agent controller:
   - Checks your preferences for matching rules
   - If rule found → Auto-responds
   - If no rule → Plays audio + shows notification → Waits for your answer

## 🎨 Customization

- **Add automation**: Edit MCP server tools in `mcp-desktop-automation/server.js`
- **Custom scripts**: Add to `automation/` directory
- **Question patterns**: Edit `~/.daisy/preferences.json`
- **Notification style**: Modify `agent-controller/simple-controller.py`

## 📝 Requirements

- **macOS** (uses AppleScript, `say`, `osascript`)
- **Node.js** (for MCP server)
- **Python 3** (for agent controller - simple version works with built-in libraries)
- **Optional**: Tesseract OCR (for screenshot text extraction)

## 🤝 Contributing

This is a framework you can extend:
- Add new MCP tools
- Improve question detection
- Add support for other IDEs
- Enhance automation scripts

## 📄 License

See LICENSE file (if applicable)

## ❓ Support

- Check `USAGE_GUIDE.md` for troubleshooting
- Review logs: `~/.daisy/logs/`
- Check preferences: `~/.daisy/preferences.json`

