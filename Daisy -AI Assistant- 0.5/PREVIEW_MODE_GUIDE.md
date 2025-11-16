# 🎛️ Preview Mode vs Autonomous Mode

## Overview

Daisy's intelligent build automation supports two modes:

1. **Autonomous Mode** (Default) - Executes actions automatically
2. **Preview Mode** - Shows actions before executing, asks for approval

---

## 🚀 Autonomous Mode (Default)

**What it does:**
- Executes all actions automatically
- No prompts or confirmations
- Fast and hands-off

**When to use:**
- You trust the automation
- You want fully hands-off operation
- Common fixes (pod install, npm install) are safe

**Configuration:**
```json
{
  "automation": {
    "mode": "autonomous"
  }
}
```

---

## 👀 Preview Mode

**What it does:**
- Shows action plan before executing
- Asks for approval on each fix
- Auto-approves safe actions (pod install, npm install, etc.)

**When to use:**
- You want to review actions first
- Working on critical projects
- Learning what the automation does

**Configuration:**
```json
{
  "automation": {
    "mode": "preview",
    "preview_actions": true,
    "auto_approve_patterns": [
      "pod install",
      "npm install",
      "pip install",
      "./gradlew build --refresh-dependencies"
    ]
  }
}
```

---

## ⚙️ How to Configure

### Option 1: Edit Preferences File

Edit `~/.daisy/preferences.json`:

```json
{
  "automation": {
    "mode": "preview",  // or "autonomous"
    "preview_actions": true,
    "auto_approve_patterns": [
      "pod install",
      "npm install"
    ]
  }
}
```

### Option 2: Per-Request Override

When calling `build_with_retry` in Cursor, you can override:

```
Use build_with_retry with ide: "xcode", previewMode: true
```

---

## 🔄 How It Works

### Autonomous Mode Flow:
```
Build fails → Detect error → Apply fix automatically → Retry
```

### Preview Mode Flow:
```
Build fails → Detect error → Show action plan → Wait for approval → Apply fix → Retry
```

### Auto-Approve in Preview Mode:
```
Build fails → Detect error → Check if safe action (pod install, etc.) → Apply automatically → Retry
```

---

## 📋 Auto-Approve Patterns

These actions are automatically approved even in preview mode:

- `pod install` - Safe dependency installation
- `npm install` - Safe package installation
- `pip install` - Safe Python package installation
- `./gradlew build --refresh-dependencies` - Safe Gradle refresh

**To add more:**
Edit `auto_approve_patterns` in preferences.json

---

## 🎯 Examples

### Example 1: Autonomous Mode

**Request:**
```
"Build my Xcode project"
```

**What happens:**
1. Build fails with CocoaPods error
2. Automatically runs `pod install`
3. Retries build
4. Reports success

**No prompts, fully automatic!**

### Example 2: Preview Mode

**Request:**
```
"Build my Xcode project"
```

**What happens:**
1. Build fails with code signing error
2. Shows: "Action required: Check code signing settings"
3. Waits for your approval
4. After approval, retries build

**You review before execution!**

### Example 3: Preview Mode with Auto-Approve

**Request:**
```
"Build my Xcode project"
```

**What happens:**
1. Build fails with CocoaPods error
2. Detects `pod install` (auto-approve pattern)
3. Automatically runs `pod install` (no prompt)
4. Retries build
5. Reports success

**Safe actions auto-approved, others require approval!**

---

## 🔧 Switching Modes

### Switch to Preview Mode:
```json
{
  "automation": {
    "mode": "preview"
  }
}
```

### Switch to Autonomous Mode:
```json
{
  "automation": {
    "mode": "autonomous"
  }
}
```

**No restart needed!** Changes take effect on next build.

---

## 💡 Best Practices

1. **Start with Preview Mode** - Learn what automation does
2. **Use Autonomous for Trusted Projects** - Faster workflow
3. **Customize Auto-Approve Patterns** - Add your safe actions
4. **Use Per-Request Override** - Override mode for specific builds

---

## 🎉 Summary

- **Autonomous**: Fast, hands-off, fully automatic
- **Preview**: Safe, review before execution, auto-approve safe actions
- **Flexible**: Switch anytime, override per-request

**Choose the mode that fits your workflow!** 🚀

