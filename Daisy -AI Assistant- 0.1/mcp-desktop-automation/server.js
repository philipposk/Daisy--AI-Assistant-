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

