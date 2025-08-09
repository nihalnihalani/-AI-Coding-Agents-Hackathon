from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import JSONResponse
import logging
import json
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

from ..agents.aura_agent import AuraAgent
from ..models.schemas import ChatRequest, ChatResponse, ConversationMessage
from ..core.logging import get_logger
from ..services.websocket_manager import websocket_manager
from ..core.auth import get_optional_user, verify_websocket_token

logger = get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

# Active chat sessions
active_chat_sessions = {}

@router.post("/text", response_model=ChatResponse)
async def chat_text(request: ChatRequest):
    """Handle text-based chat interactions with the onboarding agent."""
    try:
        session_id = request.session_id
        user_message = request.message
        context = request.context or {}
        
        logger.info(f"Processing chat message for session {session_id}: {user_message[:100]}...")
        
        # Get or create agent for this session
        if session_id not in active_chat_sessions:
            agent = AuraAgent()
            # Apply any provided context
            if context:
                agent.update_state(context)
            active_chat_sessions[session_id] = agent
        else:
            agent = active_chat_sessions[session_id]
        
        # Process user input through agent
        result = await agent.process_input(user_message, session_id)
        
        # Extract response from conversation history
        conversation_history = result.get("conversation_history", [])
        if conversation_history:
            latest_response = conversation_history[-1]
            response_text = latest_response.get("content", "I'm here to help with your onboarding!")
            llm_used = latest_response.get("llm_used", "unknown")
            intent = latest_response.get("intent")
            suggestions = latest_response.get("suggestions", [])
        else:
            response_text = "I'm here to help with your onboarding! How can I assist you?"
            llm_used = "fallback"
            intent = "greeting"
            suggestions = ["Upload your resume", "Ask about onboarding process", "Get help with tasks"]
        
        # Create response message
        message_id = str(uuid.uuid4())
        
        # Check if onboarding plan was updated
        updated_plan = None
        if result.get("onboarding_plan_steps"):
            # Plan was created or updated
            plan_steps = result.get("onboarding_plan_steps", [])
            completed_tasks = result.get("completed_tasks", [])
            
            updated_plan = {
                "total_tasks": len(plan_steps),
                "completed_tasks": len(completed_tasks),
                "current_step": result.get("current_step"),
                "progress_percentage": (len(completed_tasks) / len(plan_steps) * 100) if plan_steps else 0
            }
        
        response = ChatResponse(
            response=response_text,
            session_id=session_id,
            message_id=message_id,
            llm_used=llm_used,
            intent=intent,
            suggested_actions=suggestions,
            updated_plan=updated_plan
        )
        
        # Send real-time update via WebSocket if connected
        await websocket_manager.send_message(session_id, {
            "category": "chat",
            "type": "chat_response",
            "data": response.dict()
        }, require_auth=False)
        
        logger.info(f"Chat response generated for session {session_id} using {llm_used}")
        
        return response
        
    except Exception as e:
        logger.error(f"Error processing chat message: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process chat message: {str(e)}")

@router.get("/history/{session_id}")
async def get_conversation_history(session_id: str, limit: Optional[int] = 50):
    """Retrieve conversation history for a chat session."""
    try:
        if session_id not in active_chat_sessions:
            return {
                "success": True,
                "data": {
                    "session_id": session_id,
                    "conversation_history": [],
                    "total_messages": 0
                },
                "message": "No conversation history found for this session"
            }
        
        agent = active_chat_sessions[session_id]
        state = agent.get_state()
        conversation_history = state.get("conversation_history", [])
        
        # Apply limit if specified
        if limit and len(conversation_history) > limit:
            conversation_history = conversation_history[-limit:]
        
        # Convert to ConversationMessage format
        formatted_messages = []
        for msg in conversation_history:
            formatted_msg = ConversationMessage(
                message_id=str(uuid.uuid4()),
                session_id=session_id,
                role=msg.get("role", "unknown"),
                content=msg.get("content", ""),
                llm_used=msg.get("llm_used"),
                intent=msg.get("intent"),
                metadata=msg.get("metadata", {}),
                timestamp=datetime.fromisoformat(msg.get("timestamp", datetime.now().isoformat()))
            )
            formatted_messages.append(formatted_msg.dict())
        
        return {
            "success": True,
            "data": {
                "session_id": session_id,
                "conversation_history": formatted_messages,
                "total_messages": len(formatted_messages),
                "current_intent": state.get("current_user_intent"),
                "active_llm": state.get("active_llm")
            },
            "message": f"Retrieved {len(formatted_messages)} messages from conversation history"
        }
        
    except Exception as e:
        logger.error(f"Error retrieving conversation history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.websocket("/stream/{session_id}")
async def websocket_chat_stream(
    websocket: WebSocket, 
    session_id: str, 
    token: Optional[str] = Query(None),
    client_info: Optional[str] = Query(None)
):
    """WebSocket endpoint for real-time chat streaming with authentication."""
    try:
        # Parse client info if provided
        parsed_client_info = None
        if client_info:
            try:
                parsed_client_info = json.loads(client_info)
            except json.JSONDecodeError:
                parsed_client_info = {"user_agent": client_info}
        
        # Connect through WebSocket manager
        await websocket_manager.connect(
            websocket, 
            session_id, 
            token=token,
            client_info=parsed_client_info
        )
        
        # Listen for incoming messages
        while True:
            try:
                data = await websocket.receive_text()
                await websocket_manager.handle_incoming_message(session_id, data)
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error handling WebSocket message for session {session_id}: {e}")
                break
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        logger.error(f"Error in WebSocket connection for session {session_id}: {e}")
    finally:
        await websocket_manager.disconnect(session_id)

@router.post("/context/{session_id}")
async def update_chat_context(session_id: str, context_updates: Dict[str, Any]):
    """Update chat context for a session."""
    try:
        if session_id not in active_chat_sessions:
            # Create new session with context
            agent = AuraAgent()
            agent.update_state(context_updates)
            active_chat_sessions[session_id] = agent
        else:
            # Update existing session
            agent = active_chat_sessions[session_id]
            current_state = agent.get_state()
            
            # Merge context updates
            contextual_memory = current_state.get("contextual_memory", {})
            contextual_memory.update(context_updates)
            
            agent.update_state({
                "contextual_memory": contextual_memory,
                **context_updates
            })
        
        return {
            "success": True,
            "data": {
                "session_id": session_id,
                "context_updates": context_updates,
                "updated_keys": list(context_updates.keys())
            },
            "message": f"Chat context updated with {len(context_updates)} items"
        }
        
    except Exception as e:
        logger.error(f"Error updating chat context: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/suggestions/{session_id}")
async def get_chat_suggestions(session_id: str):
    """Get contextual chat suggestions based on current conversation state."""
    try:
        suggestions = []
        
        if session_id in active_chat_sessions:
            agent = active_chat_sessions[session_id]
            state = agent.get_state()
            
            current_intent = state.get("current_user_intent", "")
            plan_steps = state.get("onboarding_plan_steps", [])
            current_step = state.get("current_step")
            
            # Generate contextual suggestions
            if not plan_steps:
                suggestions = [
                    "Upload my resume to get started",
                    "What is the onboarding process?",
                    "How can you help me with onboarding?"
                ]
            elif current_step:
                current_task = next((step for step in plan_steps if step.get("step_id") == current_step), None)
                if current_task:
                    task_title = current_task.get("title", "current task")
                    suggestions = [
                        f"Help me with: {task_title}",
                        "Mark this task as completed",
                        "What's my next task?",
                        "Show my progress"
                    ]
                else:
                    suggestions = [
                        "What should I work on next?",
                        "Show my onboarding progress",
                        "Schedule a meeting with my team"
                    ]
            else:
                suggestions = [
                    "Show my onboarding plan",
                    "What tasks do I need to complete?",
                    "How can I get help?"
                ]
                
            # Add intent-specific suggestions
            if current_intent == "task_management":
                suggestions.extend([
                    "Update task progress",
                    "Get help with current challenges"
                ])
            elif current_intent == "calendar_scheduling":
                suggestions.extend([
                    "Schedule a team meeting",
                    "Check my availability"
                ])
        else:
            # Default suggestions for new sessions
            suggestions = [
                "Hello, I'm new here",
                "Help me get started with onboarding",
                "Upload my resume"
            ]
        
        return {
            "success": True,
            "data": {
                "session_id": session_id,
                "suggestions": suggestions[:6],  # Limit to 6 suggestions
                "context": {
                    "has_active_session": session_id in active_chat_sessions,
                    "current_intent": active_chat_sessions[session_id].get_state().get("current_user_intent") if session_id in active_chat_sessions else None
                }
            },
            "message": f"Generated {len(suggestions)} contextual suggestions"
        }
        
    except Exception as e:
        logger.error(f"Error getting chat suggestions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/clear-history/{session_id}")
async def clear_conversation_history(session_id: str, keep_context: bool = True):
    """Clear conversation history for a session, optionally keeping context."""
    try:
        if session_id not in active_chat_sessions:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        agent = active_chat_sessions[session_id]
        current_state = agent.get_state()
        
        # Clear conversation history
        cleared_messages = len(current_state.get("conversation_history", []))
        
        updates = {"conversation_history": []}
        
        if not keep_context:
            # Also clear contextual memory and reset to initial state
            updates.update({
                "contextual_memory": {},
                "current_user_intent": None,
                "errors": []
            })
        
        agent.update_state(updates)
        
        # Notify via WebSocket if connected
        await websocket_manager.send_message(session_id, {
            "category": "chat",
            "type": "history_cleared",
            "data": {
                "session_id": session_id,
                "cleared_messages": cleared_messages,
                "context_preserved": keep_context
            }
        }, require_auth=False)
        
        return {
            "success": True,
            "data": {
                "session_id": session_id,
                "cleared_messages": cleared_messages,
                "context_preserved": keep_context
            },
            "message": f"Cleared {cleared_messages} messages from conversation history"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing conversation history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sessions")
async def get_active_chat_sessions():
    """Get list of all active chat sessions."""
    try:
        sessions_info = []
        
        for session_id, agent in active_chat_sessions.items():
            state = agent.get_state()
            conversation_history = state.get("conversation_history", [])
            
            # Get last activity
            last_activity = None
            if conversation_history:
                last_message = conversation_history[-1]
                last_activity = last_message.get("timestamp")
            
            sessions_info.append({
                "session_id": session_id,
                "message_count": len(conversation_history),
                "current_intent": state.get("current_user_intent"),
                "active_llm": state.get("active_llm"),
                "last_activity": last_activity,
                "websocket_connected": session_id in websocket_manager.active_connections,
                "has_onboarding_plan": len(state.get("onboarding_plan_steps", [])) > 0
            })
        
        return {
            "success": True,
            "data": {
                "total_sessions": len(sessions_info),
                "active_websockets": len(websocket_manager.active_connections),
                "sessions": sessions_info
            },
            "message": f"Retrieved {len(sessions_info)} active chat sessions"
        }
        
    except Exception as e:
        logger.error(f"Error getting active chat sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/session/{session_id}")
async def end_chat_session(session_id: str):
    """End a chat session and clean up resources."""
    try:
        session_existed = session_id in active_chat_sessions
        
        if session_existed:
            # Get final statistics
            agent = active_chat_sessions[session_id]
            state = agent.get_state()
            
            session_summary = {
                "session_id": session_id,
                "total_messages": len(state.get("conversation_history", [])),
                "final_intent": state.get("current_user_intent"),
                "llm_used": state.get("active_llm"),
                "end_time": datetime.now().isoformat()
            }
            
            # Remove from active sessions
            del active_chat_sessions[session_id]
        else:
            session_summary = {
                "session_id": session_id,
                "end_time": datetime.now().isoformat(),
                "note": "Session was not active"
            }
        
        # Disconnect WebSocket if connected
        if session_id in websocket_manager.active_connections:
            await websocket_manager.disconnect(session_id)
        
        logger.info(f"Ended chat session {session_id}")
        
        return {
            "success": True,
            "data": session_summary,
            "message": f"Chat session {'ended' if session_existed else 'was not active'}"
        }
        
    except Exception as e:
        logger.error(f"Error ending chat session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def chat_service_health():
    """Check chat service health and statistics."""
    try:
        return {
            "success": True,
            "data": {
                "service_status": "healthy",
                "active_chat_sessions": len(active_chat_sessions),
                "active_websocket_connections": len(websocket_manager.active_connections),
                "websocket_manager_status": "operational",
                "total_sessions_created": len(active_chat_sessions)  # Simplified metric
            },
            "message": "Chat service is healthy and operational"
        }
        
    except Exception as e:
        logger.error(f"Error checking chat service health: {e}")
        raise HTTPException(status_code=500, detail=str(e))