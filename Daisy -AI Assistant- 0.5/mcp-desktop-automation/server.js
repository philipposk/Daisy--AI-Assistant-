#!/usr/bin/env node

/**
 * MCP Server for Desktop Automation
 * Provides tools for Cursor to control your desktop: screenshots, mouse, keyboard, app control
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { spawn, exec } from "child_process";
import { promisify } from "util";
import * as fs from "fs/promises";
import * as path from "path";

const execAsync = promisify(exec);

// Optional OpenAI client for vision API (if OPENAI_API_KEY is set)
let openaiClient = null;
let openaiInitialized = false;

async function initializeOpenAI() {
  if (openaiInitialized) return;
  openaiInitialized = true;
  try {
    const { OpenAI } = await import("openai");
    
    // Try environment variable first, then Daisy config file
    let apiKey = process.env.OPENAI_API_KEY;
    
    if (!apiKey) {
      // Try to read from Daisy config file
      try {
        const configPath = path.join(process.env.HOME, ".daisy", "config.json");
        const configContent = await fs.readFile(configPath, "utf-8");
        const config = JSON.parse(configContent);
        apiKey = config.openai_api_key || config.OPENAI_API_KEY;
      } catch (e) {
        // Config file not found or invalid - that's okay
      }
    }
    
    if (apiKey) {
      openaiClient = new OpenAI({ apiKey });
      console.error("✅ OpenAI client initialized for vision API");
    } else {
      console.error("⚠️  OpenAI API key not found. Set OPENAI_API_KEY or add to ~/.daisy/config.json");
    }
  } catch (e) {
    console.error("⚠️  OpenAI not available (optional for vision API):", e.message);
  }
}

class DesktopAutomationServer {
  constructor() {
    this.server = new Server(
      {
        name: "desktop-automation",
        version: "0.1.0",
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    this.setupToolHandlers();
    this.setupErrorHandling();
  }

  setupToolHandlers() {
    this.server.setRequestHandler(ListToolsRequestSchema, async () => ({
      tools: [
        {
          name: "take_screenshot",
          description:
            "Takes a screenshot of the entire screen or a specific window. Returns the path to the screenshot file.",
          inputSchema: {
            type: "object",
            properties: {
              windowName: {
                type: "string",
                description:
                  "Optional: Name of the window to screenshot (e.g., 'Xcode', 'Cursor'). If not provided, screenshots entire screen.",
              },
              outputPath: {
                type: "string",
                description:
                  "Optional: Path to save the screenshot. Defaults to ~/Desktop/screenshot_YYYYMMDD_HHMMSS.png",
              },
            },
          },
        },
        {
          name: "click_mouse",
          description:
            "Clicks the mouse at a specific screen coordinate or finds and clicks UI elements by text/description.",
          inputSchema: {
            type: "object",
            properties: {
              x: {
                type: "number",
                description: "X coordinate (only if clicking by position)",
              },
              y: {
                type: "number",
                description: "Y coordinate (only if clicking by position)",
              },
              elementText: {
                type: "string",
                description:
                  "Text or description of UI element to click (uses macOS accessibility APIs)",
              },
              button: {
                type: "string",
                enum: ["left", "right", "middle"],
                default: "left",
                description: "Mouse button to click",
              },
            },
          },
        },
        {
          name: "type_text",
          description: "Types text at the current cursor position or into a focused field.",
          inputSchema: {
            type: "object",
            properties: {
              text: {
                type: "string",
                description: "Text to type",
              },
              delay: {
                type: "number",
                description: "Delay between keystrokes in milliseconds (default: 50)",
              },
            },
            required: ["text"],
          },
        },
        {
          name: "key_press",
          description: "Presses a key combination (e.g., Cmd+R, Enter, Escape).",
          inputSchema: {
            type: "object",
            properties: {
              keys: {
                type: "array",
                items: { type: "string" },
                description:
                  "Array of keys to press simultaneously (e.g., ['cmd', 'r'] for Cmd+R)",
              },
            },
            required: ["keys"],
          },
        },
        {
          name: "open_application",
          description:
            "Opens an application by name (e.g., 'Xcode', 'Android Studio', 'Safari').",
          inputSchema: {
            type: "object",
            properties: {
              appName: {
                type: "string",
                description: "Name of the application to open",
              },
            },
            required: ["appName"],
          },
        },
        {
          name: "get_active_window",
          description: "Gets information about the currently active window.",
          inputSchema: {
            type: "object",
            properties: {},
          },
        },
        {
          name: "find_ui_element",
          description:
            "Finds UI elements by text, label, or accessibility identifier. Returns position and details.",
          inputSchema: {
            type: "object",
            properties: {
              text: {
                type: "string",
                description: "Text to search for in UI elements",
              },
              elementType: {
                type: "string",
                description:
                  "Type of element (button, menu, text field, etc.)",
              },
            },
          },
        },
        {
          name: "wait_for_element",
          description: "Waits for a UI element to appear on screen (useful for loading states).",
          inputSchema: {
            type: "object",
            properties: {
              text: {
                type: "string",
                description: "Text of the element to wait for",
              },
              timeout: {
                type: "number",
                description: "Timeout in seconds (default: 30)",
                default: 30,
              },
            },
          },
        },
        {
          name: "run_terminal_command",
          description:
            "Runs a terminal command and returns the output. Use for running builds, tests, etc.",
          inputSchema: {
            type: "object",
            properties: {
              command: {
                type: "string",
                description: "Terminal command to execute",
              },
              workingDirectory: {
                type: "string",
                description: "Working directory for the command",
              },
            },
            required: ["command"],
          },
        },
        {
          name: "capture_build_log",
          description:
            "Captures build output from Xcode or Android Studio. Returns logs and detects errors.",
          inputSchema: {
            type: "object",
            properties: {
              ide: {
                type: "string",
                enum: ["xcode", "android", "terminal"],
                description: "Which IDE to capture logs from",
              },
              timeout: {
                type: "number",
                description: "Timeout in seconds to wait for build (default: 60)",
                default: 60,
              },
            },
            required: ["ide"],
          },
        },
        {
          name: "analyze_screenshot_with_vision",
          description:
            "Analyzes a screenshot using GPT-4 Vision to detect errors, buttons, and UI elements. Requires OPENAI_API_KEY.",
          inputSchema: {
            type: "object",
            properties: {
              screenshotPath: {
                type: "string",
                description: "Path to screenshot file to analyze",
              },
              windowName: {
                type: "string",
                description: "Optional: Take new screenshot of specific window (e.g., 'Xcode')",
              },
              prompt: {
                type: "string",
                description: "What to look for in the screenshot (e.g., 'Find any error messages or build failures')",
                default: "Analyze this screenshot and identify any error messages, build failures, or issues that need attention.",
              },
            },
          },
        },
        {
          name: "detect_build_errors",
          description:
            "Analyzes build logs and detects common errors. Returns error type and suggested fixes.",
          inputSchema: {
            type: "object",
            properties: {
              logText: {
                type: "string",
                description: "Build log text to analyze",
              },
              ide: {
                type: "string",
                enum: ["xcode", "android", "terminal"],
                description: "Type of IDE/build system",
              },
            },
            required: ["logText", "ide"],
          },
        },
        {
          name: "build_with_retry",
          description:
            "Executes a build with automatic error detection and retry logic. Loops until success or max retries. Supports preview mode.",
          inputSchema: {
            type: "object",
            properties: {
              ide: {
                type: "string",
                enum: ["xcode", "android", "terminal"],
                description: "Which IDE to build in",
              },
              action: {
                type: "string",
                enum: ["build", "run", "test"],
                description: "Build action to perform",
                default: "build",
              },
              maxRetries: {
                type: "number",
                description: "Maximum number of retry attempts (default: 3)",
                default: 3,
              },
              projectPath: {
                type: "string",
                description: "Optional: Path to project directory for dependency fixes",
              },
              previewMode: {
                type: "boolean",
                description: "If true, show actions before executing (preview mode). If false or not set, uses preferences.",
                default: false,
              },
            },
            required: ["ide"],
          },
        },
      ],
    }));

    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;

      try {
        switch (name) {
          case "take_screenshot":
            return await this.takeScreenshot(args);
          case "click_mouse":
            return await this.clickMouse(args);
          case "type_text":
            return await this.typeText(args);
          case "key_press":
            return await this.keyPress(args);
          case "open_application":
            return await this.openApplication(args);
          case "get_active_window":
            return await this.getActiveWindow();
          case "find_ui_element":
            return await this.findUIElement(args);
          case "wait_for_element":
            return await this.waitForElement(args);
          case "run_terminal_command":
            return await this.runTerminalCommand(args);
          case "capture_build_log":
            return await this.captureBuildLog(args);
          case "analyze_screenshot_with_vision":
            return await this.analyzeScreenshotWithVision(args);
          case "detect_build_errors":
            return await this.detectBuildErrors(args);
          case "build_with_retry":
            return await this.buildWithRetry(args);
          default:
            throw new Error(`Unknown tool: ${name}`);
        }
      } catch (error) {
        return {
          content: [
            {
              type: "text",
              text: `Error: ${error.message}`,
            },
          ],
          isError: true,
        };
      }
    });
  }

  async takeScreenshot(args) {
    const timestamp = new Date()
      .toISOString()
      .replace(/:/g, "-")
      .split(".")[0];
    const defaultPath = path.join(
      process.env.HOME,
      "Desktop",
      `screenshot_${timestamp}.png`
    );
    const outputPath = args.outputPath || defaultPath;

    let command;
    if (args.windowName) {
      // Screenshot specific window using screencapture
      command = `screencapture -l$(osascript -e 'tell application "System Events" to get id of first window whose name contains "${args.windowName}"') "${outputPath}"`;
    } else {
      command = `screencapture "${outputPath}"`;
    }

    await execAsync(command);
    return {
      content: [
        {
          type: "text",
          text: `Screenshot saved to: ${outputPath}`,
        },
      ],
    };
  }

  async clickMouse(args) {
    if (args.elementText) {
      // Use AppleScript to find and click element by accessibility
      const script = `
        tell application "System Events"
          set frontApp to first application process whose frontmost is true
          tell frontApp
            try
              set targetButton to first button whose name contains "${args.elementText}" or value contains "${args.elementText}" or description contains "${args.elementText}"
              click targetButton
              return "Clicked element: ${args.elementText}"
            on error
              return "Could not find element: ${args.elementText}"
            end try
          end tell
        end tell
      `;
      const result = await execAsync(`osascript -e '${script}'`);
      return {
        content: [
          {
            type: "text",
            text: result.stdout.trim(),
          },
        ],
      };
    } else if (args.x !== undefined && args.y !== undefined) {
      // Click at specific coordinates using AppleScript
      const button = args.button || "left";
      const script = `
        tell application "System Events"
          click at {${args.x}, ${args.y}}
        end tell
      `;
      await execAsync(`osascript -e '${script}'`);
      return {
        content: [
          {
            type: "text",
            text: `Clicked at (${args.x}, ${args.y})`,
          },
        ],
      };
    } else {
      throw new Error("Must provide either (x, y) coordinates or elementText");
    }
  }

  async typeText(args) {
    const delay = args.delay || 50;
    const script = `
      tell application "System Events"
        keystroke "${args.text}"
      end tell
    `;
    await execAsync(`osascript -e '${script}'`);
    return {
      content: [
        {
          type: "text",
          text: `Typed: ${args.text}`,
        },
      ],
    };
  }

  async keyPress(args) {
    const keys = args.keys || [];
    const keyMap = {
      cmd: "command down",
      ctrl: "control down",
      alt: "option down",
      shift: "shift down",
      enter: "return",
      escape: "escape",
      tab: "tab",
      space: "space",
      delete: "delete",
      backspace: "delete",
    };

    const modifiers = [];
    const modifierKeys = ['cmd', 'ctrl', 'alt', 'shift'];
    const mainKey = keys
      .map((k) => {
        const lower = k.toLowerCase();
        if (modifierKeys.includes(lower)) {
          modifiers.push(keyMap[lower] || lower);
          return null;
        }
        return keyMap[lower] || k;
      })
      .filter(Boolean)[0];

    const modString = modifiers.length ? ` using {${modifiers.join(", ")}}` : "";

    const script = `
      tell application "System Events"
        keystroke "${mainKey}"${modString}
      end tell
    `;

    await execAsync(`osascript -e '${script}'`);
    return {
      content: [
        {
          type: "text",
          text: `Pressed keys: ${keys.join("+")}`,
        },
      ],
    };
  }

  async openApplication(args) {
    const script = `
      tell application "${args.appName}"
        activate
      end tell
    `;
    await execAsync(`osascript -e '${script}'`);
    return {
      content: [
        {
          type: "text",
          text: `Opened application: ${args.appName}`,
        },
      ],
    };
  }

  async getActiveWindow() {
    const script = `
      tell application "System Events"
        set frontApp to first application process whose frontmost is true
        tell frontApp
          set windowName to name of first window
        end tell
        return name of frontApp & " - " & windowName
      end tell
    `;
    const result = await execAsync(`osascript -e '${script}'`);
    return {
      content: [
        {
          type: "text",
          text: `Active window: ${result.stdout.trim()}`,
        },
      ],
    };
  }

  async findUIElement(args) {
    const script = `
      tell application "System Events"
        set frontApp to first application process whose frontmost is true
        tell frontApp
          try
            set targetElement to first UI element whose name contains "${args.text}" or value contains "${args.text}"
            set elementPosition to position of targetElement
            set elementSize to size of targetElement
            return "Found element: ${args.text} at " & (item 1 of elementPosition) & "," & (item 2 of elementPosition) & " size: " & (item 1 of elementSize) & "x" & (item 2 of elementSize)
          on error
            return "Element not found: ${args.text}"
          end try
        end tell
      end tell
    `;
    const result = await execAsync(`osascript -e '${script}'`);
    return {
      content: [
        {
          type: "text",
          text: result.stdout.trim(),
        },
      ],
    };
  }

  async waitForElement(args) {
    const timeout = (args.timeout || 30) * 1000;
    const startTime = Date.now();
    const interval = 500;

    while (Date.now() - startTime < timeout) {
      try {
        const result = await this.findUIElement({ text: args.text });
        if (!result.content[0].text.includes("not found")) {
          return {
            content: [
              {
                type: "text",
                text: `Element "${args.text}" appeared after ${(Date.now() - startTime) / 1000}s`,
              },
            ],
          };
        }
      } catch (e) {
        // Continue waiting
      }
      await new Promise((resolve) => setTimeout(resolve, interval));
    }

    return {
      content: [
        {
          type: "text",
          text: `Timeout: Element "${args.text}" did not appear within ${timeout / 1000}s`,
        },
      ],
      isError: true,
    };
  }

  async runTerminalCommand(args) {
    const options = args.workingDirectory
      ? { cwd: args.workingDirectory }
      : {};
    const result = await execAsync(args.command, options);
    return {
      content: [
        {
          type: "text",
          text: `Command: ${args.command}\nOutput:\n${result.stdout}\n${result.stderr}`,
        },
      ],
    };
  }

  async captureBuildLog(args) {
    const { ide, timeout = 60 } = args;
    let logText = "";

    try {
      if (ide === "xcode") {
        // Get Xcode console output using AppleScript
        const script = `
          tell application "Xcode"
            activate
          end tell
          tell application "System Events"
            tell process "Xcode"
              try
                -- Try to get text from console area
                set consoleText to value of text area 1 of scroll area 1 of group 1 of window 1
                return consoleText
              on error
                return "Could not capture Xcode console. Make sure Xcode is open and build has run."
              end try
            end tell
          end tell
        `;
        const result = await execAsync(`osascript -e '${script}'`);
        logText = result.stdout || result.stderr || "";
      } else if (ide === "android") {
        // For Android Studio, we'd need to capture Gradle output
        // This is a simplified version - in practice, you'd read from Gradle log files
        logText = "Android Studio log capture - check ~/.gradle/daemon/ for build logs";
      } else if (ide === "terminal") {
        // Terminal output is captured via run_terminal_command
        logText = "Use run_terminal_command to capture terminal output";
      }

      return {
        content: [
          {
            type: "text",
            text: `Build log captured:\n${logText || "No log text captured"}`,
          },
        ],
      };
    } catch (error) {
      return {
        content: [
          {
            type: "text",
            text: `Error capturing build log: ${error.message}`,
          },
        ],
        isError: true,
      };
    }
  }

  async analyzeScreenshotWithVision(args) {
    await initializeOpenAI();
    if (!openaiClient) {
      return {
        content: [
          {
            type: "text",
            text: "Error: OpenAI API key not set. Set OPENAI_API_KEY environment variable to use vision analysis.",
          },
        ],
        isError: true,
      };
    }

    try {
      let screenshotPath = args.screenshotPath;

      // If windowName is provided, take a new screenshot
      if (args.windowName && !screenshotPath) {
        const timestamp = new Date()
          .toISOString()
          .replace(/:/g, "-")
          .split(".")[0];
        screenshotPath = path.join(
          process.env.HOME,
          "Desktop",
          `screenshot_${timestamp}.png`
        );
        await this.takeScreenshot({
          windowName: args.windowName,
          outputPath: screenshotPath,
        });
      }

      if (!screenshotPath || !(await fs.access(screenshotPath).then(() => true).catch(() => false))) {
        return {
          content: [
            {
              type: "text",
              text: `Error: Screenshot file not found: ${screenshotPath}`,
            },
          ],
          isError: true,
        };
      }

      // Read image file
      const imageBuffer = await fs.readFile(screenshotPath);
      const base64Image = imageBuffer.toString("base64");

      // Call GPT-4 Vision API
      const prompt = args.prompt || "Analyze this screenshot and identify any error messages, build failures, or issues that need attention.";

      const response = await openaiClient.chat.completions.create({
        model: "gpt-4o", // or "gpt-4-vision-preview"
        messages: [
          {
            role: "user",
            content: [
              {
                type: "text",
                text: prompt,
              },
              {
                type: "image_url",
                image_url: {
                  url: `data:image/png;base64,${base64Image}`,
                },
              },
            ],
          },
        ],
        max_tokens: 500,
      });

      const analysis = response.choices[0].message.content;

      return {
        content: [
          {
            type: "text",
            text: `Screenshot Analysis:\n${analysis}\n\nScreenshot: ${screenshotPath}`,
          },
        ],
      };
    } catch (error) {
      return {
        content: [
          {
            type: "text",
            text: `Error analyzing screenshot: ${error.message}`,
          },
        ],
        isError: true,
      };
    }
  }

  async detectBuildErrors(args) {
    const { logText, ide } = args;
    const errors = [];
    const suggestions = [];

    // Common error patterns
    const errorPatterns = {
      xcode: [
        {
          pattern: /pod.*not found|CocoaPods/i,
          type: "missing_dependency",
          fix: "pod install",
          message: "CocoaPods dependency missing",
        },
        {
          pattern: /No such module|Cannot find/i,
          type: "import_error",
          fix: "Check imports and module dependencies",
          message: "Module import error",
        },
        {
          pattern: /Build failed|error:/i,
          type: "build_error",
          fix: "Review error details above",
          message: "Build compilation error",
        },
        {
          pattern: /signing.*error|provisioning/i,
          type: "signing_error",
          fix: "Check code signing settings",
          message: "Code signing issue",
        },
      ],
      android: [
        {
          pattern: /Gradle.*not found|dependency.*not found/i,
          type: "missing_dependency",
          fix: "./gradlew build --refresh-dependencies",
          message: "Gradle dependency missing",
        },
        {
          pattern: /BUILD FAILED/i,
          type: "build_error",
          fix: "Review Gradle error details",
          message: "Gradle build failed",
        },
        {
          pattern: /SDK.*not found|Android SDK/i,
          type: "sdk_error",
          fix: "Check Android SDK installation",
          message: "Android SDK issue",
        },
      ],
      terminal: [
        {
          pattern: /npm.*not found|package.*not found/i,
          type: "missing_dependency",
          fix: "npm install",
          message: "npm package missing",
        },
        {
          pattern: /python.*not found|ModuleNotFoundError/i,
          type: "missing_dependency",
          fix: "pip install <package>",
          message: "Python module missing",
        },
        {
          pattern: /error:|Error:|ERROR/i,
          type: "general_error",
          fix: "Review error message",
          message: "General error detected",
        },
      ],
    };

    const patterns = errorPatterns[ide] || errorPatterns.terminal;

    for (const errorPattern of patterns) {
      if (errorPattern.pattern.test(logText)) {
        errors.push({
          type: errorPattern.type,
          message: errorPattern.message,
          fix: errorPattern.fix,
        });
        suggestions.push(errorPattern.fix);
      }
    }

    // Check for success indicators
    const successPatterns = {
      xcode: /Build Succeeded|BUILD SUCCEEDED/i,
      android: /BUILD SUCCESSFUL/i,
      terminal: /success|Success|SUCCESS/i,
    };

    const isSuccess = successPatterns[ide]?.test(logText) || false;

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(
            {
              success: isSuccess,
              errors: errors,
              suggestions: suggestions,
              summary: isSuccess
                ? "Build succeeded!"
                : errors.length > 0
                ? `Found ${errors.length} error(s). Suggestions: ${suggestions.join(", ")}`
                : "No specific errors detected, but build may have failed.",
            },
            null,
            2
          ),
        },
      ],
    };
  }

  async loadAutomationMode() {
    try {
      const prefsPath = path.join(process.env.HOME, ".daisy", "preferences.json");
      const prefsContent = await fs.readFile(prefsPath, "utf-8");
      const prefs = JSON.parse(prefsContent);
      return prefs.automation?.mode || "autonomous";
    } catch (e) {
      return "autonomous"; // Default to autonomous
    }
  }

  async shouldAutoApprove(action) {
    try {
      const prefsPath = path.join(process.env.HOME, ".daisy", "preferences.json");
      const prefsContent = await fs.readFile(prefsPath, "utf-8");
      const prefs = JSON.parse(prefsContent);
      const autoApprovePatterns = prefs.automation?.auto_approve_patterns || [];
      return autoApprovePatterns.some((pattern) => action.includes(pattern));
    } catch (e) {
      return false;
    }
  }

  async buildWithRetry(args) {
    const { ide, action = "build", maxRetries = 3, projectPath, previewMode } = args;
    
    // Determine mode: explicit previewMode > preferences > default (autonomous)
    const usePreviewMode = previewMode !== undefined 
      ? previewMode 
      : (await this.loadAutomationMode()) === "preview";
    
    let attempt = 0;
    let lastError = null;
    const actionsTaken = [];
    const previewActions = [];

    while (attempt < maxRetries) {
      attempt++;
      actionsTaken.push(`Attempt ${attempt}: Executing ${action}...`);

      try {
        // Execute build
        if (ide === "xcode") {
          await this.openApplication({ appName: "Xcode" });
          await new Promise((resolve) => setTimeout(resolve, 2000)); // Wait for Xcode

          if (action === "build") {
            await this.keyPress({ keys: ["cmd", "b"] });
          } else if (action === "run") {
            await this.keyPress({ keys: ["cmd", "r"] });
          }

          // Wait for build to complete
          await new Promise((resolve) => setTimeout(resolve, 5000));

          // Capture build log
          const logResult = await this.captureBuildLog({ ide: "xcode" });
          const logText = logResult.content[0].text;

          // Detect errors
          const errorResult = await this.detectBuildErrors({
            logText: logText,
            ide: "xcode",
          });
          const errorData = JSON.parse(errorResult.content[0].text);

          if (errorData.success) {
            return {
              content: [
                {
                  type: "text",
                  text: `✅ Build succeeded on attempt ${attempt}!\n\nActions taken:\n${actionsTaken.join("\n")}`,
                },
              ],
            };
          }

          // If errors found, try to fix them
          if (errorData.errors.length > 0 && attempt < maxRetries) {
            const firstError = errorData.errors[0];
            actionsTaken.push(`Error detected: ${firstError.message}`);

            // Apply suggested fix
            const fixAction = firstError.fix;
            const shouldAutoApprove = await this.shouldAutoApprove(fixAction);
            
            if (usePreviewMode && !shouldAutoApprove) {
              // Preview mode: show action plan
              previewActions.push({
                action: fixAction,
                reason: firstError.message,
                autoApprove: false,
              });
              
              // In preview mode, return the action plan for approval
              return {
                content: [
                  {
                    type: "text",
                    text: JSON.stringify({
                      mode: "preview",
                      message: `Action required: ${fixAction}`,
                      reason: firstError.message,
                      error: firstError,
                      actions: previewActions,
                      prompt: `Should I execute: ${fixAction}? (This will fix: ${firstError.message})`,
                    }, null, 2),
                  },
                ],
              };
            } else {
              // Autonomous mode or auto-approve: execute directly
              if (fixAction.includes("pod install") && projectPath) {
                actionsTaken.push(`Applying fix: pod install`);
                await this.runTerminalCommand({
                  command: `cd "${projectPath}" && pod install`,
                });
                await new Promise((resolve) => setTimeout(resolve, 3000));
              } else if (fixAction.includes("npm install") && projectPath) {
                actionsTaken.push(`Applying fix: npm install`);
                await this.runTerminalCommand({
                  command: `cd "${projectPath}" && npm install`,
                });
                await new Promise((resolve) => setTimeout(resolve, 3000));
              }
            }

            lastError = errorData;
            // Continue to next attempt
            continue;
          }

          lastError = errorData;
        } else if (ide === "android") {
          // Similar logic for Android Studio
          await this.openApplication({ appName: "Android Studio" });
          // Android Studio automation would go here
          lastError = { message: "Android Studio automation not fully implemented" };
        } else {
          // Terminal builds
          if (projectPath && action === "build") {
            const result = await this.runTerminalCommand({
              command: action,
              workingDirectory: projectPath,
            });
            const logText = result.content[0].text;

            const errorResult = await this.detectBuildErrors({
              logText: logText,
              ide: "terminal",
            });
            const errorData = JSON.parse(errorResult.content[0].text);

            if (errorData.success) {
              return {
                content: [
                  {
                    type: "text",
                    text: `✅ Build succeeded on attempt ${attempt}!\n\nActions taken:\n${actionsTaken.join("\n")}`,
                  },
                ],
              };
            }

            lastError = errorData;
          }
        }
      } catch (error) {
        lastError = { message: error.message };
        actionsTaken.push(`Error: ${error.message}`);
      }

      // Wait before retry
      if (attempt < maxRetries) {
        await new Promise((resolve) => setTimeout(resolve, 2000));
      }
    }

    // All retries exhausted
    return {
      content: [
        {
          type: "text",
          text: `❌ Build failed after ${maxRetries} attempts.\n\nLast error: ${JSON.stringify(lastError, null, 2)}\n\nActions taken:\n${actionsTaken.join("\n")}`,
        },
      ],
      isError: true,
    };
  }

  setupErrorHandling() {
    this.server.onerror = (error) => {
      console.error("[MCP Error]", error);
    };

    process.on("SIGINT", async () => {
      await this.server.close();
      process.exit(0);
    });
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error("Desktop Automation MCP server running on stdio");
  }
}

const server = new DesktopAutomationServer();
server.run().catch(console.error);

