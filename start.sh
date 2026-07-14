#!/bin/bash
set -e

# Change directory to the agent directory
cd "$(dirname "$0")/elder-asset-agent"

echo "🚀 Starting Elder Asset Agent setup..."

# Check if python3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 is not installed. Please install Python 3 first."
    exit 1
fi

# Check if .env exists, if not copy from .env.example
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        echo "📝 Creating .env file from .env.example..."
        cp .env.example .env
        echo "⚠️ Please make sure to add your GEMINI_API_KEY to the elder-asset-agent/.env file!"
    else
        echo "❌ Error: .env.example not found."
    fi
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating Python virtual environment (venv)..."
    python3 -m venv venv
else
    echo "✅ Virtual environment already exists."
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip and install dependencies
echo "📥 Installing/Updating dependencies from requirements.txt..."
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo "✅ Dependencies installed successfully!"

# Run the chatbot
echo "🤖 Starting Elder Asset Agent Chatbot..."
echo "----------------------------------------"
python chat.py
