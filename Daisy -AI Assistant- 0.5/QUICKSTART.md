# Daisy - Quick Start Guide

## What Daisy Does

Daisy automates your development workflow by allowing Cursor to:
- ✅ **Control your desktop** (mouse, keyboard, screenshots)
- ✅ **Open apps** (Xcode, Android Studio, Terminal)
- ✅ **Run commands** (builds, tests)
- ✅ **Handle questions automatically** based on your preferences
- ✅ **Notify you** when your input is needed (audio + notifications)

## Installation (3 Steps)

### 1. Run Setup Script
```bash
cd "/Users/phktistakis/Daisy -AI Assistant- 0.1"
./setup.sh
```

### 2. Configure Cursor
Edit Cursor settings to add MCP server:
- Settings → Features → MCP
- Add server:
  - **Command**: `node`
  - **Args**: `["/Users/phktistakis/Daisy -AI Assistant- 0.1/mcp-desktop-automation/server.js"]`

Or create `~/.cursor/mcp.json`:
```json
{
  "mcpServers": {
    "desktop-automation": {
      "command": "node",
      "args": ["/Users/phktistakis/Daisy -AI Assistant- 0.1/mcp-desktop-automation/server.js"]
    }
  }
}
```

### 3. Start Agent Controller
```bash
python3 "/Users/phktistakis/Daisy -AI Assistant- 0.1/agent-controller/simple-controller.py"
```

Leave this running in the background.

## Usage

### Test It
In Cursor, try:
- "Take a screenshot"
- "Open Xcode"
- "What window is active?"

### How It Works

1. **You ask Cursor** → "Build and run my Xcode project"
2. **Cursor uses MCP tools** → Opens Xcode, clicks Build, clicks Run
3. **If Cursor asks a question**:
   - Agent controller checks your preferences
   - If rule found → auto-responds
   - If no rule → plays audio + shows notification → waits for your answer

### Set Up Auto-Decisions

**Option 1**: When asked a question, type `remember this` and specify the action.

**Option 2**: Edit `~/.daisy/preferences.json`:
```json
{
  "rules": [
    {
      "pattern": ".*continue.*",
      "action": "yes",
      "description": "Always continue"
    }
  ]
}
```

## How Background Operation Works

The system can run in the background:

1. **MCP Server**: Runs when Cursor uses it (automatic)
2. **Agent Controller**: Run as a service:
   ```bash
   cp launchd-service.plist ~/Library/LaunchAgents/com.daisy.agent-controller.plist
   launchctl load ~/Library/LaunchAgents/com.daisy.agent-controller.plist
   ```

The automation **only runs when Cursor requests it**, so it doesn't interfere with your normal computer use.

## Common Questions

**Q: Does it work while I'm using my computer?**
A: Yes! Automation only runs when Cursor requests it. You can use your computer normally.

**Q: How does it know when Cursor asks a question?**
A: Currently uses a file-based system (`~/.daisy/question.txt`). For full integration, you'd monitor Cursor's logs/API (extensible framework provided).

**Q: Is it safe?**
A: Yes, but review preferences before auto-approving actions. The agent only does what Cursor requests through MCP.

**Q: Can I customize it?**
A: Yes! Edit the MCP server tools, add automation scripts, customize question detection.

## Next Steps

1. Read `USAGE_GUIDE.md` for detailed instructions
2. Test basic automation in Cursor
3. Set up your preferences for auto-decisions
4. Extend the system as needed

## Troubleshooting

**Permissions**: Grant Accessibility and Screen Recording access in System Settings.

**Not working?**: 
- Check MCP server runs: `node mcp-desktop-automation/server.js`
- Check agent controller is running
- Check Cursor's MCP configuration

See `USAGE_GUIDE.md` for more troubleshooting.

