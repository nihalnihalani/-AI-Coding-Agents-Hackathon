"""
Google Calendar Service for Aura Onboarding Agent
Provides calendar integration with proper error handling and demo functionality
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pydantic import BaseModel

# Google Calendar imports
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_CALENDAR_AVAILABLE = True
except ImportError:
    GOOGLE_CALENDAR_AVAILABLE = False
    logging.warning("Google Calendar dependencies not available")

from ..core.config import settings
from ..core.logging import get_logger

logger = get_logger(__name__)

class CalendarEvent(BaseModel):
    """Calendar event model."""
    id: Optional[str] = None
    title: str
    description: Optional[str] = None
    start_time: str
    end_time: str
    attendees: List[str] = []
    location: Optional[str] = None
    meet_link: Optional[str] = None
    status: str = "confirmed"

class MeetingRequest(BaseModel):
    """Meeting request model."""
    title: str
    description: Optional[str] = None
    start_time: str
    duration: int = 60
    attendees: List[str] = []
    location: Optional[str] = None

class AvailabilityCheck(BaseModel):
    """Availability check model."""
    start_time: str
    end_time: str
    attendees: List[str] = []

class CalendarService:
    """Google Calendar service with demo functionality."""
    
    def __init__(self):
        self.service = None
        self.credentials = None
        self.is_demo_mode = True  # Default to demo mode
        
        # Google Calendar API scopes
        self.scopes = [
            'https://www.googleapis.com/auth/calendar',
            'https://www.googleapis.com/auth/calendar.events'
        ]
        
        self._initialize_service()
    
    def _initialize_service(self):
        """Initialize Google Calendar service."""
        if not GOOGLE_CALENDAR_AVAILABLE:
            logger.warning("Google Calendar not available, using demo mode")
            self.is_demo_mode = True
            return
        
        try:
            if not settings.google_calendar_credentials_path:
                logger.warning("Google Calendar credentials not configured, using demo mode")
                self.is_demo_mode = True
                return
            
            # Load credentials
            self.credentials = self._load_credentials()
            
            if self.credentials and self.credentials.valid:
                self.service = build('calendar', 'v3', credentials=self.credentials)
                self.is_demo_mode = False
                logger.info("Google Calendar service initialized successfully")
            else:
                logger.warning("Google Calendar credentials are invalid, using demo mode")
                self.is_demo_mode = True
                
        except Exception as e:
            logger.error(f"Error initializing Google Calendar service: {e}")
            self.is_demo_mode = True
    
    def _load_credentials(self) -> Optional[Credentials]:
        """Load Google Calendar credentials."""
        if not GOOGLE_CALENDAR_AVAILABLE:
            return None
            
        try:
            credentials_path = settings.google_calendar_credentials_path
            if not credentials_path or not os.path.exists(credentials_path):
                return None
            
            token_path = credentials_path.replace('.json', '_token.json')
            
            creds = None
            
            # Load existing token
            if os.path.exists(token_path):
                creds = Credentials.from_authorized_user_file(token_path, self.scopes)
            
            # If no valid credentials, initiate OAuth flow
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        credentials_path, self.scopes
                    )
                    creds = flow.run_local_server(port=0)
                
                # Save credentials for next run
                with open(token_path, 'w') as token:
                    token.write(creds.to_json())
            
            return creds
            
        except Exception as e:
            logger.error(f"Error loading Google Calendar credentials: {e}")
            return None
    
    async def get_events(self, days: int = 7) -> Dict[str, Any]:
        """Get calendar events for the next N days."""
        try:
            if self.is_demo_mode:
                return self._get_demo_events(days)
            
            # Real Google Calendar implementation
            now = datetime.utcnow()
            time_min = now.isoformat() + 'Z'
            time_max = (now + timedelta(days=days)).isoformat() + 'Z'
            
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                maxResults=50,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            processed_events = []
            
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                processed_events.append({
                    "id": event['id'],
                    "title": event.get('summary', 'No Title'),
                    "description": event.get('description', ''),
                    "start_time": start,
                    "end_time": event['end'].get('dateTime', event['end'].get('date')),
                    "location": event.get('location', ''),
                    "attendees": [attendee.get('email') for attendee in event.get('attendees', [])],
                    "meet_link": event.get('hangoutLink'),
                    "status": event.get('status', 'confirmed')
                })
            
            return {
                "events": processed_events,
                "total_count": len(processed_events),
                "query_range": {
                    "start": time_min,
                    "end": time_max
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting events: {e}")
            return self._get_demo_events(days)
    
    def _get_demo_events(self, days: int) -> Dict[str, Any]:
        """Generate demo calendar events."""
        now = datetime.utcnow()
        events = []
        
        # Generate demo events
        for i in range(min(days, 5)):
            event_date = now + timedelta(days=i)
            events.append({
                "id": f"demo_event_{i}",
                "title": f"Onboarding Meeting {i+1}",
                "description": f"Onboarding session for new employee - Day {i+1}",
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
            },
            "demo_mode": True
        }
    
    async def schedule_meeting(self, request: MeetingRequest) -> Dict[str, Any]:
        """Schedule a new meeting."""
        try:
            # Parse start time
            start_datetime = datetime.fromisoformat(request.start_time.replace('Z', '+00:00'))
            end_datetime = start_datetime + timedelta(minutes=request.duration)
            
            if self.is_demo_mode:
                return self._schedule_demo_meeting(request, start_datetime, end_datetime)
            
            # Real Google Calendar implementation
            event = {
                'summary': request.title,
                'description': request.description,
                'location': request.location,
                'start': {
                    'dateTime': start_datetime.isoformat(),
                    'timeZone': 'UTC',
                },
                'end': {
                    'dateTime': end_datetime.isoformat(),
                    'timeZone': 'UTC',
                },
                'attendees': [{'email': email} for email in request.attendees],
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': 24 * 60},  # 1 day before
                        {'method': 'popup', 'minutes': 10},  # 10 minutes before
                    ],
                },
                'conferenceData': {
                    'createRequest': {
                        'requestId': f"meeting-{int(datetime.now().timestamp())}",
                        'conferenceSolutionKey': {'type': 'hangoutsMeet'}
                    }
                }
            }
            
            created_event = self.service.events().insert(
                calendarId='primary',
                body=event,
                conferenceDataVersion=1,
                sendUpdates='all'
            ).execute()
            
            return {
                "success": True,
                "event_id": created_event['id'],
                "title": request.title,
                "start_time": start_datetime.isoformat(),
                "end_time": end_datetime.isoformat(),
                "attendees": request.attendees,
                "meet_link": created_event.get('hangoutLink'),
                "calendar_link": created_event.get('htmlLink'),
                "message": "Meeting scheduled successfully"
            }
            
        except Exception as e:
            logger.error(f"Error scheduling meeting: {e}")
            return self._schedule_demo_meeting(request, start_datetime, end_datetime)
    
    def _schedule_demo_meeting(self, request: MeetingRequest, start_datetime: datetime, end_datetime: datetime) -> Dict[str, Any]:
        """Schedule a demo meeting."""
        event_id = f"demo_meeting_{int(datetime.now().timestamp())}"
        
        return {
            "success": True,
            "event_id": event_id,
            "title": request.title,
            "start_time": start_datetime.isoformat(),
            "end_time": end_datetime.isoformat(),
            "attendees": request.attendees,
            "meet_link": f"https://meet.google.com/{event_id}",
            "calendar_link": f"https://calendar.google.com/event?eid={event_id}",
            "message": "Meeting scheduled successfully (Demo Mode)",
            "demo_mode": True
        }
    
    async def check_availability(self, check: AvailabilityCheck) -> Dict[str, Any]:
        """Check availability for a time slot."""
        try:
            # Parse times
            start_dt = datetime.fromisoformat(check.start_time.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(check.end_time.replace('Z', '+00:00'))
            
            if self.is_demo_mode:
                return self._check_demo_availability(start_dt, end_dt, check.attendees)
            
            # Real Google Calendar implementation
            body = {
                "timeMin": check.start_time,
                "timeMax": check.end_time,
                "items": [{"id": email} for email in check.attendees]
            }
            
            response = self.service.freebusy().query(body=body).execute()
            
            availability = {}
            all_available = True
            
            for email, calendar_info in response.get('calendars', {}).items():
                busy_periods = calendar_info.get('busy', [])
                is_available = len(busy_periods) == 0
                availability[email] = {
                    "available": is_available,
                    "busy_periods": busy_periods
                }
                if not is_available:
                    all_available = False
            
            return {
                "available": all_available,
                "availability": availability,
                "time_slot": {
                    "start": start_dt.isoformat(),
                    "end": end_dt.isoformat()
                },
                "attendees": check.attendees
            }
            
        except Exception as e:
            logger.error(f"Error checking availability: {e}")
            return self._check_demo_availability(start_dt, end_dt, check.attendees)
    
    def _check_demo_availability(self, start_dt: datetime, end_dt: datetime, attendees: List[str]) -> Dict[str, Any]:
        """Check demo availability."""
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
        
        # Demo availability for attendees
        availability = {}
        for attendee in attendees:
            availability[attendee] = {
                "available": is_available,
                "busy_periods": [] if is_available else [{"start": start_dt.isoformat(), "end": end_dt.isoformat()}]
            }
        
        return {
            "available": is_available,
            "conflict_reason": conflict_reason,
            "availability": availability,
            "time_slot": {
                "start": start_dt.isoformat(),
                "end": end_dt.isoformat()
            },
            "attendees": attendees,
            "demo_mode": True
        }
    
    async def get_meeting_suggestions(self, duration: int = 60, days_ahead: int = 7, attendees: List[str] = None) -> Dict[str, Any]:
        """Get meeting time suggestions."""
        try:
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
                    
                    # Check availability if attendees provided
                    if attendees and not self.is_demo_mode:
                        availability_check = await self.check_availability(AvailabilityCheck(
                            start_time=slot_start.isoformat(),
                            end_time=slot_end.isoformat(),
                            attendees=attendees
                        ))
                        if not availability_check["available"]:
                            continue
                    
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
                "attendees": attendees or [],
                "search_criteria": {
                    "days_ahead": days_ahead,
                    "business_hours": [9, 17]
                },
                "demo_mode": self.is_demo_mode
            }
            
        except Exception as e:
            logger.error(f"Error getting meeting suggestions: {e}")
            return {
                "suggestions": [],
                "error": str(e),
                "demo_mode": True
            }
    
    async def cancel_event(self, event_id: str) -> Dict[str, Any]:
        """Cancel a calendar event."""
        try:
            if self.is_demo_mode:
                return {
                    "success": True,
                    "event_id": event_id,
                    "message": "Event canceled successfully (Demo Mode)",
                    "demo_mode": True
                }
            
            self.service.events().delete(
                calendarId='primary',
                eventId=event_id,
                sendUpdates='all'
            ).execute()
            
            return {
                "success": True,
                "event_id": event_id,
                "message": "Event canceled successfully"
            }
            
        except Exception as e:
            logger.error(f"Error canceling event: {e}")
            return {
                "success": False,
                "error": str(e),
                "demo_mode": True
            }
    
    def is_available(self) -> bool:
        """Check if the calendar service is available."""
        return True  # Always available, either real or demo
    
    def get_status(self) -> Dict[str, Any]:
        """Get calendar service status."""
        return {
            "available": True,
            "demo_mode": self.is_demo_mode,
            "google_calendar_available": GOOGLE_CALENDAR_AVAILABLE,
            "credentials_configured": bool(settings.google_calendar_credentials_path),
            "service_initialized": self.service is not None
        }

# Global calendar service instance
calendar_service = CalendarService() 