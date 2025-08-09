from typing import Dict, Any, List, Optional
import logging
from datetime import datetime, timedelta
import json
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .base_tool import BaseTool, ToolExecutionResult
from ..core.config import settings
from ..core.logging import get_logger

logger = get_logger(__name__)

class CalendarTool(BaseTool):
    """Google Calendar integration tool for meeting scheduling and management."""
    
    def __init__(self):
        super().__init__(
            name="calendar_tool",
            description="Google Calendar integration for scheduling meetings and managing events"
        )
        
        # Google Calendar API scopes
        self.scopes = [
            'https://www.googleapis.com/auth/calendar',
            'https://www.googleapis.com/auth/calendar.events'
        ]
        
        self.service = None
        self.credentials = None
        self._initialize_service()
    
    def _initialize_service(self):
        """Initialize Google Calendar service."""
        try:
            if not settings.google_calendar_credentials:
                logger.warning("Google Calendar credentials not configured")
                return
            
            # Load credentials
            self.credentials = self._load_credentials()
            
            if self.credentials and self.credentials.valid:
                self.service = build('calendar', 'v3', credentials=self.credentials)
                logger.info("Google Calendar service initialized successfully")
            else:
                logger.warning("Google Calendar credentials are invalid or expired")
                
        except Exception as e:
            logger.error(f"Error initializing Google Calendar service: {e}")
            self.service = None
    
    def _load_credentials(self) -> Optional[Credentials]:
        """Load Google Calendar credentials."""
        try:
            credentials_path = settings.google_calendar_credentials
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
                    if os.path.exists(credentials_path):
                        flow = InstalledAppFlow.from_client_secrets_file(
                            credentials_path, self.scopes
                        )
                        creds = flow.run_local_server(port=0)
                    else:
                        logger.error(f"Credentials file not found: {credentials_path}")
                        return None
                
                # Save credentials for next run
                with open(token_path, 'w') as token:
                    token.write(creds.to_json())
            
            return creds
            
        except Exception as e:
            logger.error(f"Error loading Google Calendar credentials: {e}")
            return None
    
    async def execute(self, action: str, parameters: Dict[str, Any]) -> ToolExecutionResult:
        """Execute calendar actions."""
        try:
            if action == "schedule_meeting":
                return await self._schedule_meeting(parameters)
            elif action == "check_availability":
                return await self._check_availability(parameters)
            elif action == "list_events":
                return await self._list_events(parameters)
            elif action == "update_event":
                return await self._update_event(parameters)
            elif action == "cancel_event":
                return await self._cancel_event(parameters)
            elif action == "create_recurring_event":
                return await self._create_recurring_event(parameters)
            elif action == "find_meeting_times":
                return await self._find_meeting_times(parameters)
            else:
                return ToolExecutionResult(
                    success=False,
                    error=f"Unknown action: {action}"
                )
                
        except Exception as e:
            logger.error(f"Error executing calendar action {action}: {e}")
            return ToolExecutionResult(
                success=False,
                error=f"Calendar action failed: {str(e)}"
            )
    
    async def _schedule_meeting(self, parameters: Dict[str, Any]) -> ToolExecutionResult:
        """Schedule a new meeting."""
        try:
            # Extract parameters
            title = parameters.get("title", "Onboarding Meeting")
            description = parameters.get("description", "")
            start_time = parameters.get("start_time")  # ISO format
            duration = parameters.get("duration", 60)  # minutes
            attendees = parameters.get("attendees", [])  # list of emails
            location = parameters.get("location", "")
            
            if not start_time:
                return ToolExecutionResult(
                    success=False,
                    error="start_time is required for scheduling meetings"
                )
            
            # Parse start time
            start_datetime = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            end_datetime = start_datetime + timedelta(minutes=duration)
            
            # Create event
            event = {
                'summary': title,
                'description': description,
                'location': location,
                'start': {
                    'dateTime': start_datetime.isoformat(),
                    'timeZone': 'UTC',
                },
                'end': {
                    'dateTime': end_datetime.isoformat(),
                    'timeZone': 'UTC',
                },
                'attendees': [{'email': email} for email in attendees],
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
            
            # Create the event
            created_event = self.service.events().insert(
                calendarId='primary',
                body=event,
                conferenceDataVersion=1,
                sendUpdates='all'
            ).execute()
            
            return ToolExecutionResult(
                success=True,
                data={
                    "event_id": created_event['id'],
                    "event_link": created_event.get('htmlLink'),
                    "meet_link": created_event.get('conferenceData', {}).get('entryPoints', [{}])[0].get('uri'),
                    "title": title,
                    "start_time": start_datetime.isoformat(),
                    "end_time": end_datetime.isoformat(),
                    "attendees": attendees,
                    "message": "Meeting scheduled successfully"
                }
            )
            
        except HttpError as e:
            logger.error(f"Google Calendar API error: {e}")
            return ToolExecutionResult(
                success=False,
                error=f"Calendar API error: {str(e)}"
            )
    
    async def _check_availability(self, parameters: Dict[str, Any]) -> ToolExecutionResult:
        """Check availability for given time slots."""
        try:
            start_time = parameters.get("start_time")
            end_time = parameters.get("end_time")
            emails = parameters.get("emails", ["primary"])
            
            if not start_time or not end_time:
                return ToolExecutionResult(
                    success=False,
                    error="start_time and end_time are required"
                )
            
            # Query free/busy information
            body = {
                "timeMin": start_time,
                "timeMax": end_time,
                "items": [{"id": email} for email in emails]
            }
            
            response = self.service.freebusy().query(body=body).execute()
            
            availability = {}
            for email, calendar_info in response.get('calendars', {}).items():
                busy_periods = calendar_info.get('busy', [])
                availability[email] = {
                    "available": len(busy_periods) == 0,
                    "busy_periods": busy_periods
                }
            
            return ToolExecutionResult(
                success=True,
                data={
                    "availability": availability,
                    "query_period": {
                        "start": start_time,
                        "end": end_time
                    }
                }
            )
            
        except HttpError as e:
            return ToolExecutionResult(
                success=False,
                error=f"Error checking availability: {str(e)}"
            )
    
    async def _list_events(self, parameters: Dict[str, Any]) -> ToolExecutionResult:
        """List upcoming events."""
        try:
            max_results = parameters.get("max_results", 10)
            days_ahead = parameters.get("days_ahead", 7)
            
            # Calculate time range
            now = datetime.utcnow()
            time_min = now.isoformat() + 'Z'
            time_max = (now + timedelta(days=days_ahead)).isoformat() + 'Z'
            
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                maxResults=max_results,
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
                    "start_time": start,
                    "end_time": event['end'].get('dateTime', event['end'].get('date')),
                    "description": event.get('description', ''),
                    "location": event.get('location', ''),
                    "attendees": [attendee.get('email') for attendee in event.get('attendees', [])]
                })
            
            return ToolExecutionResult(
                success=True,
                data={
                    "events": processed_events,
                    "total_count": len(processed_events),
                    "query_range": {
                        "start": time_min,
                        "end": time_max
                    }
                }
            )
            
        except HttpError as e:
            return ToolExecutionResult(
                success=False,
                error=f"Error listing events: {str(e)}"
            )
    
    async def _find_meeting_times(self, parameters: Dict[str, Any]) -> ToolExecutionResult:
        """Find available meeting times for multiple attendees."""
        try:
            attendees = parameters.get("attendees", [])
            duration = parameters.get("duration", 60)  # minutes
            days_ahead = parameters.get("days_ahead", 7)
            preferred_hours = parameters.get("preferred_hours", [9, 17])  # 9 AM to 5 PM
            
            suggestions = []
            
            # Check each day in the range
            for day_offset in range(days_ahead):
                check_date = datetime.utcnow().date() + timedelta(days=day_offset)
                
                # Skip weekends
                if check_date.weekday() >= 5:
                    continue
                
                # Check hourly slots within preferred hours
                for hour in range(preferred_hours[0], preferred_hours[1]):
                    slot_start = datetime.combine(check_date, datetime.min.time().replace(hour=hour))
                    slot_end = slot_start + timedelta(minutes=duration)
                    
                    # Check if this slot is available for all attendees
                    availability_check = await self._check_availability({
                        "start_time": slot_start.isoformat() + 'Z',
                        "end_time": slot_end.isoformat() + 'Z',
                        "emails": attendees
                    })
                    
                    if availability_check.success:
                        all_available = all(
                            info["available"] 
                            for info in availability_check.data["availability"].values()
                        )
                        
                        if all_available:
                            suggestions.append({
                                "start_time": slot_start.isoformat(),
                                "end_time": slot_end.isoformat(),
                                "confidence": 1.0,
                                "reason": "All attendees available"
                            })
                            
                            # Limit suggestions
                            if len(suggestions) >= 5:
                                break
                
                if len(suggestions) >= 5:
                    break
            
            return ToolExecutionResult(
                success=True,
                data={
                    "suggestions": suggestions,
                    "attendees": attendees,
                    "duration_minutes": duration,
                    "search_criteria": {
                        "days_ahead": days_ahead,
                        "preferred_hours": preferred_hours
                    }
                }
            )
            
        except Exception as e:
            return ToolExecutionResult(
                success=False,
                error=f"Error finding meeting times: {str(e)}"
            )
    
    async def _update_event(self, parameters: Dict[str, Any]) -> ToolExecutionResult:
        """Update an existing event."""
        try:
            event_id = parameters.get("event_id")
            updates = parameters.get("updates", {})
            
            if not event_id:
                return ToolExecutionResult(
                    success=False,
                    error="event_id is required for updating events"
                )
            
            # Get existing event
            event = self.service.events().get(
                calendarId='primary',
                eventId=event_id
            ).execute()
            
            # Apply updates
            if "title" in updates:
                event["summary"] = updates["title"]
            
            if "description" in updates:
                event["description"] = updates["description"]
            
            if "start_time" in updates:
                start_datetime = datetime.fromisoformat(updates["start_time"].replace('Z', '+00:00'))
                event["start"]["dateTime"] = start_datetime.isoformat()
                
                # Update end time if duration is provided
                if "duration" in updates:
                    end_datetime = start_datetime + timedelta(minutes=updates["duration"])
                    event["end"]["dateTime"] = end_datetime.isoformat()
            
            # Update the event
            updated_event = self.service.events().update(
                calendarId='primary',
                eventId=event_id,
                body=event,
                sendUpdates='all'
            ).execute()
            
            return ToolExecutionResult(
                success=True,
                data={
                    "event_id": updated_event['id'],
                    "title": updated_event.get('summary'),
                    "updated_fields": list(updates.keys()),
                    "message": "Event updated successfully"
                }
            )
            
        except HttpError as e:
            return ToolExecutionResult(
                success=False,
                error=f"Error updating event: {str(e)}"
            )
    
    async def _cancel_event(self, parameters: Dict[str, Any]) -> ToolExecutionResult:
        """Cancel an event."""
        try:
            event_id = parameters.get("event_id")
            send_updates = parameters.get("send_updates", True)
            
            if not event_id:
                return ToolExecutionResult(
                    success=False,
                    error="event_id is required for canceling events"
                )
            
            self.service.events().delete(
                calendarId='primary',
                eventId=event_id,
                sendUpdates='all' if send_updates else 'none'
            ).execute()
            
            return ToolExecutionResult(
                success=True,
                data={
                    "event_id": event_id,
                    "message": "Event canceled successfully"
                }
            )
            
        except HttpError as e:
            return ToolExecutionResult(
                success=False,
                error=f"Error canceling event: {str(e)}"
            )
    
    async def _create_recurring_event(self, parameters: Dict[str, Any]) -> ToolExecutionResult:
        """Create a recurring event series."""
        try:
            title = parameters.get("title", "Recurring Onboarding Meeting")
            start_time = parameters.get("start_time")
            duration = parameters.get("duration", 60)
            recurrence_rule = parameters.get("recurrence", "FREQ=WEEKLY;COUNT=4")  # Weekly for 4 weeks
            attendees = parameters.get("attendees", [])
            
            if not start_time:
                return ToolExecutionResult(
                    success=False,
                    error="start_time is required for recurring events"
                )
            
            start_datetime = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            end_datetime = start_datetime + timedelta(minutes=duration)
            
            event = {
                'summary': title,
                'start': {
                    'dateTime': start_datetime.isoformat(),
                    'timeZone': 'UTC',
                },
                'end': {
                    'dateTime': end_datetime.isoformat(),
                    'timeZone': 'UTC',
                },
                'attendees': [{'email': email} for email in attendees],
                'recurrence': [recurrence_rule],
                'reminders': {
                    'useDefault': True
                }
            }
            
            created_event = self.service.events().insert(
                calendarId='primary',
                body=event,
                sendUpdates='all'
            ).execute()
            
            return ToolExecutionResult(
                success=True,
                data={
                    "event_id": created_event['id'],
                    "title": title,
                    "recurrence": recurrence_rule,
                    "message": "Recurring event created successfully"
                }
            )
            
        except HttpError as e:
            return ToolExecutionResult(
                success=False,
                error=f"Error creating recurring event: {str(e)}"
            )
    
    def is_available(self) -> bool:
        """Check if the calendar tool is available."""
        return self.service is not None and self.credentials is not None
    
    def get_available_actions(self) -> List[str]:
        """Get list of available actions."""
        return [
            "schedule_meeting",
            "check_availability", 
            "list_events",
            "update_event",
            "cancel_event",
            "create_recurring_event",
            "find_meeting_times"
        ]