# Google Calendar Integration - Aura Onboarding Agent

## Overview

The Aura Onboarding Agent now includes a comprehensive Google Calendar integration that provides both real Google Calendar API functionality and demo mode for testing. The integration is designed to be robust, with proper error handling and fallback mechanisms.

## Features

### ✅ Core Calendar Functions
- **Event Management**: Create, read, update, and delete calendar events
- **Meeting Scheduling**: Schedule meetings with attendees and video conferencing
- **Availability Checking**: Check availability for multiple attendees
- **Meeting Suggestions**: Get intelligent meeting time suggestions
- **Recurring Events**: Create recurring meeting series
- **Calendar Sync**: Real-time synchronization with Google Calendar

### ✅ Advanced Features
- **Demo Mode**: Full functionality without Google Calendar credentials
- **Error Handling**: Graceful fallback when Google Calendar is unavailable
- **Business Hours**: Intelligent scheduling within business hours
- **Conflict Detection**: Automatic detection of scheduling conflicts
- **Video Conferencing**: Automatic Google Meet link generation
- **Reminders**: Configurable email and popup reminders

## API Endpoints

### Calendar Events
```
GET /api/calendar/events?days=7
```
Returns calendar events for the specified number of days.

**Response:**
```json
{
  "events": [
    {
      "id": "demo_event_0",
      "title": "Onboarding Meeting 1",
      "description": "Onboarding session for new employee - Day 1",
      "start_time": "2025-08-02T10:00:00",
      "end_time": "2025-08-02T11:00:00",
      "location": "Conference Room A",
      "attendees": ["demo@aura.ai", "manager@aura.ai"],
      "meet_link": "https://meet.google.com/demo-0",
      "status": "confirmed"
    }
  ],
  "total_count": 1,
  "query_range": {
    "start": "2025-08-02T23:28:00",
    "end": "2025-08-09T23:28:00"
  },
  "demo_mode": true
}
```

### Schedule Meeting
```
POST /api/calendar/schedule
```
Schedule a new meeting.

**Request Body:**
```json
{
  "title": "Onboarding Kickoff",
  "description": "Initial onboarding meeting with new employee",
  "start_time": "2025-08-04T10:00:00",
  "duration": 60,
  "attendees": ["demo@aura.ai", "manager@aura.ai"],
  "location": "Conference Room A"
}
```

**Response:**
```json
{
  "success": true,
  "event_id": "demo_meeting_1754176262621",
  "title": "Onboarding Kickoff",
  "start_time": "2025-08-04T10:00:00",
  "end_time": "2025-08-04T11:00:00",
  "attendees": ["demo@aura.ai", "manager@aura.ai"],
  "meet_link": "https://meet.google.com/demo_meeting_1754176262621",
  "calendar_link": "https://calendar.google.com/event?eid=demo_meeting_1754176262621",
  "message": "Meeting scheduled successfully (Demo Mode)",
  "demo_mode": true
}
```

### Check Availability
```
GET /api/calendar/availability?start_time=2025-08-04T10:00:00&end_time=2025-08-04T11:00:00&attendees=demo@aura.ai,manager@aura.ai
```
Check availability for a specific time slot.

**Response:**
```json
{
  "available": true,
  "conflict_reason": null,
  "availability": {
    "demo@aura.ai": {
      "available": true,
      "busy_periods": []
    },
    "manager@aura.ai": {
      "available": true,
      "busy_periods": []
    }
  },
  "time_slot": {
    "start": "2025-08-04T10:00:00",
    "end": "2025-08-04T11:00:00"
  },
  "attendees": ["demo@aura.ai", "manager@aura.ai"],
  "demo_mode": true
}
```

### Get Meeting Suggestions
```
GET /api/calendar/suggestions?duration=60&days_ahead=7&attendees=demo@aura.ai,manager@aura.ai
```
Get intelligent meeting time suggestions.

**Response:**
```json
{
  "suggestions": [
    {
      "start_time": "2025-08-04T09:00:00",
      "end_time": "2025-08-04T10:00:00",
      "confidence": 0.9,
      "reason": "Business hours, no conflicts detected"
    }
  ],
  "duration_minutes": 60,
  "attendees": ["demo@aura.ai", "manager@aura.ai"],
  "search_criteria": {
    "days_ahead": 7,
    "business_hours": [9, 17]
  },
  "demo_mode": true
}
```

### Cancel Event
```
DELETE /api/calendar/events/{event_id}
```
Cancel a calendar event.

**Response:**
```json
{
  "success": true,
  "event_id": "demo_event_123",
  "message": "Event canceled successfully (Demo Mode)"
}
```

### Update Event
```
PUT /api/calendar/events/{event_id}
```
Update a calendar event.

**Request Body:**
```json
{
  "title": "Updated Meeting Title",
  "description": "Updated description",
  "start_time": "2025-08-04T10:00:00",
  "end_time": "2025-08-04T11:00:00",
  "attendees": ["demo@aura.ai"],
  "location": "Conference Room B"
}
```

### Calendar Status
```
GET /api/calendar/status
```
Get calendar service status and configuration.

**Response:**
```json
{
  "available": true,
  "demo_mode": true,
  "google_calendar_available": true,
  "credentials_configured": false,
  "service_initialized": false,
  "message": "Calendar service running in demo mode"
}
```

## Configuration

### Environment Variables

Add these to your `.env` file:

```env
# Google Calendar Configuration
GOOGLE_CALENDAR_CREDENTIALS_PATH=/path/to/credentials.json
```

### Google Calendar Setup

1. **Create Google Cloud Project**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing one
   - Enable Google Calendar API

2. **Create Service Account**:
   - Go to "IAM & Admin" > "Service Accounts"
   - Create a new service account
   - Download the JSON credentials file

3. **Configure Credentials**:
   - Place the credentials file in your project
   - Update `GOOGLE_CALENDAR_CREDENTIALS_PATH` in `.env`
   - The service will automatically handle OAuth flow

### Demo Mode

The calendar service automatically runs in demo mode when:
- Google Calendar credentials are not configured
- Google Calendar dependencies are not available
- Credentials are invalid or expired

Demo mode provides full functionality with simulated data, making it perfect for development and testing.

## Service Architecture

### CalendarService Class

The main service class provides:

- **Automatic Fallback**: Switches to demo mode when Google Calendar is unavailable
- **Error Handling**: Graceful error handling with detailed logging
- **Credential Management**: Automatic OAuth flow and token refresh
- **Demo Data**: Realistic demo data for testing

### Key Methods

```python
# Get calendar events
await calendar_service.get_events(days=7)

# Schedule a meeting
await calendar_service.schedule_meeting(meeting_request)

# Check availability
await calendar_service.check_availability(availability_check)

# Get meeting suggestions
await calendar_service.get_meeting_suggestions(duration=60, days_ahead=7)

# Cancel an event
await calendar_service.cancel_event(event_id)

# Get service status
calendar_service.get_status()
```

## Integration with AI Agent

The calendar integration is seamlessly integrated with the AI agent:

### Intent Recognition
- **Calendar Scheduling**: Recognizes meeting scheduling requests
- **Availability Queries**: Understands availability checking
- **Event Management**: Handles event creation, updates, and cancellation

### Tool Integration
The calendar tool is registered with the agent and can be used for:
- Scheduling onboarding meetings
- Checking manager availability
- Creating recurring training sessions
- Coordinating team meetings

### Example Agent Interactions

```
User: "Schedule a meeting with my manager tomorrow at 2 PM"
Agent: "I'll schedule a meeting with your manager tomorrow at 2 PM. Let me check availability and create the event."

User: "What meetings do I have this week?"
Agent: "Let me check your calendar for this week's meetings."

User: "Find a time when both my manager and I are available"
Agent: "I'll check both calendars and suggest available meeting times."
```

## Error Handling

The calendar integration includes comprehensive error handling:

### Common Scenarios
- **Network Issues**: Graceful fallback to demo mode
- **Invalid Credentials**: Automatic retry with OAuth flow
- **API Limits**: Rate limiting and retry logic
- **Invalid Requests**: Detailed error messages

### Error Responses
```json
{
  "success": false,
  "error": "Error scheduling meeting: Invalid time format",
  "demo_mode": true
}
```

## Testing

### Manual Testing
```bash
# Test calendar status
curl http://localhost:8000/api/calendar/status

# Test getting events
curl "http://localhost:8000/api/calendar/events?days=7"

# Test scheduling a meeting
curl -X POST http://localhost:8000/api/calendar/schedule \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Meeting",
    "start_time": "2025-08-04T10:00:00",
    "duration": 60,
    "attendees": ["demo@aura.ai"]
  }'

# Test availability check
curl "http://localhost:8000/api/calendar/availability?start_time=2025-08-04T10:00:00&end_time=2025-08-04T11:00:00"
```

### Automated Testing
The calendar service includes comprehensive unit tests covering:
- Demo mode functionality
- Error handling scenarios
- API endpoint validation
- Integration with AI agent

## Future Enhancements

### Planned Features
- **Calendar Sync**: Real-time sync with multiple calendar providers
- **Smart Scheduling**: AI-powered meeting time optimization
- **Recurring Patterns**: Advanced recurring meeting patterns
- **Calendar Analytics**: Meeting analytics and insights
- **Integration APIs**: Connect with other calendar services

### Roadmap
1. **Phase 1**: Basic Google Calendar integration ✅
2. **Phase 2**: Advanced scheduling algorithms
3. **Phase 3**: Multi-calendar support
4. **Phase 4**: AI-powered optimization

## Support

For issues with the calendar integration:

1. **Check Status**: Use `/api/calendar/status` to verify service health
2. **Review Logs**: Check application logs for detailed error messages
3. **Test Endpoints**: Use the provided test endpoints to isolate issues
4. **Demo Mode**: Verify functionality works in demo mode first

The calendar integration is designed to be robust and user-friendly, providing both powerful real-world functionality and comprehensive testing capabilities. 