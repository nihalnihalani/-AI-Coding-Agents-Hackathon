# AI Agent - Intelligent Onboarding Assistant

A modern AI-powered onboarding assistant with voice capabilities, calendar integration, and multi-modal interactions.

## Features

- AI-powered chat interface (Gemini/Claude)
- Voice interaction support
- Calendar integration
- Authentication system
- Dashboard analytics
- Real-time WebSocket communication

## Quick Start

### Prerequisites

- Python 3.8+
- Node.js 16+

### Installation & Run

```bash
# Clone the repository
git clone <repo-url>
cd ai_agent

# Run the application
./run.sh
```

The application will be available at:
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Manual Setup

If you prefer to set up manually:

```bash
# Backend
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

## Configuration

### Environment Variables

Create `.env` files in both `backend/` and `frontend/` directories:

**backend/.env**
```
GEMINI_API_KEY=your_gemini_key
CLAUDE_API_KEY=your_claude_key
GOOGLE_CALENDAR_CREDENTIALS=path_to_credentials.json
VAPI_API_KEY=your_vapi_key
SECRET_KEY=your_secret_key
```

**frontend/.env**
```
VITE_API_URL=http://localhost:8000
```

## Project Structure

```
ai_agent/
├── backend/          # FastAPI backend
│   ├── app/         # Application code
│   │   ├── agents/  # AI agent logic
│   │   ├── api/     # API endpoints
│   │   ├── core/    # Core utilities
│   │   ├── models/  # Data models
│   │   ├── services/# Business logic
│   │   └── tools/   # Integration tools
│   ├── main.py      # Entry point
│   └── requirements.txt
├── frontend/        # React frontend
│   ├── src/
│   │   ├── components/
│   │   ├── contexts/
│   │   ├── pages/
│   │   └── types/
│   └── package.json
└── run.sh          # Startup script
```

## API Endpoints

Key endpoints:
- `POST /api/auth/login` - User authentication
- `GET /api/chat/history/{session_id}` - Chat history
- `POST /api/chat/message` - Send chat message
- `GET /api/calendar/events` - Calendar events
- `POST /api/calendar/schedule` - Schedule meeting
- `GET /api/dashboard/stats` - Dashboard statistics

## Development

```bash
# Run tests
cd backend && pytest
cd frontend && npm test

# Linting
cd backend && pylint app/
cd frontend && npm run lint

# Build for production
cd frontend && npm run build
```

## License

MIT