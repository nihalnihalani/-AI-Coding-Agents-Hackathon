"""
Voice-controlled navigation for AI Agent using Gemini Live API
"""

import os
import asyncio
import base64
import io
import traceback
import json
import time
from typing import Dict, Any, Optional

import cv2
import pyaudio
import PIL.Image
import mss
import pyautogui

from google import genai
from google.genai import types

# Audio configuration
FORMAT = pyaudio.paInt16
CHANNELS = 1
SEND_SAMPLE_RATE = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE = 1024

MODEL = "models/gemini-2.5-flash-exp-native-audio-thinking-dialog"

# Initialize Gemini client
client = genai.Client(
    http_options={"api_version": "v1beta"},
    api_key=os.environ.get("GEMINI_API_KEY"),
)

# Navigation function declarations
navigation_functions = [
    types.FunctionDeclaration(
        name='navigate_to_page',
        description='Navigate to a specific page in the AI Agent application',
        parameters=types.Schema(
            type='OBJECT',
            properties={
                'page': types.Schema(
                    type='STRING',
                    description='The page to navigate to: dashboard, chat, onboarding, approvals, profile, settings',
                    enum=['dashboard', 'chat', 'onboarding', 'approvals', 'profile', 'settings']
                ),
            },
            required=['page'],
        ),
    ),
    types.FunctionDeclaration(
        name='click_element',
        description='Click on a specific UI element',
        parameters=types.Schema(
            type='OBJECT',
            properties={
                'element_type': types.Schema(
                    type='STRING',
                    description='Type of element to click: button, link, input, card',
                ),
                'element_text': types.Schema(
                    type='STRING',
                    description='Text content or label of the element to click',
                ),
                'x': types.Schema(
                    type='INTEGER',
                    description='X coordinate to click (optional)',
                ),
                'y': types.Schema(
                    type='INTEGER',
                    description='Y coordinate to click (optional)',
                ),
            },
            required=['element_type'],
        ),
    ),
    types.FunctionDeclaration(
        name='type_text',
        description='Type text into an input field',
        parameters=types.Schema(
            type='OBJECT',
            properties={
                'text': types.Schema(
                    type='STRING',
                    description='Text to type',
                ),
            },
            required=['text'],
        ),
    ),
    types.FunctionDeclaration(
        name='scroll_page',
        description='Scroll the page up or down',
        parameters=types.Schema(
            type='OBJECT',
            properties={
                'direction': types.Schema(
                    type='STRING',
                    description='Direction to scroll: up or down',
                    enum=['up', 'down']
                ),
                'amount': types.Schema(
                    type='INTEGER',
                    description='Amount to scroll (default 3)',
                ),
            },
            required=['direction'],
        ),
    ),
]

tools = [
    types.Tool(function_declarations=navigation_functions),
    types.Tool(google_search=types.GoogleSearch()),
]

CONFIG = types.LiveConnectConfig(
    response_modalities=["AUDIO"],
    media_resolution="MEDIA_RESOLUTION_MEDIUM",
    speech_config=types.SpeechConfig(
        voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Zephyr")
        )
    ),
    realtime_input_config=types.RealtimeInputConfig(turn_coverage="TURN_INCLUDES_ALL_INPUT"),
    context_window_compression=types.ContextWindowCompressionConfig(
        trigger_tokens=25600,
        sliding_window=types.SlidingWindow(target_tokens=12800),
    ),
    tools=tools,
    system_instruction="""You are a voice assistant for the AI Agent application. You can see the current screen and help users navigate the application using voice commands.

Available navigation commands:
- "Go to dashboard" - Navigate to the dashboard page
- "Open chat" - Navigate to the chat page  
- "Show onboarding" - Navigate to onboarding page
- "View approvals" - Navigate to approvals page
- "Open profile" - Navigate to profile page
- "Go to settings" - Navigate to settings page
- "Click [element]" - Click on buttons, links, or other UI elements
- "Type [text]" - Type text into input fields
- "Scroll up/down" - Scroll the page

You can see what's currently on screen and should describe what you see and suggest relevant actions. Be conversational and helpful.

When users give navigation commands, use the appropriate function calls to perform the actions."""
)

pya = pyaudio.PyAudio()

class VoiceNavigator:
    def __init__(self):
        self.audio_in_queue = None
        self.out_queue = None
        self.session = None
        self.audio_stream = None

    def navigate_to_page(self, page: str) -> Dict[str, Any]:
        """Navigate to a specific page using browser navigation"""
        try:
            # Map page names to URLs
            url_map = {
                'dashboard': 'http://localhost:3000/dashboard',
                'chat': 'http://localhost:3000/chat',
                'onboarding': 'http://localhost:3000/onboarding',
                'approvals': 'http://localhost:3000/approvals',
                'profile': 'http://localhost:3000/profile',
                'settings': 'http://localhost:3000/settings'
            }
            
            if page in url_map:
                # Use pyautogui to navigate - press Cmd+L to focus address bar, then type URL
                pyautogui.hotkey('cmd', 'l')  # Focus address bar (Mac)
                time.sleep(0.5)
                pyautogui.typewrite(url_map[page])
                pyautogui.press('enter')
                return {"success": True, "message": f"Navigated to {page} page"}
            else:
                return {"success": False, "message": f"Unknown page: {page}"}
        except Exception as e:
            return {"success": False, "message": f"Navigation error: {str(e)}"}

    def click_element(self, element_type: str, element_text: Optional[str] = None, 
                     x: Optional[int] = None, y: Optional[int] = None) -> Dict[str, Any]:
        """Click on a UI element"""
        try:
            if x is not None and y is not None:
                pyautogui.click(x, y)
                return {"success": True, "message": f"Clicked at coordinates ({x}, {y})"}
            elif element_text:
                # Try to find element by text (simplified approach)
                # In a real implementation, you might use computer vision or OCR
                return {"success": True, "message": f"Attempted to click {element_type} with text '{element_text}'"}
            else:
                return {"success": False, "message": "Need either coordinates or element text"}
        except Exception as e:
            return {"success": False, "message": f"Click error: {str(e)}"}

    def type_text(self, text: str) -> Dict[str, Any]:
        """Type text into the currently focused input"""
        try:
            pyautogui.typewrite(text)
            return {"success": True, "message": f"Typed: {text}"}
        except Exception as e:
            return {"success": False, "message": f"Type error: {str(e)}"}

    def scroll_page(self, direction: str, amount: int = 3) -> Dict[str, Any]:
        """Scroll the page up or down"""
        try:
            if direction == 'up':
                pyautogui.scroll(amount)
            elif direction == 'down':
                pyautogui.scroll(-amount)
            return {"success": True, "message": f"Scrolled {direction}"}
        except Exception as e:
            return {"success": False, "message": f"Scroll error: {str(e)}"}

    def _get_screen(self):
        """Capture current screen"""
        sct = mss.mss()
        monitor = sct.monitors[0]
        screenshot = sct.grab(monitor)
        
        # Convert to PIL Image
        img = PIL.Image.frombytes('RGB', screenshot.size, screenshot.bgra, 'raw', 'BGRX')
        
        # Resize for efficiency
        img.thumbnail([1024, 1024])
        
        # Convert to base64
        image_io = io.BytesIO()
        img.save(image_io, format="jpeg")
        image_io.seek(0)
        
        mime_type = "image/jpeg"
        image_bytes = image_io.read()
        return {"mime_type": mime_type, "data": base64.b64encode(image_bytes).decode()}

    async def get_screen(self):
        """Continuously capture screen"""
        while True:
            frame = await asyncio.to_thread(self._get_screen)
            if frame is None:
                break
            await asyncio.sleep(2.0)  # Capture every 2 seconds
            await self.out_queue.put(frame)

    async def send_realtime(self):
        """Send screen captures to Gemini"""
        while True:
            msg = await self.out_queue.get()
            await self.session.send(input=msg)

    async def listen_audio(self):
        """Listen to microphone input"""
        mic_info = pya.get_default_input_device_info()
        self.audio_stream = await asyncio.to_thread(
            pya.open,
            format=FORMAT,
            channels=CHANNELS,
            rate=SEND_SAMPLE_RATE,
            input=True,
            input_device_index=mic_info["index"],
            frames_per_buffer=CHUNK_SIZE,
        )
        kwargs = {"exception_on_overflow": False} if __debug__ else {}
        
        while True:
            data = await asyncio.to_thread(self.audio_stream.read, CHUNK_SIZE, **kwargs)
            await self.out_queue.put({"data": data, "mime_type": "audio/pcm"})

    async def receive_audio(self):
        """Receive and process audio responses from Gemini"""
        while True:
            turn = self.session.receive()
            async for response in turn:
                if data := response.data:
                    self.audio_in_queue.put_nowait(data)
                    continue
                if text := response.text:
                    print(f"Assistant: {text}")
                if response.function_calls:
                    for function_call in response.function_calls:
                        await self._handle_function_call(function_call)

            # Clear audio queue on interruption
            while not self.audio_in_queue.empty():
                self.audio_in_queue.get_nowait()

    async def _handle_function_call(self, function_call):
        """Handle function calls from Gemini"""
        function_name = function_call.name
        args = function_call.args
        
        print(f"Executing: {function_name} with args: {args}")
        
        if function_name == 'navigate_to_page':
            result = self.navigate_to_page(args.get('page'))
        elif function_name == 'click_element':
            result = self.click_element(
                args.get('element_type'),
                args.get('element_text'),
                args.get('x'),
                args.get('y')
            )
        elif function_name == 'type_text':
            result = self.type_text(args.get('text'))
        elif function_name == 'scroll_page':
            result = self.scroll_page(args.get('direction'), args.get('amount', 3))
        else:
            result = {"success": False, "message": f"Unknown function: {function_name}"}
        
        # Send function response back to Gemini
        function_response = types.Part.from_function_response(
            name=function_name,
            response=result
        )
        await self.session.send(input=function_response, end_of_turn=True)

    async def play_audio(self):
        """Play audio responses"""
        stream = await asyncio.to_thread(
            pya.open,
            format=FORMAT,
            channels=CHANNELS,
            rate=RECEIVE_SAMPLE_RATE,
            output=True,
        )
        while True:
            bytestream = await self.audio_in_queue.get()
            await asyncio.to_thread(stream.write, bytestream)

    async def send_text(self):
        """Handle text input (for testing)"""
        while True:
            text = await asyncio.to_thread(input, "Text command (or 'q' to quit): ")
            if text.lower() == "q":
                break
            await self.session.send(input=text or ".", end_of_turn=True)

    async def run(self):
        """Main run loop"""
        try:
            print("🎙️ Starting Voice Navigator for AI Agent")
            print("📱 Make sure the AI Agent is open at http://localhost:3000")
            print("🔊 Speak your navigation commands...")
            print("💬 Examples: 'Go to dashboard', 'Open chat', 'Click login button'")
            print("❌ Say 'quit' or press Ctrl+C to exit")
            
            async with (
                client.aio.live.connect(model=MODEL, config=CONFIG) as session,
                asyncio.TaskGroup() as tg,
            ):
                self.session = session
                self.audio_in_queue = asyncio.Queue()
                self.out_queue = asyncio.Queue(maxsize=5)

                # Start all tasks
                send_text_task = tg.create_task(self.send_text())
                tg.create_task(self.send_realtime())
                tg.create_task(self.listen_audio())
                tg.create_task(self.get_screen())
                tg.create_task(self.receive_audio())
                tg.create_task(self.play_audio())

                await send_text_task
                raise asyncio.CancelledError("User requested exit")

        except asyncio.CancelledError:
            print("\n👋 Voice Navigator stopped")
        except Exception as e:
            if self.audio_stream:
                self.audio_stream.close()
            traceback.print_exception(e)

def main():
    """Entry point"""
    if not os.environ.get("GEMINI_API_KEY"):
        print("❌ Error: GEMINI_API_KEY environment variable not set")
        print("Please set your Gemini API key:")
        print("export GEMINI_API_KEY='your-api-key-here'")
        return
    
    navigator = VoiceNavigator()
    asyncio.run(navigator.run())

if __name__ == "__main__":
    main()