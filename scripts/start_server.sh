#Author: Rishi


#!/bin/bash

# Simple script to start a local HTTP server for the CAPTCHA demo

PORT=8000

# Kill any existing process on the port
if lsof -ti:$PORT &> /dev/null; then
    echo "⚠️  Port $PORT is already in use. Stopping existing process..."
    lsof -ti:$PORT | xargs kill -9 2>/dev/null
    sleep 1
fi

echo "🚀 Starting Motor-Timing CAPTCHA Demo Server..."
echo ""
echo "Server will be available at: http://localhost:$PORT"
echo "Press Ctrl+C to stop the server"
echo ""

# Check for Python 3 first
if command -v python3 &> /dev/null; then
    echo "Starting Python 3 HTTP server..."
    python3 -m http.server $PORT
# Fallback to Python 2
elif command -v python &> /dev/null; then
    echo "Starting Python 2 HTTP server..."
    python -m SimpleHTTPServer $PORT
else
    echo "❌ Error: Python is not installed."
    echo "Please install Python or use another method from the README."
    exit 1
fi


