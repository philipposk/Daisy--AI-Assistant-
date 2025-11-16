# 💬 How to Interact with Daisy

If Daisy spoke and showed a notification, here's how to respond:

## 🎯 Current Situation

Daisy is monitoring for questions from **Cursor**. When Cursor asks you something, Daisy will:
1. 🔊 **Speak it aloud** (what you heard!)
2. 🔔 **Show a notification** (what you saw!)
3. ⏳ **Wait for your response**

## 📝 How to Respond (3 Ways)

### Method 1: Terminal (If Daisy is Running There)

Look for a terminal window where Daisy is running. You'll see something like:

```
[QUESTION DETECTED] Do you want to continue?
[MANUAL INPUT REQUIRED]
Type your response, or press Enter to skip:
> 
```

**Just type your answer after the `>` and press Enter:**
- Type: `yes` (then Enter)
- Or: `continue` (then Enter)
- Or: Press Enter alone to skip

### Method 2: File-Based Response (If No Terminal Visible)

If Daisy is running in the background, respond via file:

**Step 1:** Check what Daisy is asking:
```bash
cat ~/.daisy/question.txt
```

**Step 2:** Write your response:
```bash
echo "yes" > ~/.daisy/response.txt
```

Or for different answers:
```bash
echo "continue" > ~/.daisy/response.txt
echo "option_a" > ~/.daisy/response.txt
echo "no" > ~/.daisy/response.txt
```

### Method 3: Set Auto-Answers (Future Questions)

Edit preferences so Daisy answers automatically:

```bash
nano ~/.daisy/preferences.json
```

Add rules like:
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

## 🔍 Find Out What Daisy Asked

**Check the notification:**
- Look at your macOS notification - it should show the question

**Check the question file:**
```bash
cat ~/.daisy/question.txt
```

**Check if Daisy is running:**
```bash
ps aux | grep simple-controller
```

**View Daisy's output:**
- If Daisy started in a terminal, look at that terminal window
- If it's in background, check logs: `tail ~/.daisy/logs/*.log`

## 🎤 Quick Response Commands

**Common responses:**
```bash
# Continue/proceed
echo "yes" > ~/.daisy/response.txt
echo "continue" > ~/.daisy/response.txt

# Choose option
echo "option_a" > ~/.daisy/response.txt
echo "option_b" > ~/.daisy/response.txt

# Stop/cancel
echo "no" > ~/.daisy/response.txt
echo "stop" > ~/.daisy/response.txt

# Skip (empty response)
echo "" > ~/.daisy/response.txt
```

## 🧪 Test Daisy

Want to see how it works? Test Daisy:

```bash
echo "Do you want to continue?" > ~/.daisy/question.txt
```

Daisy will:
1. Speak: "Do you want to continue?"
2. Show notification
3. Wait for your response

Then respond:
```bash
echo "yes" > ~/.daisy/response.txt
```

## 📋 Quick Reference

**See what Daisy asked:**
```bash
cat ~/.daisy/question.txt
```

**Answer Daisy:**
```bash
echo "your_answer" > ~/.daisy/response.txt
```

**View preferences:**
```bash
cat ~/.daisy/preferences.json
```

**Edit preferences (auto-answers):**
```bash
nano ~/.daisy/preferences.json
```

**Check if Daisy is running:**
```bash
ps aux | grep simple-controller
```

**Start Daisy (if not running):**
```bash
cd "/Users/phktistakis/Daisy -AI Assistant- 0.1"
./start-agent.sh
```

**Stop Daisy:**
- If in terminal: Press `Ctrl+C`
- If in background: `pkill -f simple-controller`

## 💡 Pro Tips

1. **Set up auto-answers** - Edit `~/.daisy/preferences.json` so Daisy handles common questions automatically

2. **Check the terminal** - If you started Daisy with `./start-agent.sh`, look at that terminal window for the question

3. **Use simple answers** - Daisy understands: `yes`, `no`, `continue`, `stop`, `option_a`, `option_b`, etc.

4. **Remember patterns** - Type `remember this` in the terminal to save your answer for similar questions

## 🆘 Need Help?

**Daisy not responding?**
- Check if running: `ps aux | grep simple-controller`
- Restart: `./start-agent.sh`

**Can't find the question?**
- Check notification history (macOS Notification Center)
- Check: `cat ~/.daisy/question.txt`
- Look at terminal where Daisy is running

**Want to restart?**
```bash
pkill -f simple-controller
cd "/Users/phktistakis/Daisy -AI Assistant- 0.1"
./start-agent.sh
```

