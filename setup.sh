#!/bin/bash

# Universal Manga Downloader - Quick Start Script

echo "🚀 Universal Manga Downloader Setup"
echo "===================================="

# Check if we're in the right directory
if [ ! -f "manga_downloader.py" ]; then
    echo "❌ Error: Please run this script from the project root directory"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3.11 -m venv .venv
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -q --upgrade pip
pip install -q -e .

# Check if Tkinter is available
echo "🔍 Checking Tkinter availability..."
if python -c "import tkinter" 2>/dev/null; then
    echo "✅ Tkinter is available"
    TKINTER_OK=true
else
    echo "⚠️  Tkinter not found"
    echo ""
    echo "To install Tkinter on macOS:"
    echo "  brew reinstall python@3.11 python-tk@3.11"
    echo ""
    echo "Or run without GUI:"
    echo "  umd --no-gui --doctor"
    TKINTER_OK=false
fi

# Run diagnostics
echo ""
echo "🏥 Running diagnostics..."
umd --doctor

echo ""
echo "===================================="
if [ "$TKINTER_OK" = true ]; then
    echo "✅ Setup complete! Run 'umd' to start the application"
else
    echo "⚠️  Setup complete with warnings. Install Tkinter to use GUI mode."
fi
echo ""
echo "Useful commands:"
echo "  umd               - Start the GUI application"
echo "  umd --version     - Show version information"
echo "  umd --doctor      - Run diagnostics"
echo "  umd --config-info - Show configuration"
echo "  umd --help        - Show all options"
