#!/bin/bash

echo "🚀 Installing Voice Navigator Dependencies"
echo "========================================"

# Check Python version
python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "📍 Python version: $python_version"

# Install system dependencies on macOS
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "🍎 Detected macOS - installing system dependencies"
    
    # Check if Homebrew is installed
    if ! command -v brew &> /dev/null; then
        echo "❌ Homebrew not found. Please install Homebrew first:"
        echo "   /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        exit 1
    fi
    
    # Install portaudio for PyAudio
    echo "🔊 Installing PortAudio for PyAudio..."
    brew install portaudio
    
    # Install OpenCV dependencies
    echo "📷 Installing OpenCV dependencies..."
    brew install opencv
    
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "🐧 Detected Linux - installing system dependencies"
    
    # Ubuntu/Debian
    if command -v apt &> /dev/null; then
        sudo apt update
        sudo apt install -y portaudio19-dev python3-pyaudio
        sudo apt install -y python3-opencv
    # Red Hat/CentOS/Fedora
    elif command -v yum &> /dev/null; then
        sudo yum install -y portaudio-devel
        sudo yum install -y python3-opencv
    elif command -v dnf &> /dev/null; then
        sudo dnf install -y portaudio-devel
        sudo dnf install -y python3-opencv
    fi
fi

# Create virtual environment
echo "🌟 Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
echo "📦 Upgrading pip..."
pip install --upgrade pip

# Install Python dependencies
echo "🐍 Installing Python packages..."
pip install -r requirements.txt

# Additional installations that might be needed
echo "🔧 Installing additional dependencies..."
pip install requests  # For testing connectivity

# Test installations
echo "🧪 Testing installations..."
python -c "import cv2; print('✅ OpenCV installed')" || echo "❌ OpenCV installation failed"
python -c "import pyaudio; print('✅ PyAudio installed')" || echo "❌ PyAudio installation failed"
python -c "import PIL; print('✅ Pillow installed')" || echo "❌ Pillow installation failed"
python -c "import mss; print('✅ MSS installed')" || echo "❌ MSS installation failed"
python -c "import pyautogui; print('✅ PyAutoGUI installed')" || echo "❌ PyAutoGUI installation failed"
python -c "from google import genai; print('✅ Google GenAI installed')" || echo "❌ Google GenAI installation failed"

echo ""
echo "✨ Installation complete!"
echo ""
echo "Next steps:"
echo "1. Set your Gemini API key:"
echo "   export GEMINI_API_KEY='your-api-key-here'"
echo ""
echo "2. Make sure AI Agent is running:"
echo "   Backend: http://localhost:8000"
echo "   Frontend: http://localhost:3000"
echo ""
echo "3. Run the test suite:"
echo "   python test_voice.py"
echo ""
echo "4. Start voice navigation:"
echo "   python voice_navigator.py"
echo ""
echo "📱 On macOS, you may need to grant permissions for:"
echo "   • Microphone access"
echo "   • Screen recording"
echo "   • Accessibility (for PyAutoGUI)"