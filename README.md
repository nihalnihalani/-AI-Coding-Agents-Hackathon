# 🤖 Aura Onboarding Agent

An autonomous, multi-modal AI onboarding assistant powered by Gemini 2.5 Pro and Claude, featuring real-time chat, voice integration, and intelligent workflow automation.

## ✨ Features

- 🧠 **Multi-LLM Intelligence**: Gemini 2.5 Pro for document analysis, Claude for conversations
- 💬 **Real-time Chat**: WebSocket-powered conversations with AI assistant
- 🎤 **Voice Integration**: Vapi AI for voice interactions
- 📋 **Smart Onboarding**: AI-generated personalized onboarding plans
- ✅ **Approval Workflows**: Human-in-the-loop approval system
- 🔗 **Tool Integration**: Calendar, Slack, GitHub automation
- 🔐 **Role-based Access**: Employee, Manager, Admin permissions
- 📱 **Responsive Design**: Works on desktop and mobile

## 🚀 Quick Start

### Prerequisites

- **Python 3.8+** (for backend)
- **Node.js 16+** (for frontend)
- **Redis** (optional, for full functionality)

### Option 1: One-Click Startup (Recommended)

```bash
# Clone or navigate to the project directory
cd "onboarding agent loop"

# Run the full-stack application
./start.sh
```

This will automatically:
- Install all dependencies
- Start the backend server on http://localhost:8000
- Start the frontend on http://localhost:3000
- Display demo account credentials

### Option 2: Manual Setup

#### Backend Setup

```bash
cd backend

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the server
python start.py
```

#### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

## 🔑 Demo Accounts

| Role | Email | Password | Permissions |
|------|-------|----------|-------------|
| Employee | `demo@aura.ai` | `demo123` | Basic onboarding access |
| Manager | `manager@aura.ai` | `manager123` | Approval management |
| Admin | `admin@aura.ai` | `admin123` | Full system access |

## 🌐 Application URLs

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **WebSocket**: ws://localhost:8000/chat/stream

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   React Frontend │────│   FastAPI Backend │────│  External APIs  │
│                 │    │                  │    │                 │
│ • TypeScript    │    │ • LangGraph      │    │ • Gemini 2.5    │
│ • Tailwind CSS  │    │ • Multi-LLM      │    │ • Claude        │
│ • WebSocket     │    │ • Redis State    │    │ • Vapi AI       │
│ • Real-time UI  │    │ • JWT Auth       │    │ • Calendar API  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 📁 Project Structure

```
onboarding-agent-loop/
├── backend/                 # FastAPI Python backend
│   ├── app/
│   │   ├── agents/         # LangGraph AI agents
│   │   ├── api/            # REST API endpoints
│   │   ├── core/           # Core utilities (auth, config)
│   │   ├── models/         # Pydantic models
│   │   ├── services/       # Business logic services
│   │   └── tools/          # External tool integrations
│   ├── tests/              # Backend tests
│   └── requirements.txt    # Python dependencies
├── frontend/               # React TypeScript frontend
│   ├── src/
│   │   ├── components/     # Reusable UI components
│   │   ├── contexts/       # React contexts (auth, websocket)
│   │   ├── pages/          # Application pages
│   │   ├── lib/            # Utilities and API client
│   │   └── types/          # TypeScript type definitions
│   └── package.json        # Node.js dependencies
└── docs/                   # Documentation
```

## 🔧 Configuration

### Environment Variables

#### Backend (.env)
```env
# Security
JWT_SECRET_KEY=your-secret-key
JWT_EXPIRE_MINUTES=30

# AI APIs
GEMINI_API_KEY=your-gemini-key
ANTHROPIC_API_KEY=your-claude-key

# External Services
SLACK_BOT_TOKEN=your-slack-token
GITHUB_TOKEN=your-github-token
VAPI_API_KEY=your-vapi-key

# Database
REDIS_URL=redis://localhost:6379/0
```

#### Frontend (.env)
```env
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_BASE_URL=ws://localhost:8000
```

## 🧪 Testing

### Backend Tests
```bash
cd backend
pytest tests/
```

### Frontend Tests
```bash
cd frontend
npm test
```

## 📊 Key Components

### Backend Services
- **LangGraph Agent**: Multi-step AI workflow orchestration
- **Multi-LLM Service**: Intelligent routing between AI models
- **WebSocket Manager**: Real-time communication
- **State Service**: Redis-based persistence
- **Tool Registry**: External API integrations

### Frontend Features
- **Authentication**: JWT-based with role permissions
- **Real-time Chat**: WebSocket integration
- **Dashboard**: Progress tracking and analytics
- **Onboarding**: File upload and plan generation
- **Approvals**: Manager workflow interface

## 🔒 Security Features

- JWT authentication with automatic refresh
- Role-based access control (RBAC)
- API rate limiting
- Input validation and sanitization
- CORS configuration
- Secure WebSocket connections

## 🚦 Development

### Backend Development
```bash
cd backend
# Auto-reload on changes
uvicorn app:app --reload

# Run tests
pytest tests/ -v

# Code formatting
black app/
isort app/
```

### Frontend Development
```bash
cd frontend
# Development server
npm run dev

# Type checking
npm run type-check

# Build for production
npm run build
```

## 📈 Production Deployment

### Docker Deployment (Recommended)
```bash
# Build and run with Docker Compose
docker-compose up -d

# Scale services
docker-compose up -d --scale backend=3
```

### Manual Deployment
1. Set production environment variables
2. Build frontend: `npm run build`
3. Deploy backend with gunicorn: `gunicorn app:app -w 4 -k uvicorn.workers.UvicornWorker`
4. Serve frontend with nginx or CDN
5. Set up Redis cluster for production

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details

## 🆘 Troubleshooting

### Common Issues

**Port Already in Use**
```bash
# Kill processes on ports 3000 and 8000
lsof -ti:3000,8000 | xargs kill -9
```

**Redis Connection Failed**
```bash
# Install Redis (macOS)
brew install redis
brew services start redis

# Install Redis (Ubuntu)
sudo apt install redis-server
sudo systemctl start redis
```

**Python Dependencies**
```bash
# Upgrade pip
python -m pip install --upgrade pip

# Clear pip cache
pip cache purge
```

**Node.js Dependencies**
```bash
# Clear npm cache
npm cache clean --force

# Delete node_modules and reinstall
rm -rf node_modules package-lock.json
npm install
```

### Getting Help

- 📖 Check the [API Documentation](http://localhost:8000/docs)
- 🔍 Search existing issues
- 💬 Open a new issue with details
- 📧 Contact support

## 🎯 Features Roadmap

- [ ] Mobile app (React Native)
- [ ] Advanced analytics dashboard
- [ ] Multi-tenant support
- [ ] SSO integration
- [ ] Advanced workflow automation
- [ ] Performance monitoring
- [ ] Audit logging

---

**Built with ❤️ by Claude Code**

*Powered by Gemini 2.5 Pro, Claude, and the latest AI technologies*