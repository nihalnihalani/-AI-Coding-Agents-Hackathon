#!/bin/bash

# Simple startup script for AI Agent

echo "🚀 Starting AI Agent..."

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed"
    exit 1
fi

# Check Node
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed"
    exit 1
fi

# Install backend dependencies if needed
if [ ! -d "backend/venv" ]; then
    echo "📦 Setting up Python environment..."
    cd backend
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    cd ..
fi

# Install frontend dependencies if needed
if [ ! -d "frontend/node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    cd frontend
    npm install
    cd ..
fi

# Start services
echo "🔧 Starting backend server..."
cd backend
source venv/bin/activate
python main.py &
BACKEND_PID=$!
cd ..

echo "🎨 Starting frontend..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo "✅ AI Agent is running!"
echo "   Backend: http://localhost:8000"
echo "   Frontend: http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop..."

# Handle shutdown
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT

# Wait
wait