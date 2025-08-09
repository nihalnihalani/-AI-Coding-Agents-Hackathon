#!/bin/bash

# Aura Onboarding Agent - Full Stack Startup Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if a port is in use
port_in_use() {
    lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null
}

# Function to start backend
start_backend() {
    print_status "Starting backend server..."
    
    cd backend
    
    # Check if Python is available
    if ! command_exists python3; then
        print_error "Python 3 is not installed"
        exit 1
    fi
    
    # Check if pip is available
    if ! command_exists pip3; then
        print_error "pip3 is not installed"
        exit 1
    fi
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        print_status "Creating Python virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Install dependencies
    print_status "Installing Python dependencies..."
    pip install -r requirements.txt
    
    # Check Redis (optional)
    if command_exists redis-cli; then
        if redis-cli ping >/dev/null 2>&1; then
            print_success "Redis is running"
        else
            print_warning "Redis is not running - some features may be limited"
        fi
    else
        print_warning "Redis is not installed - some features may be limited"
    fi
    
    # Start the backend server
    print_status "Starting FastAPI server on http://localhost:8000"
    python start.py &
    BACKEND_PID=$!
    
    cd ..
}

# Function to start frontend
start_frontend() {
    print_status "Starting frontend development server..."
    
    cd frontend
    
    # Check if Node.js is available
    if ! command_exists node; then
        print_error "Node.js is not installed"
        print_status "Please install Node.js from https://nodejs.org/"
        exit 1
    fi
    
    # Check if npm is available
    if ! command_exists npm; then
        print_error "npm is not installed"
        exit 1
    fi
    
    # Install dependencies
    print_status "Installing Node.js dependencies..."
    npm install
    
    # Start the frontend server
    print_status "Starting Vite development server on http://localhost:3000"
    npm run dev &
    FRONTEND_PID=$!
    
    cd ..
}

# Function to cleanup on exit
cleanup() {
    print_status "Shutting down servers..."
    
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi
    
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
    fi
    
    # Kill any remaining processes on our ports
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    lsof -ti:3000 | xargs kill -9 2>/dev/null || true
    
    print_success "Cleanup complete"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Main execution
main() {
    echo "🤖 Aura Onboarding Agent - Full Stack Startup"
    echo "=============================================="
    
    # Check prerequisites
    print_status "Checking prerequisites..."
    
    # Check if ports are available
    if port_in_use 8000; then
        print_error "Port 8000 is already in use"
        exit 1
    fi
    
    if port_in_use 3000; then
        print_error "Port 3000 is already in use"
        exit 1
    fi
    
    # Start services
    start_backend
    sleep 3  # Give backend time to start
    
    start_frontend
    sleep 2  # Give frontend time to start
    
    print_success "🎉 Aura Onboarding Agent is now running!"
    echo ""
    echo "📍 Application URLs:"
    echo "   🌐 Frontend:  http://localhost:3000"
    echo "   🔧 Backend:   http://localhost:8000"
    echo "   📖 API Docs:  http://localhost:8000/docs"
    echo ""
    echo "👤 Demo Accounts:"
    echo "   📧 Employee:  demo@aura.ai     (password: demo123)"
    echo "   👔 Manager:   manager@aura.ai  (password: manager123)"
    echo "   🔑 Admin:     admin@aura.ai    (password: admin123)"
    echo ""
    echo "🔄 Press Ctrl+C to stop all servers"
    echo "=============================================="
    
    # Wait for user interrupt
    wait
}

# Run main function
main