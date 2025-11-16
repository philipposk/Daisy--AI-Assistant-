#!/bin/bash
# Start the Daisy Agent Controller

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "🚀 Starting Daisy Agent Controller..."
echo "📝 Logs will be written to ~/.daisy/logs/"
echo ""

# Use simple controller (no heavy dependencies)
python3 agent-controller/simple-controller.py

