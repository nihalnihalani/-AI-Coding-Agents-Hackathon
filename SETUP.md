# 🚀 Setup Instructions for Aura Onboarding Agent

## Prerequisites

- Python 3.8+ (3.9 recommended)
- Node.js 16+
- Conda (Miniconda or Anaconda)
- Redis (optional, for full functionality)
- Git

## Quick Setup with Conda

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd ai_agent
```

### 2. Set Up Backend (Python with Conda)

```bash
# Create conda environment
conda create -n ai_agent python=3.9 -y

# Activate the environment
conda activate ai_agent

# Navigate to backend
cd backend

# Copy environment file
cp .env.example .env

# Edit .env and add your API keys:
# - GEMINI_API_KEY=your_actual_gemini_key
# - ANTHROPIC_API_KEY=your_actual_anthropic_key
# - JWT_SECRET_KEY=generate_a_secure_32_char_key

# Install dependencies
pip install -r requirements.txt

# Go back to root
cd ..
```

### 3. Set Up Frontend (React/TypeScript)

```bash
# Navigate to frontend
cd frontend

# Copy environment file
cp .env.example .env

# Install dependencies
npm install

# Go back to root
cd ..
```

### 4. Run the Application

#### Option A: Run Both Servers Manually

```bash
# Terminal 1 - Backend
conda activate ai_agent
cd backend
python start.py
```

```bash
# Terminal 2 - Frontend
cd frontend
npm run dev
```

#### Option B: Use the Start Script

```bash
# Make sure you're in the conda environment
conda activate ai_agent

# Run the start script
./start.sh
```

## Access the Application

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## Demo Accounts

| Role | Email | Password |
|------|-------|----------|
| Employee | demo@aura.ai | demo123 |
| Manager | manager@aura.ai | manager123 |
| Admin | admin@aura.ai | admin123 |

## Configuration

### Required API Keys

1. **Gemini API Key**: Get from [Google AI Studio](https://makersuite.google.com/app/apikey)
2. **Anthropic API Key**: Get from [Anthropic Console](https://console.anthropic.com/)

### Optional Services

- **Redis**: For session management and caching
- **Vapi**: For voice integration
- **GitHub**: For repository integration
- **Slack**: For team notifications

## Troubleshooting

### Port Already in Use

```bash
# Kill processes on ports
lsof -ti:3000,8000 | xargs kill -9
```

### Redis Not Available

The app works without Redis but with limited features. To install:

```bash
# macOS
brew install redis
brew services start redis

# Ubuntu/Debian
sudo apt install redis-server
sudo systemctl start redis
```

### Module Not Found Errors

```bash
# Reinstall backend dependencies
conda activate ai_agent
cd backend
pip install -r requirements.txt

# Reinstall frontend dependencies
cd ../frontend
rm -rf node_modules package-lock.json
npm install
```

## Project Structure

```
ai_agent/
├── backend/                 # FastAPI Python backend
│   ├── app/                # Application code
│   ├── requirements.txt    # Python dependencies
│   ├── start.py            # Backend starter script
│   └── .env.example        # Environment template
├── frontend/               # React TypeScript frontend
│   ├── src/               # Source code
│   ├── package.json       # Node dependencies
│   └── .env.example       # Environment template
├── tests/                 # Test files
├── start.sh              # Full-stack starter script
└── README.md             # Project documentation
```

## Development

### Backend Development

```bash
conda activate ai_agent
cd backend
python start.py  # Auto-reloads on changes
```

### Frontend Development

```bash
cd frontend
npm run dev  # Hot module replacement enabled
```

### Running Tests

```bash
# Backend tests
cd backend
pytest tests/

# Frontend tests
cd frontend
npm test
```

## Security Notes

- Never commit `.env` files with real API keys
- Always use `.env.example` as a template
- Generate secure JWT secret keys for production
- Update CORS settings for production domains

## Support

For issues or questions, please check:
- API Documentation: http://localhost:8000/docs
- GitHub Issues: [Create an issue](https://github.com/your-repo/issues)

---

Built with ❤️ using FastAPI, React, LangGraph, and AI