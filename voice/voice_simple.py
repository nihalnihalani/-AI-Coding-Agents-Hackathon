#!/usr/bin/env python3
"""
Simplified Voice Navigator for AI Agent
Basic version with minimal dependencies for quick testing
"""

import os
import time
import webbrowser
from typing import Dict, Any

try:
    import pyautogui
    import requests
    from google import genai
    from google.genai import types
except ImportError as e:
    print(f"❌ Missing dependency: {e}")
    print("Run: pip install google-genai pyautogui requests")
    exit(1)

class SimpleVoiceNavigator:
    """Simplified voice navigator with text commands"""
    
    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            print("❌ Please set GEMINI_API_KEY environment variable")
            exit(1)
        
        self.client = genai.Client(api_key=self.api_key)
        self.base_url = "http://localhost:3000"
        
        # Set PyAutoGUI settings
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.5
    
    def navigate_to_page(self, page: str) -> bool:
        """Navigate to a specific page"""
        urls = {
            'dashboard': f'{self.base_url}/dashboard',
            'chat': f'{self.base_url}/chat', 
            'onboarding': f'{self.base_url}/onboarding',
            'approvals': f'{self.base_url}/approvals',
            'profile': f'{self.base_url}/profile',
            'settings': f'{self.base_url}/settings',
            'login': f'{self.base_url}/login',
            'home': self.base_url,
        }
        
        if page.lower() in urls:
            url = urls[page.lower()]
            print(f"🔗 Navigating to {page}: {url}")
            webbrowser.open(url)
            return True
        return False
    
    def click_at_position(self, x: int, y: int):
        """Click at specific coordinates"""
        print(f"🖱️ Clicking at ({x}, {y})")
        pyautogui.click(x, y)
    
    def type_text(self, text: str):
        """Type text"""
        print(f"⌨️ Typing: {text}")
        pyautogui.typewrite(text, interval=0.05)
    
    def scroll(self, direction: str, amount: int = 3):
        """Scroll page"""
        if direction.lower() == 'up':
            pyautogui.scroll(amount)
        elif direction.lower() == 'down':
            pyautogui.scroll(-amount)
        print(f"📜 Scrolled {direction}")
    
    def login_demo(self):
        """Quick login with demo credentials"""
        print("🔐 Logging in with demo credentials...")
        self.navigate_to_page('login')
        time.sleep(2)
        
        # Focus email field and type
        pyautogui.press('tab')  # Navigate to email field
        self.type_text('demo@aura.ai')
        
        # Navigate to password field
        pyautogui.press('tab')
        self.type_text('demo123')
        
        # Submit
        pyautogui.press('enter')
        print("✅ Login submitted")
    
    def process_command(self, command: str) -> str:
        """Process voice command using Gemini"""
        try:
            prompt = f"""
            You are a voice assistant for the AI Agent application. 
            Process this command and return a JSON response with the action to take:
            
            Command: "{command}"
            
            Available actions:
            - navigate: {{page: "dashboard|chat|onboarding|approvals|profile|settings|login"}}
            - click: {{x: number, y: number}} (screen coordinates)
            - type: {{text: "text to type"}}
            - scroll: {{direction: "up|down", amount: number}}
            - login: {{}} (quick demo login)
            - unknown: {{}} (if command is unclear)
            
            Return only valid JSON with one action.
            """
            
            response = self.client.models.generate_content(
                model='gemini-2.0-flash-001',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type='application/json',
                    temperature=0.1,
                )
            )
            
            return response.text
            
        except Exception as e:
            print(f"❌ Error processing command: {e}")
            return '{"unknown": {}}'
    
    def execute_action(self, action_json: str):
        """Execute the action from JSON response"""
        try:
            import json
            action = json.loads(action_json)
            
            if 'navigate' in action:
                page = action['navigate'].get('page')
                if page:
                    self.navigate_to_page(page)
                else:
                    print("❌ No page specified for navigation")
            
            elif 'click' in action:
                x = action['click'].get('x')
                y = action['click'].get('y')
                if x is not None and y is not None:
                    self.click_at_position(x, y)
                else:
                    print("❌ Invalid coordinates for click")
            
            elif 'type' in action:
                text = action['type'].get('text')
                if text:
                    self.type_text(text)
                else:
                    print("❌ No text specified for typing")
            
            elif 'scroll' in action:
                direction = action['scroll'].get('direction', 'down')
                amount = action['scroll'].get('amount', 3)
                self.scroll(direction, amount)
            
            elif 'login' in action:
                self.login_demo()
            
            elif 'unknown' in action:
                print("❓ Command not understood. Try:")
                print("  • 'go to dashboard'")
                print("  • 'open chat'")
                print("  • 'login'")
                print("  • 'scroll down'")
                print("  • 'type hello world'")
            
            else:
                print(f"❓ Unknown action: {action}")
                
        except json.JSONDecodeError:
            print(f"❌ Invalid JSON response: {action_json}")
        except Exception as e:
            print(f"❌ Error executing action: {e}")
    
    def check_app_status(self):
        """Check if AI Agent is running"""
        try:
            response = requests.get("http://localhost:8000/health", timeout=5)
            if response.status_code == 200:
                print("✅ AI Agent backend is running")
                return True
            else:
                print("⚠️ AI Agent backend responded with error")
                return False
        except requests.exceptions.RequestException:
            print("❌ AI Agent backend is not running")
            print("Please start it with: cd backend && python main.py")
            return False
    
    def run(self):
        """Main interaction loop"""
        print("🎙️ Simple Voice Navigator for AI Agent")
        print("=====================================")
        
        # Check if app is running
        if not self.check_app_status():
            print("Please start the AI Agent first.")
            return
        
        print("\n💡 Available commands:")
        print("  • Navigation: 'go to dashboard', 'open chat', 'show settings'")
        print("  • Login: 'login' (uses demo credentials)")
        print("  • Interaction: 'scroll down', 'type hello world'")
        print("  • Exit: 'quit' or 'exit'\n")
        
        while True:
            try:
                command = input("🎤 Enter voice command: ").strip()
                
                if command.lower() in ['quit', 'exit', 'q']:
                    print("👋 Goodbye!")
                    break
                
                if not command:
                    continue
                
                print(f"🧠 Processing: {command}")
                
                # Process command with Gemini
                action_json = self.process_command(command)
                print(f"📋 Action: {action_json}")
                
                # Execute the action
                self.execute_action(action_json)
                
                print()  # Add spacing
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")

def main():
    """Entry point"""
    navigator = SimpleVoiceNavigator()
    navigator.run()

if __name__ == "__main__":
    main()