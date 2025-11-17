#!/bin/bash

# Newsletter Analyst - Quick Setup Script
# This script automates the initial setup process

set -e  # Exit on error

echo "=========================================="
echo "Newsletter Analyst - Quick Setup"
echo "=========================================="
echo ""

# Check Python version
echo "Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
REQUIRED_VERSION="3.10"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "Error: Python $REQUIRED_VERSION or higher is required (found $PYTHON_VERSION)"
    exit 1
fi

echo "✓ Python $PYTHON_VERSION found"
echo ""

# Create virtual environment
echo "Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
echo "✓ Virtual environment activated"
echo ""

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip --quiet
echo "✓ pip upgraded"
echo ""

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt --quiet
echo "✓ Dependencies installed"
echo ""

# Create necessary directories
echo "Creating directories..."
mkdir -p data
mkdir -p config
mkdir -p output
mkdir -p logs
echo "✓ Directories created"
echo ""

# Set up .env file
if [ ! -f ".env" ]; then
    echo "Setting up .env file..."
    cp .env.example .env
    echo "✓ .env file created from .env.example"
    echo ""
    echo "⚠️  IMPORTANT: Edit .env file and add your API keys:"
    echo "   - ANTHROPIC_API_KEY"
    echo "   - GMAIL_CREDENTIALS_PATH (default: config/credentials.json)"
else
    echo "✓ .env file already exists"
fi
echo ""

# Check for Gmail credentials
echo "Checking for Gmail credentials..."
if [ ! -f "config/credentials.json" ]; then
    echo "⚠️  Gmail credentials not found!"
    echo ""
    echo "Please complete the following steps:"
    echo "1. Go to Google Cloud Console: https://console.cloud.google.com/"
    echo "2. Create a project and enable Gmail API"
    echo "3. Create OAuth 2.0 credentials (Desktop app)"
    echo "4. Download the JSON file"
    echo "5. Copy it to: config/credentials.json"
    echo ""
else
    echo "✓ Gmail credentials found"
fi
echo ""

# Print next steps
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Configure your API keys:"
echo "   nano .env"
echo ""
echo "2. Add Gmail credentials (if not done):"
echo "   cp ~/Downloads/client_secret_*.json config/credentials.json"
echo ""
echo "3. Authenticate with Gmail:"
echo "   python -m src.gmail_client"
echo ""
echo "4. Fetch your first emails:"
echo "   python src/main.py fetch-emails --label 'Newsletter' --max-results 50"
echo ""
echo "5. Analyze emails:"
echo "   python src/main.py analyze-emails"
echo ""
echo "6. Launch dashboard:"
echo "   streamlit run dashboard.py"
echo ""
echo "For detailed instructions, see DEPLOYMENT.md"
echo ""
