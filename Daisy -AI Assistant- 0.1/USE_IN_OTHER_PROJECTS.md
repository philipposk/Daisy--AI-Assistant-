# 📁 How to Use Daisy in Other Cursor Projects

Daisy is already configured **globally** for Cursor! Here's how to use it in any project:

## ✅ Daisy is Already Global

**Good news:** Daisy's MCP server is configured **globally** in `~/.cursor/mcp.json`, so it's available in **ALL Cursor projects** automatically!

## 🚀 Quick Setup for New Projects

### Option 1: Copy `.cursorrules` (Recommended)

To get automatic execution rules in a new project:

**Step 1:** Copy the `.cursorrules` file to your new project:
```bash
cp "/Users/phktistakis/Daisy -AI Assistant- 0.1/.cursorrules" /path/to/your/new/project/.cursorrules
```

**Step 2:** Done! Cursor will automatically read `.cursorrules` in that project.

### Option 2: Global `.cursorrules` (All Projects)

To make `.cursorrules` work for ALL projects:

**Create a global rules file:**
```bash
cp "/Users/phktistakis/Daisy -AI Assistant- 0.1/.cursorrules" ~/.cursorrules
```

Cursor will check both:
1. `~/.cursorrules` (global - for all projects)
2. `./.cursorrules` (project-specific - overrides global)

## 🔧 What's Already Working

### MCP Server (Global)
✅ **Already configured** in `~/.cursor/mcp.json`
- Works in **ALL Cursor projects** automatically
- Cursor can use Daisy's tools in any project

### Agent Controller (Global)
✅ **Already running** (if you started it)
- Runs in the background
- Monitors for questions from any project
- Works globally, not project-specific

### What You Need to Add

**Only `.cursorrules` needs to be in each project:**
- This tells Cursor to use MCP tools automatically
- Without it, Cursor might still ask you to run things manually

## 📋 Step-by-Step for New Project

### Method 1: Quick Copy (Per Project)

```bash
# Navigate to your new project
cd /path/to/your/new/project

# Copy .cursorrules
cp "/Users/phktistakis/Daisy -AI Assistant- 0.1/.cursorrules" .

# Done! Daisy is now available in this project
```

### Method 2: Global Setup (All Projects)

```bash
# Copy to home directory (global)
cp "/Users/phktistakis/Daisy -AI Assistant- 0.1/.cursorrules" ~/.cursorrules

# Done! Daisy works in ALL projects now
```

### Method 3: Symbolic Link (Sync Updates)

```bash
# In your new project
cd /path/to/your/new/project

# Create symlink (always up-to-date)
ln -s "/Users/phktistakis/Daisy -AI Assistant- 0.1/.cursorrules" .cursorrules

# Done! Changes to Daisy's .cursorrules will sync automatically
```

## ✅ Verify It's Working

In your new project, ask Cursor:
- "Take a screenshot" (should work automatically)
- "Open Xcode and run" (should work automatically)

If it works, Daisy is active!

## 🔍 What Works Globally vs Per-Project

### Global (Works Everywhere)
- ✅ MCP Server configuration (`~/.cursor/mcp.json`)
- ✅ Agent Controller (if running in background)
- ✅ Daisy automation tools

### Per-Project (Needs Setup)
- ⚠️ `.cursorrules` file (tells Cursor to use automation)
- ⚠️ Project-specific automation rules (if customized)

## 🎯 Best Practice

**Recommended Setup:**

1. **Global `.cursorrules`** (one file for all projects):
   ```bash
   cp "/Users/phktistakis/Daisy -AI Assistant- 0.1/.cursorrules" ~/.cursorrules
   ```

2. **Keep Daisy running** (one agent for all projects):
   ```bash
   # Already running in background, or:
   cd "/Users/phktistakis/Daisy -AI Assistant- 0.1"
   nohup ./start-agent.sh > ~/.daisy/logs/agent.log 2>&1 &
   ```

3. **Done!** Daisy works in all Cursor projects automatically!

## 🔄 Updating Daisy

If you update Daisy's `.cursorrules`, you can:

**If using global:**
- Update `~/.cursorrules` directly
- Changes apply to all projects

**If using per-project:**
- Update each project's `.cursorrules` individually
- Or use symlink (see Method 3 above)

## 📝 Project-Specific Customization

You can also create project-specific rules:

**In your project, create `.cursorrules`:**
```markdown
# Project-specific rules
# Daisy's global rules are also active

## This Project Specific
When working on this project:
- Always use Python 3.11
- Use specific build commands
```

**Project-specific rules override global rules.**

## 🆘 Troubleshooting

**Daisy not working in new project?**

1. **Check MCP is configured:**
   ```bash
   cat ~/.cursor/mcp.json
   ```
   Should show `desktop-automation` server.

2. **Check `.cursorrules` exists:**
   ```bash
   cat ~/.cursorrules  # or ./cursorrules in project
   ```

3. **Check agent is running:**
   ```bash
   ps aux | grep simple-controller
   ```

4. **Restart Cursor** after adding `.cursorrules`

**Still not working?**
- Make sure Cursor has MCP enabled
- Check Cursor Settings → Features → Model Context Protocol
- Restart Cursor

## ✨ Summary

**To use Daisy in other projects:**

1. ✅ MCP Server: **Already global** (no setup needed)
2. ✅ Agent Controller: **Already running** (works globally)
3. ⚠️ `.cursorrules`: **Copy to project or make global**

**Easiest way:**
```bash
cp "/Users/phktistakis/Daisy -AI Assistant- 0.1/.cursorrules" ~/.cursorrules
```

**Then Daisy works in ALL Cursor projects!** 🎉

