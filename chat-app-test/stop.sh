#!/bin/bash

# Chat App Test - Stop Script
echo "🛑 Stopping ChemLink Chat Test..."
echo ""

# Kill process on port 5005
if lsof -ti:5005 > /dev/null 2>&1; then
    PID=$(lsof -ti:5005)
    kill -9 $PID
    echo "✅ Stopped chat app (PID: $PID)"
else
    echo "ℹ️  No process running on port 5005"
fi

echo ""
echo "Done!"
