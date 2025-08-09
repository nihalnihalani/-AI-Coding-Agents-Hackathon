from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create app
app = FastAPI(
    title="AI Agent API",
    description="AI-powered onboarding assistant",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class LoginRequest(BaseModel):
    email: str
    password: str

class ChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None

class CalendarEvent(BaseModel):
    title: str
    description: Optional[str] = None
    start_time: str
    end_time: str
    attendees: List[str] = []
    location: Optional[str] = None

class MeetingRequest(BaseModel):
    title: str
    description: Optional[str] = None
    start_time: str
    duration: int = 60
    attendees: List[str] = []
    location: Optional[str] = None

# Demo users
DEMO_USERS = {
    "demo@aura.ai": {"password": "demo123", "name": "Demo User", "role": "employee", "id": 1},
    "manager@aura.ai": {"password": "manager123", "name": "Manager User", "role": "manager", "id": 2},
    "admin@aura.ai": {"password": "admin123", "name": "Admin User", "role": "admin", "id": 3}
}

# Routes
@app.get("/")
async def root():
    return {"message": "AI Agent API", "status": "running"}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "ai-agent",
        "version": "1.0.0",
        "environment": "development"
    }

@app.post("/api/auth/login")
async def login(request: LoginRequest):
    user = DEMO_USERS.get(request.email)
    if not user or user["password"] != request.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    return {
        "access_token": f"demo_token_{user['id']}",
        "token_type": "bearer",
        "user_info": {
            "user_id": str(user["id"]),
            "email": request.email,
            "full_name": user["name"],
            "role": user["role"],
            "permissions": ["*"] if user["role"] == "admin" else [f"{user['role']}:*"],
            "is_active": True
        }
    }

@app.get("/api/auth/me")
async def get_current_user():
    return {
        "user_id": "1",
        "email": "demo@aura.ai",
        "full_name": "Demo User",
        "role": "employee",
        "permissions": ["employee:*"],
        "is_active": True
    }

@app.post("/api/chat/message")
async def chat_message(request: ChatMessage):
    # Simple echo response for now
    responses = [
        "Hello! I'm your AI assistant. How can I help you today?",
        "I can help you with onboarding tasks, scheduling meetings, and answering questions.",
        "Let me assist you with that request.",
        "I understand. Let me help you with that."
    ]
    
    import random
    return {
        "message": random.choice(responses),
        "type": "text",
        "timestamp": datetime.utcnow().isoformat(),
        "session_id": request.session_id,
        "success": True
    }

@app.get("/api/chat/history/{session_id}")
async def get_chat_history(session_id: str):
    return {
        "session_id": session_id,
        "messages": [
            {
                "id": 1,
                "content": "Welcome! I'm your AI onboarding assistant.",
                "type": "text",
                "timestamp": datetime.utcnow().isoformat(),
                "sender": "assistant"
            }
        ]
    }

@app.get("/api/dashboard/stats")
async def get_dashboard_stats():
    return {
        "totalUsers": 156,
        "activeOnboarding": 23,
        "completedOnboarding": 133,
        "pendingApprovals": 7,
        "avgCompletionTime": "4.2 days",
        "satisfactionScore": 4.7
    }

@app.get("/api/dashboard/activity")
async def get_dashboard_activity():
    return {
        "activities": [
            {
                "id": 1,
                "type": "onboarding_completed",
                "user": "John Doe",
                "timestamp": datetime.utcnow().isoformat(),
                "description": "Completed onboarding process"
            }
        ]
    }

@app.get("/api/calendar/events")
async def get_calendar_events(days: int = 7):
    now = datetime.utcnow()
    events = []
    
    for i in range(min(days, 3)):
        event_date = now + timedelta(days=i)
        events.append({
            "id": f"event_{i}",
            "title": f"Onboarding Meeting {i+1}",
            "description": "Onboarding session",
            "start_time": event_date.replace(hour=10, minute=0).isoformat(),
            "end_time": event_date.replace(hour=11, minute=0).isoformat(),
            "location": "Conference Room A",
            "attendees": ["demo@aura.ai", "manager@aura.ai"],
            "status": "confirmed"
        })
    
    return {
        "events": events,
        "total_count": len(events)
    }

@app.post("/api/calendar/schedule")
async def schedule_meeting(request: MeetingRequest):
    return {
        "success": True,
        "event_id": f"meeting_{datetime.now().timestamp()}",
        "title": request.title,
        "start_time": request.start_time,
        "message": "Meeting scheduled successfully"
    }

@app.get("/api/onboarding/progress/{session_id}")
async def get_onboarding_progress(session_id: str):
    return {
        "session_id": session_id,
        "progress": 65,
        "current_step": "Setting up development environment",
        "completed_tasks": 7,
        "total_tasks": 12
    }

@app.get("/api/onboarding/plan/{session_id}")
async def get_onboarding_plan(session_id: str):
    return {
        "session_id": session_id,
        "plan": {
            "title": "Software Engineer Onboarding",
            "tasks": [
                {
                    "id": "1",
                    "title": "Complete HR paperwork",
                    "status": "completed"
                },
                {
                    "id": "2",
                    "title": "Set up development environment",
                    "status": "in_progress"
                }
            ]
        }
    }

@app.get("/api/approvals")
async def get_approvals():
    return {"approvals": []}

@app.get("/api/approvals/pending")
async def get_pending_approvals():
    return {
        "pending": [
            {
                "id": "1",
                "type": "system_access",
                "description": "Request access to GitHub",
                "requester": "Demo User",
                "timestamp": datetime.utcnow().isoformat()
            }
        ]
    }

@app.get("/api/settings/user")
async def get_user_settings():
    return {
        "notifications": {
            "email": True,
            "push": True,
            "sms": False
        },
        "theme": "light",
        "language": "en",
        "timezone": "UTC"
    }

@app.put("/api/settings/user")
async def update_user_settings():
    return {"message": "Settings updated successfully"}

# WebSocket endpoint stub
@app.get("/api/chat/stream")
async def chat_stream():
    return {"message": "WebSocket endpoint for chat"}

@app.post("/api/onboarding/upload")
async def upload_document():
    return {"message": "Document uploaded successfully"}

@app.get("/api/chat/suggestions/{session_id}")
async def get_chat_suggestions(session_id: str):
    return {
        "suggestions": [
            "Tell me about my onboarding plan",
            "What's my next task?",
            "How do I set up my environment?",
            "Who should I contact for help?"
        ]
    }

@app.post("/api/chat/text")
async def chat_text():
    return {
        "message": "Thanks for your message!",
        "type": "text",
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)