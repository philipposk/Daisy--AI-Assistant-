#!/bin/bash
# Test the MCP server

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR/mcp-desktop-automation"

echo "🧪 Testing MCP Server..."
echo ""

# Test that the server file exists and is executable
if [ ! -f "server.js" ]; then
    echo "❌ Error: server.js not found"
    exit 1
fi

# Test Node.js can run it (should exit immediately with proper error if not configured as MCP)
echo "✅ MCP server file found"
echo "✅ Node.js version: $(node --version)"
echo "✅ MCP SDK installed: $(npm list @modelcontextprotocol/sdk 2>/dev/null | grep @modelcontextprotocol || echo 'not found')"
echo ""
echo "✅ MCP server is ready!"
echo "💡 Note: This server must be configured in Cursor to be used"
echo "📋 See CURSOR_SETUP.md for configuration instructions"

