#!/usr/bin/env python3
"""
Test script for Voice Navigator
Tests individual components and dependencies
"""

import sys
import os

def test_imports():
    """Test all required imports"""
    print("🧪 Testing imports...")
    
    try:
        import cv2
        print("✅ OpenCV: OK")
    except ImportError as e:
        print(f"❌ OpenCV: {e}")
        return False
    
    try:
        import pyaudio
        print("✅ PyAudio: OK")
    except ImportError as e:
        print(f"❌ PyAudio: {e}")
        return False
    
    try:
        import PIL.Image
        print("✅ Pillow: OK")
    except ImportError as e:
        print(f"❌ Pillow: {e}")
        return False
    
    try:
        import mss
        print("✅ MSS (Screen capture): OK")
    except ImportError as e:
        print(f"❌ MSS: {e}")
        return False
    
    try:
        import pyautogui
        print("✅ PyAutoGUI: OK")
    except ImportError as e:
        print(f"❌ PyAutoGUI: {e}")
        return False
    
    try:
        from google import genai
        print("✅ Google GenAI: OK")
    except ImportError as e:
        print(f"❌ Google GenAI: {e}")
        return False
    
    return True

def test_audio():
    """Test audio system"""
    print("\n🔊 Testing audio system...")
    
    try:
        import pyaudio
        pya = pyaudio.PyAudio()
        
        # List audio devices
        print("Available audio devices:")
        for i in range(pya.get_device_count()):
            info = pya.get_device_info_by_index(i)
            print(f"  {i}: {info['name']} - {info['maxInputChannels']} in, {info['maxOutputChannels']} out")
        
        # Test default input device
        default_input = pya.get_default_input_device_info()
        print(f"✅ Default input device: {default_input['name']}")
        
        # Test default output device
        default_output = pya.get_default_output_device_info()
        print(f"✅ Default output device: {default_output['name']}")
        
        pya.terminate()
        return True
        
    except Exception as e:
        print(f"❌ Audio test failed: {e}")
        return False

def test_screen_capture():
    """Test screen capture"""
    print("\n📸 Testing screen capture...")
    
    try:
        import mss
        import PIL.Image
        
        with mss.mss() as sct:
            # Get monitor info
            monitors = sct.monitors
            print(f"✅ Found {len(monitors)-1} monitors")
            
            for i, monitor in enumerate(monitors[1:], 1):  # Skip the first (all monitors)
                print(f"  Monitor {i}: {monitor['width']}x{monitor['height']} at ({monitor['left']}, {monitor['top']})")
            
            # Test screenshot
            screenshot = sct.grab(monitors[0])  # All monitors
            img = PIL.Image.frombytes('RGB', screenshot.size, screenshot.bgra, 'raw', 'BGRX')
            print(f"✅ Screenshot captured: {img.size}")
            
        return True
        
    except Exception as e:
        print(f"❌ Screen capture test failed: {e}")
        return False

def test_automation():
    """Test PyAutoGUI automation"""
    print("\n🖱️ Testing automation...")
    
    try:
        import pyautogui
        
        # Get screen size
        screen_size = pyautogui.size()
        print(f"✅ Screen size: {screen_size}")
        
        # Get current mouse position
        mouse_pos = pyautogui.position()
        print(f"✅ Mouse position: {mouse_pos}")
        
        # Test failsafe
        pyautogui.FAILSAFE = True
        print("✅ Failsafe enabled (move mouse to top-left corner to stop)")
        
        return True
        
    except Exception as e:
        print(f"❌ Automation test failed: {e}")
        return False

def test_gemini_api():
    """Test Gemini API connection"""
    print("\n🤖 Testing Gemini API...")
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY not set")
        print("Set it with: export GEMINI_API_KEY='your-api-key'")
        return False
    
    try:
        from google import genai
        
        client = genai.Client(
            http_options={"api_version": "v1beta"},
            api_key=api_key,
        )
        
        # Test simple text generation
        response = client.models.generate_content(
            model='gemini-2.0-flash-001',
            contents='Say "Hello from Voice Navigator test!"'
        )
        
        print(f"✅ API Response: {response.text}")
        return True
        
    except Exception as e:
        print(f"❌ Gemini API test failed: {e}")
        return False

def test_app_connectivity():
    """Test AI Agent app connectivity"""
    print("\n🌐 Testing AI Agent connectivity...")
    
    try:
        import requests
        
        # Test backend
        try:
            response = requests.get("http://localhost:8000/health", timeout=5)
            if response.status_code == 200:
                print("✅ Backend (port 8000): OK")
            else:
                print(f"⚠️ Backend responded with status {response.status_code}")
        except requests.exceptions.RequestException:
            print("❌ Backend (port 8000): Not responding")
            return False
        
        # Test frontend
        try:
            response = requests.get("http://localhost:3000", timeout=5)
            if response.status_code == 200:
                print("✅ Frontend (port 3000): OK")
            else:
                print(f"⚠️ Frontend responded with status {response.status_code}")
        except requests.exceptions.RequestException:
            print("❌ Frontend (port 3000): Not responding")
            print("Make sure to run: npm run dev in the frontend directory")
            return False
        
        return True
        
    except ImportError:
        print("❌ Requests library not available")
        return False

def main():
    """Run all tests"""
    print("🚀 Voice Navigator Test Suite")
    print("=" * 40)
    
    tests = [
        test_imports,
        test_audio, 
        test_screen_capture,
        test_automation,
        test_gemini_api,
        test_app_connectivity,
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    print("\n" + "=" * 40)
    print("📊 Test Results:")
    
    test_names = [
        "Imports",
        "Audio System", 
        "Screen Capture",
        "Automation",
        "Gemini API",
        "App Connectivity",
    ]
    
    passed = 0
    for name, result in zip(test_names, results):
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {name}: {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{len(tests)} tests passed")
    
    if all(results):
        print("\n🎉 All tests passed! Voice Navigator should work correctly.")
        print("\nTo run the voice navigator:")
        print("  python voice_navigator.py")
    else:
        print("\n⚠️ Some tests failed. Please fix the issues before running the voice navigator.")
        
        if not results[4]:  # Gemini API test
            print("\n💡 To set up Gemini API:")
            print("  1. Go to https://makersuite.google.com/app/apikey")
            print("  2. Create an API key")
            print("  3. Export it: export GEMINI_API_KEY='your-key'")
        
        if not results[5]:  # App connectivity
            print("\n💡 To start the AI Agent:")
            print("  1. Backend: cd backend && python main.py")
            print("  2. Frontend: cd frontend && npm run dev")

if __name__ == "__main__":
    main()