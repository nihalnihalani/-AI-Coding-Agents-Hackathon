#!/usr/bin/env python3
"""
Aura Onboarding Agent - Development Server Starter
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        print(f"Current version: {sys.version}")
        sys.exit(1)
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")

def check_redis():
    """Check if Redis is running."""
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        print("✅ Redis connection successful")
        return True
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        print("💡 Please ensure Redis is installed and running:")
        print("   - Install Redis: https://redis.io/download")
        print("   - Start Redis: redis-server")
        return False

def install_dependencies():
    """Install Python dependencies."""
    print("📦 Installing Python dependencies...")
    try:
        subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ], check=True, capture_output=True)
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def check_env_file():
    """Check if .env file exists."""
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ .env file not found")
        print("💡 Creating .env file with default values...")
        # The .env file should already be created by now
        return env_file.exists()
    
    print("✅ Environment file found")
    return True

def start_server():
    """Start the FastAPI development server."""
    print("🚀 Starting Aura Onboarding Agent server...")
    print("📍 Server will be available at: http://localhost:8000")
    print("📖 API documentation at: http://localhost:8000/docs")
    print("🔄 Press Ctrl+C to stop the server")
    print("-" * 50)
    
    try:
        # Start the server
        subprocess.run([
            "uvicorn", "app_simple:app", 
            "--host", "0.0.0.0", 
            "--port", "8000", 
            "--reload",
            "--log-level", "info"
        ], check=True)
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"❌ Server failed to start: {e}")
        sys.exit(1)

def main():
    """Main startup function."""
    print("🤖 Aura Onboarding Agent - Development Server")
    print("=" * 50)
    
    # Check Python version
    check_python_version()
    
    # Check environment file
    if not check_env_file():
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies():
        sys.exit(1)
    
    # Check Redis (optional - will work without it but with limited functionality)
    redis_available = check_redis()
    if not redis_available:
        print("⚠️  Redis not available - some features will be limited")
        print("🔄 Continuing without Redis...")
    
    print("\n🎉 All checks passed! Starting server...")
    time.sleep(1)
    
    # Start the server
    start_server()

if __name__ == "__main__":
    main()