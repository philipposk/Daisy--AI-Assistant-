# 🗣️ How to Talk to Daisy

Daisy is now running! Here's how to interact with her:

## Current Setup

Daisy is monitoring for questions from Cursor. When Cursor asks you something, Daisy will:
1. 🔊 **Speak it aloud** (using macOS `say` command)
2. 🔔 **Show a notification** (what you saw!)
3. 💬 **Wait for your response**

## How to Respond to Daisy

### Method 1: Terminal (Currently Running)

If you see Daisy running in a terminal, you can type your answer directly:

```
[QUESTION DETECTED] Do you want to continue?
[MANUAL INPUT REQUIRED]
Type your response, or press Enter to skip:
> yes
```

Just type your answer after the `>` prompt and press Enter.

### Method 2: File-Based Communication

Daisy is watching for questions in a file. You can respond by:

**Step 1:** Check what Daisy is asking:
```bash
cat ~/.daisy/question.txt
```

**Step 2:** Write your response:
```bash
echo "yes" > ~/.daisy/response.txt
# or
echo "continue" > ~/.daisy/response.txt
# or
echo "option_a" > ~/.daisy/response.txt
```

**Step 3:** Daisy will read the response and act on it!

### Method 3: Edit Preferences (Auto-Answers)

To make Daisy automatically answer certain questions:

**Edit preferences:**
```bash
nano ~/.daisy/preferences.json
```

**Add rules like:**
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

Then Daisy will auto-answer matching questions!

## What Daisy Heard/Detected

If Daisy spoke and showed a notification, it means:
- ✅ Daisy is running
- ✅ She detected a question (possibly from Cursor or a test file)
- ✅ She's waiting for your response

## Quick Commands

**See what Daisy is asking:**
```bash
cat ~/.daisy/question.txt
```

**Answer Daisy:**
```bash
echo "your_answer_here" > ~/.daisy/response.txt
```

**Check Daisy's preferences:**
```bash
cat ~/.daisy/preferences.json
```

**Edit preferences (auto-answers):**
```bash
nano ~/.daisy/preferences.json
```

**View Daisy's logs:**
```bash
tail -f ~/.daisy/logs/agent-controller.log
```

**Test Daisy:**
```bash
echo "Do you want to continue?" > ~/.daisy/question.txt
```

## Common Responses

When Daisy asks, you can respond with:

- **Continue questions**: `yes`, `continue`, `proceed`
- **Choice questions**: `option_a`, `option_b`, `first`, `second`
- **Stop questions**: `no`, `stop`, `cancel`
- **Skip questions**: Press Enter (empty response) or type `skip`

## Setting Up Auto-Answers

Want Daisy to automatically answer? Edit `~/.daisy/preferences.json`:

```json
{
  "rules": [
    {
      "pattern": ".*do you want to continue.*",
      "action": "yes",
      "description": "Always continue"
    },
    {
      "pattern": ".*which option.*",
      "action": "option_a",
      "description": "Always choose option A"
    }
  ]
}
```

Patterns use regex syntax. Actions can be any text response.

## Voice Commands (Future)

The full version supports voice input, but the simple controller uses:
- Terminal input (type your answer)
- File-based communication (`response.txt`)
- Preferences/rules (auto-answers)

## Need Help?

**Daisy not responding?**
- Check if she's running: `ps aux | grep simple-controller`
- Check logs: `cat ~/.daisy/logs/agent-controller.log`

**Can't find the question?**
- Check: `cat ~/.daisy/question.txt`
- Or look at the terminal where Daisy is running

**Want to restart Daisy?**
- Stop: Press `Ctrl+C` in the terminal
- Start: `./start-agent.sh`

## Pro Tip 💡

Set up auto-answers in preferences so Daisy can handle common questions automatically, and only notify you for important decisions!

