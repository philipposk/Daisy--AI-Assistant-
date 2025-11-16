# Setting up Cursor with Daisy MCP Server

## Step 1: Configure MCP Server in Cursor

Cursor supports MCP servers through configuration. Add this to your Cursor settings:

### Via Settings UI:
1. Open Cursor Settings
2. Go to "Features" → "Model Context Protocol"
3. Add a new server with:
   - Name: `desktop-automation`
   - Command: `node`
   - Args: `["/absolute/path/to/mcp-desktop-automation/server.js"]`

### Via Config File:
Edit `~/.cursor/mcp.json` (or equivalent config location):

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

## Step 2: Start the Agent Controller

Run the agent controller in the background:

```bash
cd "/Users/phktistakis/Daisy -AI Assistant- 0.1"
python3 agent-controller/main.py &
```

Or create a launchd service to run it automatically (see `launchd-service.plist`).

## Step 3: Test It

Ask Cursor to:
- "Take a screenshot"
- "Open Xcode"
- "Click the Run button in Xcode"

The MCP server will handle these requests automatically!

## How It Works

1. **You ask Cursor** to do something (e.g., "Build and run the project")
2. **Cursor uses MCP tools** to control your desktop (open Xcode, click buttons, etc.)
3. **When Cursor asks a question**, the agent controller:
   - Detects the question (via screenshot OCR or log monitoring)
   - Converts it to audio and plays it
   - Shows a notification
   - Applies your preferences/rules if available
   - Waits for your voice/text response if needed

## Background Operation

To run in the background while you use your computer:

1. **Use a separate desktop/virtual environment** (optional)
2. **Run agent as a launchd service** (see below)
3. **The automation runs only when Cursor requests it** - doesn't interfere with normal use

