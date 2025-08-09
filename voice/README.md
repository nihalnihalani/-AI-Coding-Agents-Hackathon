# Voice Navigator for AI Agent

Voice-controlled navigation system using Gemini's Live API for hands-free interaction with the AI Agent application.

## Features

- 🎙️ **Voice Commands**: Control the application using natural speech
- 👁️ **Screen Awareness**: AI can see and understand the current screen
- 🗣️ **Audio Responses**: Get spoken feedback from the AI assistant
- 🖱️ **Smart Navigation**: Automatic page navigation and UI interaction
- ⌨️ **Text Input**: Voice-to-text input for forms and chat

## Setup

### 1. Install Dependencies

```bash
cd voice
pip install -r requirements.txt
```

### 2. Set Gemini API Key

Get your API key from [Google AI Studio](https://makersuite.google.com/app/apikey):

```bash
export GEMINI_API_KEY="your-api-key-here"
```

### 3. Start the AI Agent Application

Make sure the AI Agent is running:
- Backend: `http://localhost:8000`
- Frontend: `http://localhost:3000`

### 4. Run Voice Navigator

```bash
python voice_navigator.py
```

## Voice Commands

### Navigation Commands
- **"Go to dashboard"** - Navigate to the dashboard page
- **"Open chat"** - Navigate to the chat page
- **"Show onboarding"** - Navigate to onboarding page
- **"View approvals"** - Navigate to approvals page
- **"Open profile"** - Navigate to profile page
- **"Go to settings"** - Navigate to settings page

### Interaction Commands
- **"Click [element]"** - Click on buttons, links, or UI elements
- **"Type [text]"** - Type text into input fields
- **"Scroll up/down"** - Scroll the page
- **"Login"** - Navigate to login and fill credentials

### Example Usage
- "Go to the chat page"
- "Click the send button"
- "Type hello world"
- "Scroll down to see more"
- "Open the dashboard"

## How It Works

1. **Screen Capture**: Continuously captures screenshots of your screen
2. **Audio Input**: Listens to your microphone for voice commands
3. **AI Processing**: Gemini AI processes both visual and audio input
4. **Function Calling**: AI determines appropriate actions based on commands
5. **Automation**: Executes navigation and UI interactions using PyAutoGUI
6. **Audio Response**: Provides spoken feedback about actions taken

## Technical Details

### Models Used
- **Gemini 2.5 Flash**: For multimodal understanding (vision + audio)
- **Native Audio**: Real-time voice processing
- **Function Calling**: Structured command execution

### Capabilities
- **Multimodal Input**: Simultaneous screen capture and voice input
- **Real-time Processing**: Low-latency command execution
- **Context Awareness**: Understands current application state
- **Natural Language**: Supports conversational commands

## Troubleshooting

### Audio Issues
- Check microphone permissions
- Ensure audio devices are properly configured
- Test with `python -c "import pyaudio; print('Audio OK')"`

### Screen Capture Issues
- Grant screen recording permissions on macOS
- Test with `python -c "import mss; print('Screen capture OK')"`

### API Issues
- Verify GEMINI_API_KEY is set correctly
- Check internet connection
- Ensure API quota is not exceeded

### Navigation Issues
- Make sure AI Agent is running on localhost:3000
- Check browser is in focus
- Verify PyAutoGUI permissions on macOS

## Advanced Usage

### Custom Commands
You can extend the voice navigator by adding custom function declarations in `voice_navigator.py`:

```python
custom_function = types.FunctionDeclaration(
    name='custom_action',
    description='Description of your custom action',
    parameters=types.Schema(
        type='OBJECT',
        properties={
            'param': types.Schema(
                type='STRING',
                description='Parameter description',
            ),
        },
        required=['param'],
    ),
)
```

### Configuration Options
- Adjust screen capture frequency in `get_screen()`
- Modify audio settings (sample rate, channels, etc.)
- Customize voice assistant personality in system instructions

## Security Notes

- Voice commands are processed by Google's Gemini API
- Screen captures are sent to Google for analysis
- No audio/screen data is stored permanently
- Use in trusted environments only
- Consider privacy implications before use

## License

MIT License - Feel free to modify and extend!