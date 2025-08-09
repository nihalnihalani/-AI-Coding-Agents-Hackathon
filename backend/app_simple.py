from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Import calendar service
try:
    from app.services.calendar_service import calendar_service, MeetingRequest, AvailabilityCheck
    CALENDAR_SERVICE_AVAILABLE = True
except ImportError:
    CALENDAR_SERVICE_AVAILABLE = False

# Import LLM service
try:
    from app.services.llm_service import LLMRouter
    LLM_SERVICE_AVAILABLE = True
except ImportError:
    LLM_SERVICE_AVAILABLE = False

app = FastAPI(
    title="Aura Onboarding Agent",
    description="An autonomous, multi-modal onboarding agent",
    version="1.0.0",
    debug=True
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Aura Onboarding Agent API", "status": "running"}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "service": "aura-onboarding-agent",
        "version": "1.0.0",
        "environment": "development"
    }

@app.get("/docs")
async def get_docs():
    return {"message": "API documentation available at /docs"}

from pydantic import BaseModel

class LoginRequest(BaseModel):
    email: str
    password: str

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

class ChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None

# Demo users for testing
DEMO_USERS = {
    "demo@aura.ai": {"password": "demo123", "name": "Demo User", "role": "employee", "id": 1},
    "manager@aura.ai": {"password": "manager123", "name": "Manager User", "role": "manager", "id": 2},
    "admin@aura.ai": {"password": "admin123", "name": "Admin User", "role": "admin", "id": 3}
}

@app.post("/api/auth/login")
async def login(request: LoginRequest):
    user = DEMO_USERS.get(request.email)
    
    if not user or user["password"] != request.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    return {
        "access_token": f"demo_token_{user['id']}",
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "email": request.email,
            "name": user["name"],
            "role": user["role"]
        }
    }

# Additional auth endpoints to match frontend expectations
@app.get("/api/auth/me")
async def get_current_user_api():
    return {
        "id": 1,
        "email": "demo@aura.ai",
        "name": "Demo User",
        "role": "employee"
    }

@app.get("/api/health")
async def health_check_api():
    return {
        "status": "healthy", 
        "service": "aura-onboarding-agent",
        "version": "1.0.0",
        "environment": "development"
    }

@app.get("/api/chat/stream")
async def chat_stream():
    return {"message": "WebSocket endpoint for chat"}

@app.post("/api/onboarding/upload")
async def upload_document():
    return {"message": "Document uploaded successfully"}

# Dashboard endpoints
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
                "timestamp": "2025-08-02T15:30:00Z",
                "description": "Completed onboarding process"
            }
        ]
    }

# Onboarding endpoints
@app.get("/api/onboarding/progress/{session_id}")
async def get_onboarding_progress(session_id: str):
    return {
        "session_id": session_id,
        "progress": 65,
        "current_step": "Setting up development environment",
        "completed_tasks": 7,
        "total_tasks": 12,
        "estimated_completion": "2025-08-05T10:00:00Z"
    }

@app.get("/api/onboarding/plan/{session_id}")
async def get_onboarding_plan(session_id: str):
    return {
        "session_id": session_id,
        "plan": {
            "title": "Software Engineer Onboarding Plan",
            "description": "Comprehensive onboarding for new software engineers",
            "tasks": [
                {
                    "id": "1",
                    "title": "Complete HR paperwork",
                    "description": "Fill out necessary forms and documentation",
                    "status": "completed",
                    "estimated_hours": 2
                },
                {
                    "id": "2",
                    "title": "Set up development environment",
                    "description": "Install required tools and access systems",
                    "status": "in_progress",
                    "estimated_hours": 4
                }
            ]
        }
    }

# Chat endpoints
@app.get("/api/chat/history/{session_id}")
async def get_chat_history(session_id: str, limit: int = 100):
    return {
        "session_id": session_id,
        "messages": [
            {
                "id": 1,
                "content": "Hello! I'm Aura, your onboarding assistant. How can I help you today?",
                "type": "text",
                "timestamp": "2025-08-02T15:30:00Z",
                "sender": "assistant"
            }
        ]
    }

@app.get("/api/chat/suggestions/{session_id}")
async def get_chat_suggestions(session_id: str):
    return {
        "suggestions": [
            "Tell me about my onboarding plan",
            "What's my next task?",
            "How do I set up my development environment?",
            "Who should I contact for help?"
        ]
    }

@app.post("/api/chat/text")
async def send_chat_message():
    return {
        "message": "Thanks for your message! I'm here to help with your onboarding.",
        "type": "text",
        "timestamp": "2025-08-02T15:30:00Z"
    }

@app.post("/api/chat/message")
async def chat_with_llm(request: ChatMessage):
    """Chat with the AI agent using LLM."""
    try:
        if LLM_SERVICE_AVAILABLE:
            # Initialize LLM router
            llm_router = LLMRouter()
            
            # Create a context-aware prompt
            system_prompt = """You are Aura, an AI onboarding assistant. You help new employees with their onboarding process. 
            You can help with:
            - Scheduling meetings and checking calendar availability
            - Explaining onboarding tasks and processes
            - Answering questions about company policies
            - Providing guidance on setting up development environments
            - Coordinating with managers and team members
            
            Be helpful, professional, and concise. If you need to schedule something, mention that you can help with calendar integration."""
            
            # Combine system prompt with user message
            full_prompt = f"{system_prompt}\n\nUser: {request.message}\n\nAura:"
            
            # Generate response using LLM
            result = await llm_router.generate_response(
                task_type="conversation",
                prompt=full_prompt,
                requirements={"max_tokens": 500}
            )
            
            if result["success"]:
                return {
                    "message": result["response"],
                    "type": "text",
                    "timestamp": datetime.utcnow().isoformat(),
                    "session_id": request.session_id,
                    "llm_used": result["llm_used"],
                    "success": True
                }
            else:
                # Fallback response
                return {
                    "message": "I'm here to help with your onboarding! How can I assist you today?",
                    "type": "text",
                    "timestamp": datetime.utcnow().isoformat(),
                    "session_id": request.session_id,
                    "llm_used": "fallback",
                    "success": False
                }
        else:
            # Demo response when LLM is not available
            demo_responses = [
                "Welcome to Aura! I'm here to help with your onboarding process. How can I assist you today?",
                "I can help you schedule meetings, explain onboarding tasks, and answer any questions you have.",
                "Let me know if you need help with setting up your development environment or meeting your team.",
                "I'm ready to help coordinate your onboarding activities and ensure a smooth transition."
            ]
            
            import random
            return {
                "message": random.choice(demo_responses),
                "type": "text",
                "timestamp": datetime.utcnow().isoformat(),
                "session_id": request.session_id,
                "llm_used": "demo",
                "success": True
            }
            
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return {
            "message": "I apologize, but I'm having trouble processing your request right now. Please try again.",
            "type": "text",
            "timestamp": datetime.utcnow().isoformat(),
            "session_id": request.session_id,
            "llm_used": "error",
            "success": False,
            "error": str(e)
        }

# Settings endpoints
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
        "timezone": "UTC",
        "profile": {
            "firstName": "Demo",
            "lastName": "User",
            "department": "Engineering",
            "role": "Software Engineer"
        }
    }

@app.put("/api/settings/user")
async def update_user_settings():
    return {"message": "Settings updated successfully"}

# Calendar endpoints
@app.get("/api/calendar/events")
async def get_calendar_events(days: int = 7):
    """Get calendar events for the next N days."""
    if CALENDAR_SERVICE_AVAILABLE:
        return await calendar_service.get_events(days)
    else:
        # Fallback demo implementation
        now = datetime.utcnow()
        events = []
        
        for i in range(min(days, 5)):
            event_date = now + timedelta(days=i)
            events.append({
                "id": f"event_{i}",
                "title": f"Onboarding Meeting {i+1}",
                "description": f"Onboarding session for new employee",
                "start_time": event_date.replace(hour=10, minute=0).isoformat(),
                "end_time": event_date.replace(hour=11, minute=0).isoformat(),
                "location": "Conference Room A",
                "attendees": ["demo@aura.ai", "manager@aura.ai"],
                "meet_link": f"https://meet.google.com/demo-{i}",
                "status": "confirmed"
            })
        
        return {
            "events": events,
            "total_count": len(events),
            "query_range": {
                "start": now.isoformat(),
                "end": (now + timedelta(days=days)).isoformat()
            }
        }

@app.post("/api/calendar/schedule")
async def schedule_meeting(request: MeetingRequest):
    """Schedule a new meeting."""
    try:
        if CALENDAR_SERVICE_AVAILABLE:
            return await calendar_service.schedule_meeting(request)
        else:
            # Fallback demo implementation
            start_datetime = datetime.fromisoformat(request.start_time.replace('Z', '+00:00'))
            end_datetime = start_datetime + timedelta(minutes=request.duration)
            event_id = f"meeting_{int(datetime.now().timestamp())}"
            
            return {
                "success": True,
                "event_id": event_id,
                "title": request.title,
                "start_time": start_datetime.isoformat(),
                "end_time": end_datetime.isoformat(),
                "attendees": request.attendees,
                "meet_link": f"https://meet.google.com/{event_id}",
                "calendar_link": f"https://calendar.google.com/event?eid={event_id}",
                "message": "Meeting scheduled successfully"
            }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error scheduling meeting: {str(e)}")

@app.get("/api/calendar/availability")
async def check_availability(start_time: str, end_time: str, attendees: Optional[str] = None):
    """Check availability for a time slot."""
    try:
        attendee_list = attendees.split(',') if attendees else []
        
        if CALENDAR_SERVICE_AVAILABLE:
            check = AvailabilityCheck(
                start_time=start_time,
                end_time=end_time,
                attendees=attendee_list
            )
            return await calendar_service.check_availability(check)
        else:
            # Fallback demo implementation
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            
            is_available = True
            conflict_reason = None
            
            # Check if it's during business hours (9 AM - 5 PM)
            if start_dt.hour < 9 or end_dt.hour > 17:
                is_available = False
                conflict_reason = "Outside business hours"
            
            # Check if it's on a weekend
            if start_dt.weekday() >= 5:
                is_available = False
                conflict_reason = "Weekend"
            
            return {
                "available": is_available,
                "conflict_reason": conflict_reason,
                "time_slot": {
                    "start": start_dt.isoformat(),
                    "end": end_dt.isoformat()
                },
                "attendees": attendee_list
            }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error checking availability: {str(e)}")

@app.get("/api/calendar/suggestions")
async def get_meeting_suggestions(duration: int = 60, days_ahead: int = 7, attendees: Optional[str] = None):
    """Get meeting time suggestions."""
    try:
        attendee_list = attendees.split(',') if attendees else None
        
        if CALENDAR_SERVICE_AVAILABLE:
            return await calendar_service.get_meeting_suggestions(duration, days_ahead, attendee_list)
        else:
            # Fallback demo implementation
            now = datetime.utcnow()
            suggestions = []
            
            for day_offset in range(days_ahead):
                check_date = now.date() + timedelta(days=day_offset)
                
                # Skip weekends
                if check_date.weekday() >= 5:
                    continue
                
                # Generate suggestions for business hours
                for hour in range(9, 17):
                    slot_start = datetime.combine(check_date, datetime.min.time().replace(hour=hour))
                    slot_end = slot_start + timedelta(minutes=duration)
                    
                    suggestions.append({
                        "start_time": slot_start.isoformat(),
                        "end_time": slot_end.isoformat(),
                        "confidence": 0.9,
                        "reason": "Business hours, no conflicts detected"
                    })
                    
                    if len(suggestions) >= 5:
                        break
                
                if len(suggestions) >= 5:
                    break
            
            return {
                "suggestions": suggestions,
                "duration_minutes": duration,
                "attendees": attendee_list or [],
                "search_criteria": {
                    "days_ahead": days_ahead,
                    "business_hours": [9, 17]
                }
            }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error getting suggestions: {str(e)}")

@app.delete("/api/calendar/events/{event_id}")
async def cancel_event(event_id: str):
    """Cancel a calendar event."""
    try:
        if CALENDAR_SERVICE_AVAILABLE:
            return await calendar_service.cancel_event(event_id)
        else:
            return {
                "success": True,
                "event_id": event_id,
                "message": "Event canceled successfully (Demo Mode)"
            }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error canceling event: {str(e)}")

@app.put("/api/calendar/events/{event_id}")
async def update_event(event_id: str, event: CalendarEvent):
    """Update a calendar event."""
    return {
        "success": True,
        "event_id": event_id,
        "title": event.title,
        "start_time": event.start_time,
        "end_time": event.end_time,
        "message": "Event updated successfully"
    }

@app.get("/api/calendar/status")
async def get_calendar_status():
    """Get calendar service status."""
    if CALENDAR_SERVICE_AVAILABLE:
        return calendar_service.get_status()
    else:
        return {
            "available": True,
            "demo_mode": True,
            "google_calendar_available": False,
            "credentials_configured": False,
            "service_initialized": False,
            "message": "Calendar service running in demo mode"
        }

@app.get("/api/llm/status")
async def get_llm_status():
    """Get LLM service status."""
    if LLM_SERVICE_AVAILABLE:
        try:
            llm_router = LLMRouter()
            gemini_available = llm_router.gemini_service.is_available()
            claude_available = llm_router.claude_service.is_available()
            
            return {
                "available": gemini_available or claude_available,
                "gemini_available": gemini_available,
                "claude_available": claude_available,
                "service_initialized": True,
                "message": "LLM service is available"
            }
        except Exception as e:
            return {
                "available": False,
                "gemini_available": False,
                "claude_available": False,
                "service_initialized": False,
                "error": str(e),
                "message": "LLM service error"
            }
    else:
        return {
            "available": False,
            "gemini_available": False,
            "claude_available": False,
            "service_initialized": False,
            "message": "LLM service not available"
        }

# Approvals endpoints
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
                "description": "Request access to GitHub repository",
                "requester": "Demo User",
                "timestamp": "2025-08-02T14:30:00Z",
                "risk_level": "low"
            }
        ]
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)