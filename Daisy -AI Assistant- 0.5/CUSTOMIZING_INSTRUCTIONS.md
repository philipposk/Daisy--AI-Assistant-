# 🎨 Customizing Instructions - Adding Your Own Rules

## ✅ Yes! You Can Customize It!

You can add custom instructions and rules in several ways:

---

## 🎯 What You Can Customize

### 1. **Auto-Approve Patterns** ✅ (Easy)
Add patterns for actions that should auto-approve in preview mode.

### 2. **Error Patterns** ⚠️ (Requires Code)
Add new error detection patterns (requires editing server.js).

### 3. **Build Commands** ✅ (Easy)
Add custom build commands via preferences.

### 4. **Automation Rules** ✅ (Easy)
Add rules for when to auto-execute vs ask.

---

## 📝 Method 1: Edit Preferences File (Easiest)

### Location
`~/.daisy/preferences.json`

### What You Can Add

#### Auto-Approve Patterns
```json
{
  "automation": {
    "mode": "autonomous",
    "auto_approve_patterns": [
      "pod install",
      "npm install",
      "pip install",
      "./gradlew build --refresh-dependencies",
      "your custom command here"  // ← Add your own!
    ]
  }
}
```

#### Custom Rules
```json
{
  "rules": [
    {
      "pattern": ".*your custom pattern.*",
      "action": "yes",
      "description": "Your custom rule"
    }
  ]
}
```

---

## 💬 Method 2: Ask Cursor to Add Instructions

### You Can Say:

```
"Add 'flutter pub get' to the auto-approve patterns"
```

**Cursor can:**
1. Read your preferences file
2. Add the pattern
3. Save it back

**Example:**
```
You: "Add 'yarn install' to auto-approve patterns"
Cursor: [Edits preferences.json, adds pattern]
You: "Now build my project"
Cursor: [Uses new pattern]
```

---

## 🔧 Method 3: Add Custom Error Patterns (Advanced)

### Current Error Patterns Location
`mcp-desktop-automation/server.js` (lines ~809-850)

### You Can Ask Cursor:

```
"Add a new error pattern for Flutter errors that suggests 'flutter pub get'"
```

**Cursor can:**
1. Read server.js
2. Add new pattern to errorPatterns
3. Save the file
4. You restart Cursor to load changes

**Example Pattern:**
```javascript
{
  pattern: /flutter.*not found|pub.*error/i,
  type: "missing_dependency",
  fix: "flutter pub get",
  message: "Flutter dependency missing",
}
```

---

## 📋 What Instructions You Can Add

### 1. **Custom Build Commands**

**Add to preferences:**
```json
{
  "custom_build_commands": {
    "flutter": "flutter build",
    "rust": "cargo build",
    "go": "go build"
  }
}
```

### 2. **Custom Error Fixes**

**Ask Cursor:**
```
"When you see 'ModuleNotFoundError: pandas', automatically run 'pip install pandas'"
```

Cursor can add this as a rule or pattern.

### 3. **Project-Specific Rules**

**Ask Cursor:**
```
"For this project, always run 'npm run setup' before building"
```

Cursor can remember this for the current project.

---

## 🎯 Practical Examples

### Example 1: Add Flutter Support

**You say:**
```
"Add Flutter error detection: when you see 'pub get' errors, run 'flutter pub get'"
```

**Cursor can:**
1. Add Flutter pattern to errorPatterns
2. Add 'flutter pub get' to auto-approve
3. Update server.js
4. Tell you to restart Cursor

---

### Example 2: Custom Auto-Approve

**You say:**
```
"Always auto-approve 'bundle install' commands"
```

**Cursor can:**
1. Edit preferences.json
2. Add "bundle install" to auto_approve_patterns
3. Save file
4. Works immediately (no restart needed)

---

### Example 3: Project-Specific Instruction

**You say:**
```
"For this React Native project, always run 'cd ios && pod install' before building iOS"
```

**Cursor can:**
1. Remember this for current project
2. Add to project-specific rules
3. Apply automatically when building this project

---

## 🛠️ How Cursor Can Help

### Cursor Can:

✅ **Read files** - Read preferences.json, server.js  
✅ **Edit files** - Add patterns, update configs  
✅ **Understand context** - Know what you're working on  
✅ **Apply changes** - Make modifications automatically  

### Just Ask:

```
"Add [instruction] to the build automation"
"Make it so that [action] happens when [condition]"
"Customize the error detection for [framework]"
```

---

## 📝 Step-by-Step: Adding Custom Instructions

### Step 1: Tell Cursor What You Want

```
"I want to add custom error detection for Rust projects"
```

### Step 2: Cursor Asks for Details

```
Cursor: "What error pattern should I look for?"
You: "When you see 'cannot find crate', run 'cargo build'"
```

### Step 3: Cursor Adds It

Cursor:
1. Reads server.js
2. Adds Rust pattern
3. Updates errorPatterns
4. Saves file

### Step 4: You Restart Cursor

```
Cursor: "I've added the pattern. Please restart Cursor to load it."
You: [Restart Cursor]
```

### Step 5: It Works!

Now when you build Rust projects, it detects the error and fixes it automatically.

---

## 🎨 What's Customizable

### ✅ Easy to Customize (Preferences)
- Auto-approve patterns
- Automation mode (preview/autonomous)
- Custom rules
- Build commands

### ⚠️ Requires Code Changes
- Error detection patterns
- New MCP tools
- Complex logic

### 💡 Cursor Can Help With Both!

**For preferences:** Cursor can edit directly  
**For code:** Cursor can modify server.js and tell you to restart

---

## 🔄 Dynamic Customization

### Real-Time Changes (No Restart)
- Auto-approve patterns (via preferences)
- Automation mode (via preferences)
- Custom rules (via preferences)

### Requires Restart
- Error detection patterns (code changes)
- New MCP tools (code changes)
- Complex logic (code changes)

---

## 💬 Example Conversations

### Conversation 1: Add Auto-Approve

**You:**
```
"Add 'yarn install' to the auto-approve patterns"
```

**Cursor:**
```
[Reads preferences.json]
[Adds "yarn install" to auto_approve_patterns]
[Saves file]
"Done! 'yarn install' will now auto-approve in preview mode."
```

**Works immediately!** ✅

---

### Conversation 2: Add Error Pattern

**You:**
```
"Add error detection for Python: when you see 'ModuleNotFoundError', suggest 'pip install [module]'"
```

**Cursor:**
```
[Reads server.js]
[Adds Python error pattern]
[Saves file]
"I've added Python error detection. Please restart Cursor to load the changes."
```

**Requires restart** ⚠️

---

## 🎯 Best Practices

### 1. **Start with Preferences**
- Easiest to customize
- No restart needed
- Works immediately

### 2. **Ask Cursor to Help**
- "Add [X] to auto-approve"
- "Customize error detection for [Y]"
- "Make it so [Z] happens"

### 3. **Test After Changes**
- Try a build
- See if it works
- Adjust if needed

---

## ✅ Summary

**Yes, you can add instructions from any Cursor chat!**

✅ **Easy:** Auto-approve patterns, rules (via preferences)  
✅ **Medium:** Error patterns (Cursor can edit code)  
✅ **Advanced:** New tools (requires more work)  

**Just ask Cursor:**
```
"Add [your instruction] to the build automation"
```

**Cursor will help you customize it!** 🎨



