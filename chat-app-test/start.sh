#!/bin/bash

# Chat App Test - Start Script
echo "🚀 Starting ChemLink Chat Test..."
echo ""

# Change to the script directory
cd "$(dirname "$0")"

# Check if already running
if lsof -ti:5005 > /dev/null 2>&1; then
    echo "⚠️  Port 5005 is already in use"
    echo "   Kill it with: lsof -ti:5005 | xargs kill -9"
    exit 1
fi

echo "📋 Configuration:"
echo "  ✓ Flask app: app.py (original working version)"
echo "  ✓ Port: 5005"
echo "  ✓ Database: engagement-platform-dev (localhost:5433)"
echo "  ✓ Users: Jay Sanchez ↔ David Uy"
echo "  ✓ Features: File uploads (images/audio), Reactions, Read receipts"
echo ""

# Start Flask app in background
nohup python3 app.py > server.log 2>&1 &
PID=$!

# Wait a moment for it to start
sleep 2

# Check if it's running
if ps -p $PID > /dev/null; then
    echo "✅ Chat app started successfully!"
    echo "   PID: $PID"
    echo "   URL: http://localhost:5005"
    echo "   Logs: tail -f server.log"
    echo ""
    echo "🛑 To stop: lsof -ti:5005 | xargs kill -9"
else
    echo "❌ Failed to start - check server.log for errors"
    exit 1
fi
