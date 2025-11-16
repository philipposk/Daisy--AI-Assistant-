# 📖 User Manual - Intelligent Build Automation

## 🎯 What Is This?

Daisy's **Intelligent Build Automation** is an AI-powered system that:
- **Detects build errors** automatically
- **Fixes common errors** (pod install, npm install, etc.)
- **Retries builds** until they succeed
- **Works with Xcode, Android Studio, and Terminal**

**You just ask Cursor to build, and it handles everything!**

---

## 🚀 Quick Start

### Step 1: Make Sure Cursor is Restarted
- Quit Cursor (Cmd+Q)
- Reopen Cursor
- Wait for it to fully load

### Step 2: Just Ask!
Simply tell Cursor what you want:

```
"Build my Xcode project"
```

That's it! Cursor will:
1. Open Xcode
2. Build the project
3. Detect any errors
4. Fix them automatically
5. Retry until success

---

## 💬 What Can You Tell It?

### Basic Build Commands

#### Xcode Projects:
```
"Build my Xcode project"
"Build and run my iOS app"
"Fix the build errors in my Xcode project"
"Run my Xcode project with automatic error fixing"
```

#### Android Projects:
```
"Build my Android project"
"Build my Android Studio project"
"Fix Gradle errors in my Android project"
```

#### Terminal/General:
```
"Build this project"
"Run the build and fix any errors"
"Test the build with automatic fixes"
```

---

## 🎯 What It Understands

### Natural Language Commands

The system understands these types of requests:

#### 1. **Build Requests**
- "Build [project]"
- "Run [project]"
- "Test [project]"
- "Compile [project]"

#### 2. **Error Fixing Requests**
- "Fix build errors"
- "Fix the errors"
- "Resolve build issues"
- "Fix dependency errors"

#### 3. **Specific Actions**
- "Build with automatic error fixing"
- "Build and retry on errors"
- "Build with preview mode" (shows actions first)

#### 4. **IDE-Specific**
- "Xcode build"
- "Android build"
- "Gradle build"
- "CocoaPods install"

---

## 🔧 What It Can Do

### Automatic Error Detection

It detects these types of errors:

#### Xcode Errors:
- ✅ **CocoaPods missing** → Auto-runs `pod install`
- ✅ **Module import errors** → Detected and reported
- ✅ **Build failures** → Detected with details
- ✅ **Code signing errors** → Detected

#### Android Errors:
- ✅ **Gradle dependency errors** → Auto-runs `./gradlew build --refresh-dependencies`
- ✅ **Build failures** → Detected
- ✅ **SDK errors** → Detected

#### Terminal Errors:
- ✅ **npm package missing** → Auto-runs `npm install`
- ✅ **Python module missing** → Detected
- ✅ **General errors** → Detected

### Automatic Fixes

It automatically fixes:
- ✅ Missing CocoaPods → Runs `pod install`
- ✅ Missing npm packages → Runs `npm install`
- ✅ Missing Python modules → Detected (you fix manually)
- ✅ Gradle dependencies → Refreshes dependencies

### Retry Logic

- ✅ Tries up to 3 times (configurable)
- ✅ Applies fixes between retries
- ✅ Reports success or failure
- ✅ Shows what actions were taken

---

## 📝 Example Conversations

### Example 1: Simple Build

**You:**
```
"Build my Xcode project"
```

**Cursor does:**
1. Opens Xcode
2. Presses Cmd+B (build)
3. Waits for build
4. Checks for errors
5. If CocoaPods error → runs `pod install`
6. Retries build
7. Reports: "✅ Build succeeded!"

---

### Example 2: Build with Errors

**You:**
```
"Build my iOS app, it has CocoaPods errors"
```

**Cursor does:**
1. Opens Xcode
2. Builds project
3. Detects: "CocoaPods dependency missing"
4. Automatically runs: `pod install`
5. Waits for pod install to complete
6. Retries build
7. Reports: "✅ Build succeeded after fixing CocoaPods!"

---

### Example 3: Preview Mode

**You:**
```
"Build my project in preview mode"
```

**Cursor does:**
1. Opens Xcode
2. Builds project
3. Detects error
4. Shows: "Action required: pod install"
5. Waits for your approval
6. After approval → runs `pod install`
7. Retries build

---

## 🎛️ Advanced Usage

### Direct MCP Tool Calls

You can also use the tools directly:

#### Build with Retry:
```
Use build_with_retry with ide: "xcode", action: "build", projectPath: "/path/to/project"
```

#### Detect Errors:
```
Use capture_build_log with ide: "xcode", then detect_build_errors with the log text
```

#### Analyze Screenshot:
```
Use analyze_screenshot_with_vision with windowName: "Xcode" to find errors
```

---

## ⚙️ Configuration Options

### Preview Mode vs Autonomous Mode

**Autonomous Mode (Default):**
- Executes everything automatically
- No prompts
- Fast and hands-off

**Preview Mode:**
- Shows actions before executing
- Asks for approval
- Auto-approves safe actions (pod install, npm install)

**To switch modes:**
Edit `~/.daisy/preferences.json`:
```json
{
  "automation": {
    "mode": "preview"  // or "autonomous"
  }
}
```

### Max Retries

Default: 3 retries

To change:
```
Use build_with_retry with ide: "xcode", maxRetries: 5
```

---

## 🎯 Common Use Cases

### Use Case 1: Daily Development

**Scenario:** You're working on an iOS app

**What to say:**
```
"Build my Xcode project"
```

**What happens:**
- Builds automatically
- Fixes any CocoaPods issues
- Retries if needed
- You keep coding!

---

### Use Case 2: New Project Setup

**Scenario:** Just cloned a project with dependencies

**What to say:**
```
"Build this project and fix any dependency errors"
```

**What happens:**
- Detects missing dependencies
- Installs them automatically
- Builds successfully
- Ready to code!

---

### Use Case 3: Debugging Build Issues

**Scenario:** Build keeps failing, not sure why

**What to say:**
```
"Take a screenshot of Xcode and analyze it for errors"
```

**What happens:**
- Takes screenshot
- Uses Vision API to analyze
- Identifies error messages
- Suggests fixes

---

## 🐛 Troubleshooting

### "Cursor doesn't understand"

**Try:**
- Be more specific: "Build my Xcode project" instead of "build"
- Mention the IDE: "Xcode build" or "Android build"
- Use action words: "build", "run", "fix", "test"

### "Build not starting"

**Check:**
- Is Xcode/Android Studio installed?
- Is the project path correct?
- Are macOS Accessibility permissions granted?

### "Errors not being fixed"

**Check:**
- Is the error in the supported patterns? (CocoaPods, npm, etc.)
- Check the build log for the actual error
- Some errors require manual fixes

---

## 📚 Command Reference

### Build Commands
- `"Build [project]"` - Build project
- `"Run [project]"` - Build and run
- `"Test [project]"` - Build and test

### Error Commands
- `"Fix build errors"` - Detect and fix errors
- `"Fix [specific error]"` - Fix specific error type
- `"Resolve dependencies"` - Install missing dependencies

### Analysis Commands
- `"Analyze build errors"` - Check for errors
- `"Take screenshot and analyze"` - Use Vision API
- `"Check build status"` - Get current status

### Mode Commands
- `"Build in preview mode"` - Show actions first
- `"Build automatically"` - Full automation

---

## 💡 Pro Tips

1. **Be specific** - "Build my Xcode project" works better than "build"
2. **Mention the IDE** - "Xcode build" or "Android build"
3. **Use preview mode** - If you want to see what it's doing
4. **Check the logs** - Cursor shows what actions it took
5. **Trust autonomous mode** - For trusted projects, let it run

---

## 🎓 Learning Examples

### Start Simple:
```
"Build my Xcode project"
```

### Add Specificity:
```
"Build my iOS app and fix any CocoaPods errors"
```

### Use Preview:
```
"Build my project in preview mode so I can see what it does"
```

### Direct Control:
```
Use build_with_retry with ide: "xcode", action: "build", projectPath: "/Users/me/MyApp"
```

---

## ✅ Quick Reference Card

**Basic Usage:**
```
"Build my [IDE] project"
```

**With Error Fixing:**
```
"Build my [IDE] project with automatic error fixing"
```

**Preview Mode:**
```
"Build my [IDE] project in preview mode"
```

**Analyze Errors:**
```
"Take a screenshot of [IDE] and analyze it for errors"
```

---

## 🎉 That's It!

**Just talk to Cursor naturally!** It understands:
- Build requests
- Error fixing requests
- IDE-specific commands
- Natural language

**Start with:** `"Build my Xcode project"` and see what happens! 🚀



