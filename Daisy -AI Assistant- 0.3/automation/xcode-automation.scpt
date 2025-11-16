-- AppleScript for Xcode automation
-- This script can be called from the MCP server or Python scripts

on run argv
    set action to item 1 of argv
    set projectPath to item 2 of argv
    
    if action is "open" then
        tell application "Xcode"
            open projectPath
            activate
        end tell
    else if action is "build" then
        tell application "Xcode"
            activate
            tell application "System Events"
                tell process "Xcode"
                    keystroke "b" using {command down}
                end tell
            end tell
        end tell
    else if action is "run" then
        tell application "Xcode"
            activate
            tell application "System Events"
                tell process "Xcode"
                    keystroke "r" using {command down}
                end tell
            end tell
        end tell
    else if action is "clean" then
        tell application "Xcode"
            activate
            tell application "System Events"
                tell process "Xcode"
                    keystroke "k" using {command down, shift down}
                end tell
            end tell
        end tell
    end if
end run

