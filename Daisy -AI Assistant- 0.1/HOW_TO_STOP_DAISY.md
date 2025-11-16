# 🛑 How to Stop Daisy

## Quick Stop

**Stop Daisy agent controller:**
```bash
pkill -f simple-controller
```

**Or more forcefully:**
```bash
pkill -9 -f simple-controller
```

## Check if Daisy is Running

```bash
ps aux | grep simple-controller | grep -v grep
```

**If you see output** → Daisy is running  
**If no output** → Daisy is stopped

## Stop Options

### Option 1: Stop Agent Controller (Keeps MCP Server)
**What this does:**
- Stops the agent controller (monitors questions)
- Keeps MCP server active (Cursor can still use tools)
- You won't hear Daisy speak or see notifications

**Command:**
```bash
pkill -f simple-controller
```

**When to use:** You want Cursor to use Daisy's tools, but don't want audio/notifications

### Option 2: Stop Everything
**What this does:**
- Stops agent controller
- MCP server stops when Cursor closes (or you can stop it)

**Stop agent controller:**
```bash
pkill -f simple-controller
```

**Stop MCP server:**
- Just restart Cursor, or
- MCP server stops automatically when not in use

### Option 3: Stop and Disable Permanently

**Stop agent controller:**
```bash
pkill -f simple-controller
```

**Disable from starting automatically:**
If you set up the launchd service:
```bash
launchctl unload ~/Library/LaunchAgents/com.daisy.agent-controller.plist
```

## What Happens When You Stop Daisy

### Agent Controller Stops
- ❌ No more audio notifications ("Executed Xcode run")
- ❌ No more detecting questions from files
- ❌ No more automatic execution of instructions
- ✅ Cursor can still use MCP tools directly (Option A)
- ✅ Desktop automation tools still work

### MCP Server (Continues Running)
- ✅ Still available for Cursor to use
- ✅ Cursor can still call `open_application`, `key_press`, etc.
- ✅ Runs automatically when Cursor needs it
- ✅ Stops when Cursor closes

## Restart Daisy

**To start Daisy again:**
```bash
cd "/Users/phktistakis/Daisy -AI Assistant- 0.1"
nohup ./start-agent.sh > ~/.daisy/logs/agent.log 2>&1 &
```

**Or run in foreground:**
```bash
cd "/Users/phktistakis/Daisy -AI Assistant- 0.1"
./start-agent.sh
```

## Temporarily Disable Without Stopping

### Disable Audio Only
Edit `agent-controller/simple-controller.py` and comment out `text_to_speech()` calls.

### Disable Notifications Only
Edit `agent-controller/simple-controller.py` and comment out `show_notification()` calls.

### Keep Running but Silent
- Daisy keeps running
- Still monitors for questions
- No audio or notifications
- Still executes commands automatically

## Verify Daisy is Stopped

```bash
# Check process
ps aux | grep simple-controller | grep -v grep

# Check logs (if still writing)
tail ~/.daisy/logs/agent.log
```

**Expected:** No process found, logs show "👋 Goodbye!" or similar

## Quick Reference

**Stop:**
```bash
pkill -f simple-controller
```

**Start:**
```bash
cd "/Users/phktistakis/Daisy -AI Assistant- 0.1"
./start-agent.sh
```

**Check:**
```bash
ps aux | grep simple-controller | grep -v grep
```

**Force stop:**
```bash
pkill -9 -f simple-controller
```

---

**Note:** Stopping Daisy only stops the agent controller (Option B). Cursor can still use Daisy's MCP tools directly (Option A) without the agent controller running.


