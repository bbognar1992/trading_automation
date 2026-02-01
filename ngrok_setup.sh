#!/bin/bash
# Quick setup script for ngrok
# This script helps you set up ngrok to expose your FastAPI server

echo "=== ngrok Setup for TradingView-IBKR Middleman ==="
echo ""

# Check if ngrok is installed
if ! command -v ngrok &> /dev/null; then
    echo "❌ ngrok is not installed."
    echo ""
    echo "Install ngrok:"
    echo "  macOS: brew install ngrok/ngrok/ngrok"
    echo "  Or visit: https://ngrok.com/download"
    echo ""
    exit 1
fi

echo "✅ ngrok is installed"
echo ""

# Check if authtoken is configured
if ! ngrok config check &> /dev/null; then
    echo "⚠️  ngrok authtoken not configured"
    echo ""
    echo "Get your authtoken from: https://dashboard.ngrok.com/get-started/your-authtoken"
    echo "Then run: ngrok config add-authtoken YOUR_AUTH_TOKEN"
    echo ""
    read -p "Do you want to configure it now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "Enter your ngrok authtoken: " authtoken
        ngrok config add-authtoken "$authtoken"
        echo "✅ Authtoken configured"
    else
        exit 1
    fi
else
    echo "✅ ngrok authtoken is configured"
fi

echo ""
echo "=== Starting ngrok ==="
echo "This will expose your local server on port 8000"
echo "Press Ctrl+C to stop"
echo ""

# Start ngrok
ngrok http 8000

