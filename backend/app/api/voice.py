from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
import logging
from typing import Dict, Any, Optional

from ..services.vapi_service import vapi_service
from ..core.logging import get_logger
from ..models.schemas import UserProfile

logger = get_logger(__name__)

router = APIRouter(prefix="/voice", tags=["voice"])

@router.post("/vapi-webhook")
async def vapi_webhook(request: Request):
    """Handle Vapi webhook events for voice interactions."""
    try:
        # Parse webhook data
        webhook_data = await request.json()
        
        # Log webhook for debugging
        event_type = webhook_data.get("type", "unknown")
        call_id = webhook_data.get("call", {}).get("id", "unknown")
        logger.info(f"Received Vapi webhook: {event_type} for call {call_id}")
        
        # Process webhook through Vapi service
        result = await vapi_service.handle_webhook(webhook_data)
        
        # Return appropriate response based on event type
        if event_type == "function-call":
            # Return function call result directly for Vapi to process
            return result
        else:
            # For other events, return success confirmation
            return JSONResponse(
                content={"status": "success", "message": "Webhook processed"},
                status_code=200
            )
            
    except Exception as e:
        logger.error(f"Error processing Vapi webhook: {e}")
        # Always return 200 to Vapi to prevent retries for application errors
        return JSONResponse(
            content={
                "status": "error", 
                "message": "Internal processing error",
                "result": "I apologize, but I'm experiencing a technical issue. Please try again in a moment."
            },
            status_code=200
        )

@router.post("/create-assistant")
async def create_vapi_assistant(user_profile: Optional[UserProfile] = None):
    """Create a personalized Vapi assistant configuration."""
    try:
        # Convert user profile to dict if provided
        profile_dict = user_profile.dict() if user_profile else None
        
        # Create assistant configuration
        result = await vapi_service.create_vapi_assistant(profile_dict)
        
        if result.get("success"):
            return {
                "success": True,
                "assistant_config": result["assistant_config"],
                "message": "Vapi assistant configuration created successfully"
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create assistant: {result.get('error', 'Unknown error')}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating Vapi assistant: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sessions")
async def get_active_voice_sessions():
    """Get information about active voice sessions."""
    try:
        sessions_info = vapi_service.get_active_sessions()
        
        return {
            "success": True,
            "data": sessions_info,
            "message": f"Retrieved {sessions_info['total_active']} active sessions"
        }
        
    except Exception as e:
        logger.error(f"Error retrieving voice sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/session/{call_id}")
async def get_voice_session_details(call_id: str):
    """Get detailed information about a specific voice session."""
    try:
        if call_id not in vapi_service.active_sessions:
            raise HTTPException(status_code=404, detail="Voice session not found")
        
        session = vapi_service.active_sessions[call_id]
        
        # Return sanitized session data (remove sensitive information)
        session_data = {
            "call_id": session.get("call_id"),
            "status": session.get("status"),
            "start_time": session.get("start_time"),
            "duration": vapi_service._calculate_session_duration(session),
            "interaction_count": session.get("interaction_count", 0),
            "transcript_length": len(session.get("transcript", [])),
            "speech_status": session.get("speech_status"),
            "last_activity": session.get("last_speech_update")
        }
        
        return {
            "success": True,
            "data": session_data,
            "message": f"Session details for call {call_id}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving session details: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/session/{call_id}/transcript")
async def get_voice_session_transcript(call_id: str):
    """Get the transcript for a specific voice session."""
    try:
        if call_id not in vapi_service.active_sessions:
            raise HTTPException(status_code=404, detail="Voice session not found")
        
        session = vapi_service.active_sessions[call_id]
        transcript = session.get("transcript", [])
        
        return {
            "success": True,
            "data": {
                "call_id": call_id,
                "transcript": transcript,
                "total_messages": len(transcript)
            },
            "message": f"Transcript for call {call_id} with {len(transcript)} messages"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving transcript: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/session/{call_id}/end")
async def end_voice_session(call_id: str):
    """Manually end a voice session."""
    try:
        if call_id not in vapi_service.active_sessions:
            raise HTTPException(status_code=404, detail="Voice session not found")
        
        session = vapi_service.active_sessions[call_id]
        
        # Update session status
        session["status"] = "manually_ended"
        session["end_time"] = vapi_service.datetime.now().isoformat()
        session["end_reason"] = "manual_termination"
        
        # Save session data
        await vapi_service._save_call_session(session)
        
        return {
            "success": True,
            "message": f"Voice session {call_id} ended successfully",
            "data": {
                "call_id": call_id,
                "status": "ended",
                "end_reason": "manual_termination"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ending voice session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def voice_service_health():
    """Check voice service health and configuration."""
    try:
        # Check Vapi configuration
        vapi_configured = bool(vapi_service.api_key)
        
        # Get active sessions count
        active_sessions = len(vapi_service.active_sessions)
        
        # Check service availability
        service_status = "healthy" if vapi_configured else "configuration_required"
        
        return {
            "success": True,
            "data": {
                "service_status": service_status,
                "vapi_configured": vapi_configured,
                "active_sessions": active_sessions,
                "voice_config": {
                    "provider": vapi_service.voice_config.get("provider"),
                    "voice_id": vapi_service.voice_config.get("voiceId")
                },
                "transcriber_config": {
                    "provider": vapi_service.transcriber_config.get("provider"),
                    "model": vapi_service.transcriber_config.get("model")
                }
            },
            "message": f"Voice service is {service_status}"
        }
        
    except Exception as e:
        logger.error(f"Error checking voice service health: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/test-webhook")
async def test_vapi_webhook():
    """Test endpoint for Vapi webhook functionality."""
    try:
        # Create a test webhook payload
        test_payload = {
            "type": "function-call",
            "call": {"id": "test-call-123"},
            "functionCall": {
                "name": "process_user_input",
                "parameters": {"input": "Hello, this is a test message"}
            }
        }
        
        # Process test webhook
        result = await vapi_service.handle_webhook(test_payload)
        
        return {
            "success": True,
            "data": result,
            "message": "Test webhook processed successfully"
        }
        
    except Exception as e:
        logger.error(f"Error testing webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))