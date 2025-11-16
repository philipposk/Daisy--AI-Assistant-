# 📋 Installation Instructions for You

## ✅ Already Done (I Did This)

- ✅ Installed all Node.js dependencies
- ✅ Installed all Python dependencies  
- ✅ Created all directories
- ✅ Created configuration files
- ✅ Made all scripts executable
- ✅ Tested components
- ✅ Created preferences file

## 🔧 What You Need to Do (Your Part)

### Step 1: Configure Cursor (5 minutes)

**Find Cursor's MCP configuration:**
1. Open Cursor
2. Go to Settings (⌘,)
3. Look for "Model Context Protocol" or "MCP" in Features
4. Add the MCP server with these details:
   - **Name**: `desktop-automation`
   - **Command**: `node`
   - **Args**: `["/Users/phktistakis/Daisy -AI Assistant- 0.1/mcp-desktop-automation/server.js"]`

**OR check for config file:**
- Look for `~/.cursor/mcp.json` or similar
- If it exists, add the server config from `cursor-mcp-config.json`
- If it doesn't exist, you may need to use the UI method above

**Restart Cursor** after adding the server.

### Step 2: Grant Permissions (2 minutes)

When you first try to use automation, macOS will ask for:

1. **Accessibility Access**
   - System Settings → Privacy & Security → Accessibility
   - Enable for Terminal or Command Line Tools

2. **Screen Recording Access**  
   - System Settings → Privacy & Security → Screen Recording
   - Enable for Terminal or Command Line Tools

**Tip**: If you're not prompted, you can manually grant access in System Settings.

### Step 3: Test It (1 minute)

In Cursor, try:
```
Take a screenshot
```

If it works, you're all set! ✅

### Step 4: Start Agent Controller (Optional)

If you want automatic question handling:

```bash
cd "/Users/phktistakis/Daisy -AI Assistant- 0.1"
./start-agent.sh
```

Leave this running in the background (or use a separate terminal).

## 🎯 That's It!

You're done! The system is ready to use.

### Quick Reference

**Files created:**
- `cursor-mcp-config.json` - Cursor configuration (you need to add this)
- `~/.daisy/preferences.json` - Your auto-decision rules
- `start-agent.sh` - Start the agent controller
- `test-mcp-server.sh` - Test the MCP server

**Commands:**
```bash
# Start agent
./start-agent.sh

# Test MCP server  
./test-mcp-server.sh

# View preferences
cat ~/.daisy/preferences.json

# Edit preferences
nano ~/.daisy/preferences.json
```

**See also:**
- `SETUP_COMPLETE.md` - What was done automatically
- `QUICKSTART.md` - Quick start guide
- `USAGE_GUIDE.md` - Detailed usage

## 🆘 Troubleshooting

**MCP server not working?**
- Check Node.js: `node --version`
- Check config: Look at `cursor-mcp-config.json`
- Test: `./test-mcp-server.sh`

**Permissions issues?**
- Check System Settings → Privacy & Security
- Grant Accessibility and Screen Recording

**Agent controller not working?**
- Check Python: `python3 --version`
- Check dependencies: `pip3 list | grep watchdog`
- Check logs: `~/.daisy/logs/`

## 📞 Need Help?

Check the documentation:
- `QUICKSTART.md` - Quick start
- `USAGE_GUIDE.md` - Detailed guide
- `CURSOR_SETUP.md` - Cursor configuration details

