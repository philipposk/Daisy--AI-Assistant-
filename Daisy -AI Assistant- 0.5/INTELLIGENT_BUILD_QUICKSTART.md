# 🚀 Intelligent Build Automation - Quick Start

## ✅ What's Been Added

Daisy now has **intelligent build automation** that matches ChatGPT's proposed system! Here's what's new:

### New MCP Tools

1. **`capture_build_log`** - Captures build output from Xcode/Android Studio/Terminal
2. **`analyze_screenshot_with_vision`** - Uses GPT-4 Vision to analyze screenshots for errors
3. **`detect_build_errors`** - Analyzes logs and detects common errors with suggested fixes
4. **`build_with_retry`** - Executes builds with automatic error detection and retry loop

### Features

✅ **Error Detection** - Automatically detects build errors from logs  
✅ **Automatic Fixes** - Fixes common errors (pod install, npm install, etc.)  
✅ **Retry Loop** - Loops until build succeeds or max retries reached  
✅ **Vision Analysis** - Uses GPT-4 Vision to read error dialogs  
✅ **Smart Error Patterns** - Recognizes Xcode, Android, and terminal errors  

---

## 🎯 How to Use

### Option 1: Use in Cursor (Recommended)

Just ask Cursor to build your project:

```
"Build my Xcode project with automatic error fixing"
```

Cursor will automatically:
1. Use `build_with_retry` MCP tool
2. Detect errors
3. Apply fixes (pod install, etc.)
4. Retry until success

### Option 2: Direct MCP Tool Calls

In Cursor, you can also use the tools directly:

**Simple build with retry:**
```
Use build_with_retry with ide: "xcode", action: "build", projectPath: "/path/to/project"
```

**Detect errors:**
```
Use capture_build_log with ide: "xcode", then detect_build_errors with the log text
```

**Analyze screenshot:**
```
Use analyze_screenshot_with_vision with windowName: "Xcode" to find errors
```

---

## ⚙️ Setup

### 1. Install OpenAI Package (Optional, for Vision API)

```bash
cd mcp-desktop-automation
npm install openai
```

### 2. Set OpenAI API Key (Optional, for Vision API)

```bash
export OPENAI_API_KEY="your-api-key-here"
```

**Note**: Vision API is optional. Error detection works without it using log parsing.

### 3. Restart MCP Server

If MCP server is running, restart it to load new tools:

```bash
# The MCP server will automatically reload when Cursor restarts
# Or restart Cursor to pick up new MCP tools
```

---

## 📋 Error Patterns Detected

### Xcode Errors
- ✅ CocoaPods missing → Auto-runs `pod install`
- ✅ Module import errors → Detected and reported
- ✅ Build failures → Detected with details
- ✅ Code signing errors → Detected

### Android Errors
- ✅ Gradle dependency errors → Auto-runs `./gradlew build --refresh-dependencies`
- ✅ Build failures → Detected
- ✅ SDK errors → Detected

### Terminal Errors
- ✅ npm package missing → Auto-runs `npm install`
- ✅ Python module missing → Detected
- ✅ General errors → Detected

---

## 🔄 How It Works

### Build with Retry Flow

```
1. Execute build (Xcode/Android/Terminal)
   ↓
2. Wait for build to complete
   ↓
3. Capture build log
   ↓
4. Detect errors using pattern matching
   ↓
5. If errors found:
   - Apply suggested fix (pod install, npm install, etc.)
   - Retry build
   - Loop back to step 2
   ↓
6. If success → Report success
   If max retries → Report failure with details
```

### Example: Xcode Build with CocoaPods Error

```
Attempt 1: Build fails
  → Error detected: "CocoaPods dependency missing"
  → Auto-fix: Running "pod install"
  → Waiting for pod install to complete

Attempt 2: Build succeeds!
  → ✅ Success reported
```

---

## 💰 Cost Estimate

### Without Vision API (Log Parsing Only)
- **Cost**: €0/month (completely free!)
- **Works for**: Most build errors detectable in logs

### With Vision API (GPT-4 Vision)
- **Cost**: ~€5-20/month (light use: 10-50 builds/day)
- **Works for**: Error dialogs, UI-based errors, complex error messages

**Recommendation**: Start with log parsing (free), add vision API if needed.

---

## 🧪 Testing

### Test Error Detection

1. Create a test Xcode project with missing CocoaPods
2. Ask Cursor: "Build this Xcode project"
3. Watch Daisy:
   - Detect CocoaPods error
   - Run `pod install` automatically
   - Retry build
   - Report success

### Test Vision API

1. Open Xcode with a build error dialog visible
2. Ask Cursor: "Analyze the Xcode window for errors"
3. Cursor will use `analyze_screenshot_with_vision` to read the error

---

## 🎛️ Configuration

### Max Retries

Default: 3 retries. Can be configured in `build_with_retry`:

```javascript
{
  ide: "xcode",
  action: "build",
  maxRetries: 5,  // Custom retry count
  projectPath: "/path/to/project"
}
```

### Error Patterns

Error patterns are defined in `detect_build_errors`. You can extend them by editing `mcp-desktop-automation/server.js`.

---

## 🐛 Troubleshooting

### "OpenAI API key not set"
- **Solution**: Set `OPENAI_API_KEY` environment variable (optional - only needed for vision API)

### "Could not capture Xcode console"
- **Solution**: Make sure Xcode is open and build has run. The console must be visible.

### "Build failed after max retries"
- **Solution**: Check the error details in the response. Some errors require manual fixes.

### MCP tools not appearing in Cursor
- **Solution**: Restart Cursor to reload MCP server configuration

---

## 📚 Next Steps

1. ✅ **Test with your projects** - Try building an Xcode/Android project
2. ✅ **Add custom error patterns** - Edit error patterns in `server.js`
3. ✅ **Enable preview mode** - Coming soon (see `INTELLIGENT_BUILD_AUTOMATION.md`)
4. ✅ **Extend to more IDEs** - Add VS Code, IntelliJ support

---

## 🎉 Result

You now have **exactly what ChatGPT proposed**:
- ✅ Automation backend (MCP server)
- ✅ Error detection (log parsing + vision)
- ✅ Automatic corrective actions
- ✅ Retry loop until success
- ✅ AI reasoning (Cursor integration)

**Daisy can now read errors, fix them, and loop until your build succeeds!** 🚀

