#!/bin/bash

echo "============================================"
echo "      Drawing Editor Launcher"
echo "============================================"
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 is not installed or not in PATH."
    echo "Please install Python 3.8+ and add it to your system PATH."
    exit 1
fi

# Check if the main script exists
if [ ! -f "drawing_editor/main.py" ]; then
    echo "[ERROR] drawing_editor/main.py not found."
    echo "Please run this script from the project root directory."
    exit 1
fi

# Check and install dependencies
echo "Checking dependencies..."

python3 -c "import PyQt5" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Installing PyQt5..."
    pip3 install PyQt5
    if [ $? -ne 0 ]; then
        echo "Failed to install PyQt5. Please install manually: pip3 install PyQt5"
        exit 1
    fi
fi

python3 -c "import ezdxf" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Installing ezdxf..."
    pip3 install ezdxf
    if [ $? -ne 0 ]; then
        echo "Failed to install ezdxf. Please install manually: pip3 install ezdxf"
        exit 1
    fi
fi

echo "Dependencies OK."
echo ""

# Run the application
echo "Starting editor..."
export PYTHONPATH="$(cd "$(dirname "$0")" && pwd)"
export QT_QPA_PLATFORM=offscreen
python3 drawing_editor/main.py
