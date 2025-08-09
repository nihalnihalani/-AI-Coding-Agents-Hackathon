from typing import Dict, Any, Optional, List
import logging
import json
import asyncio
from datetime import datetime
import httpx

from ..core.config import settings
from ..core.logging import get_logger
from ..agents.aura_agent import AuraAgent

logger = get_logger(__name__)

class VapiService:
    """Vapi AI integration service for voice interactions."""
    
    def __init__(self):
        self.api_key = settings.vapi_api_key
        self.base_url = "https://api.vapi.ai"
        self.agent_instance = None
        
        # Voice interaction configuration
        self.voice_config = {
            "provider": "11labs",
            "voiceId": "rachel",  # Professional female voice
            "stability": 0.7,
            "similarityBoost": 0.8,
            "style": 0.3,
            "useSpeakerBoost": True
        }
        
        # Speech-to-text configuration
        self.transcriber_config = {
            "provider": "deepgram",
            "model": "nova-2",
            "language": "en-US",
            "smartFormat": True,
            "keywords": ["onboarding", "resume", "training", "meeting", "schedule", "task", "help"]
        }
        
        # Active call sessions
        self.active_sessions = {}
    
    async def handle_webhook(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming Vapi webhook events."""
        try:
            event_type = webhook_data.get("type")
            call_id = webhook_data.get("call", {}).get("id")
            
            logger.info(f"Received Vapi webhook: {event_type} for call {call_id}")
            
            if event_type == "function-call":
                return await self._handle_function_call(webhook_data)
            elif event_type == "speech-update":
                return await self._handle_speech_update(webhook_data)
            elif event_type == "transcript":
                return await self._handle_transcript(webhook_data)
            elif event_type == "call-start":
                return await self._handle_call_start(webhook_data)
            elif event_type == "call-end":
                return await self._handle_call_end(webhook_data)
            elif event_type == "hang":
                return await self._handle_hang(webhook_data)
            else:
                logger.warning(f"Unhandled webhook event type: {event_type}")
                return {"status": "ignored", "message": f"Event type {event_type} not handled"}
                
        except Exception as e:
            logger.error(f"Error handling Vapi webhook: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _handle_function_call(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle function calls from Vapi assistant."""
        try:
            function_call = webhook_data.get("functionCall", {})
            function_name = function_call.get("name")
            parameters = function_call.get("parameters", {})
            call_id = webhook_data.get("call", {}).get("id")
            
            logger.info(f"Function call: {function_name} with params: {parameters}")
            
            # Get or create agent instance for this call
            agent = await self._get_agent_for_call(call_id)
            
            # Process the function call through our agent
            if function_name == "process_user_input":
                user_input = parameters.get("input", "")
                response = await self._process_voice_input(agent, user_input, call_id)
                
                return {
                    "result": response.get("response", "I'm here to help with your onboarding!"),
                    "suggestions": response.get("suggestions", []),
                    "followUp": response.get("follow_up_actions", [])
                }
            
            elif function_name == "get_onboarding_status":
                status = await self._get_onboarding_status(agent, call_id)
                return {
                    "result": status.get("summary", "Getting your onboarding status..."),
                    "progress": status.get("progress", {}),
                    "nextSteps": status.get("next_steps", [])
                }
            
            elif function_name == "schedule_meeting":
                meeting_request = parameters.get("meeting_details", {})
                result = await self._schedule_meeting_via_voice(agent, meeting_request, call_id)
                return {
                    "result": result.get("message", "I'll help you schedule that meeting."),
                    "meetingDetails": result.get("meeting_details", {}),
                    "success": result.get("success", False)
                }
            
            elif function_name == "upload_resume":
                return {
                    "result": "I can help you with your resume! Please upload it through the web interface, and I'll analyze it to create your personalized onboarding plan.",
                    "instruction": "Visit the web app to upload your resume file"
                }
            
            else:
                return {
                    "result": f"I understand you're asking about {function_name}. Let me help you with that through our onboarding system.",
                    "suggestion": "Let me know what specific help you need with your onboarding."
                }
                
        except Exception as e:
            logger.error(f"Error handling function call: {e}")
            return {
                "result": "I apologize, but I'm having a technical issue. Please try again or ask me something else about your onboarding.",
                "error": True
            }
    
    async def _handle_speech_update(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle speech-to-text updates."""
        try:
            speech_update = webhook_data.get("speechUpdate", {})
            call_id = webhook_data.get("call", {}).get("id")
            status = speech_update.get("status")  # "started", "stopped"
            
            # Update session state
            if call_id in self.active_sessions:
                self.active_sessions[call_id]["speech_status"] = status
                self.active_sessions[call_id]["last_speech_update"] = datetime.now().isoformat()
            
            logger.info(f"Speech update for call {call_id}: {status}")
            
            return {"status": "processed", "call_id": call_id, "speech_status": status}
            
        except Exception as e:
            logger.error(f"Error handling speech update: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _handle_transcript(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle transcript updates."""
        try:
            transcript = webhook_data.get("transcript", {})
            call_id = webhook_data.get("call", {}).get("id")
            text = transcript.get("text", "")
            role = transcript.get("role", "user")  # "user" or "assistant"
            
            # Store transcript in session
            if call_id in self.active_sessions:
                if "transcript" not in self.active_sessions[call_id]:
                    self.active_sessions[call_id]["transcript"] = []
                
                self.active_sessions[call_id]["transcript"].append({
                    "role": role,
                    "text": text,
                    "timestamp": datetime.now().isoformat()
                })
            
            logger.info(f"Transcript update for call {call_id}: {role} - {text[:100]}...")
            
            return {"status": "processed", "call_id": call_id, "transcript_length": len(text)}
            
        except Exception as e:
            logger.error(f"Error handling transcript: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _handle_call_start(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle call start event."""
        try:
            call = webhook_data.get("call", {})
            call_id = call.get("id")
            customer_number = call.get("customer", {}).get("number")
            
            # Initialize session
            self.active_sessions[call_id] = {
                "call_id": call_id,
                "customer_number": customer_number,
                "start_time": datetime.now().isoformat(),
                "status": "active",
                "transcript": [],
                "agent_state": {},
                "interaction_count": 0
            }
            
            logger.info(f"Call started: {call_id} from {customer_number}")
            
            # Create welcome message
            welcome_message = "Hello! I'm Aura, your AI onboarding assistant. I'm here to help you with your employee onboarding process. How can I assist you today?"
            
            return {
                "status": "call_started",
                "call_id": call_id,
                "welcome_message": welcome_message
            }
            
        except Exception as e:
            logger.error(f"Error handling call start: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _handle_call_end(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle call end event."""
        try:
            call = webhook_data.get("call", {})
            call_id = call.get("id")
            end_reason = call.get("endedReason", "unknown")
            duration = call.get("duration", 0)
            
            # Update session
            if call_id in self.active_sessions:
                self.active_sessions[call_id]["status"] = "ended"
                self.active_sessions[call_id]["end_time"] = datetime.now().isoformat()
                self.active_sessions[call_id]["end_reason"] = end_reason
                self.active_sessions[call_id]["duration"] = duration
                
                # Save session data for analytics
                await self._save_call_session(self.active_sessions[call_id])
                
                # Clean up after some time (keep for a while for potential follow-up)
                asyncio.create_task(self._cleanup_session(call_id, delay=3600))  # 1 hour
            
            logger.info(f"Call ended: {call_id}, reason: {end_reason}, duration: {duration}s")
            
            return {
                "status": "call_ended",
                "call_id": call_id,
                "duration": duration,
                "end_reason": end_reason
            }
            
        except Exception as e:
            logger.error(f"Error handling call end: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _handle_hang(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle hang event (call interruption)."""
        try:
            call_id = webhook_data.get("call", {}).get("id")
            
            if call_id in self.active_sessions:
                self.active_sessions[call_id]["status"] = "hung_up"
                self.active_sessions[call_id]["hang_time"] = datetime.now().isoformat()
            
            logger.info(f"Call hung up: {call_id}")
            
            return {"status": "hang_processed", "call_id": call_id}
            
        except Exception as e:
            logger.error(f"Error handling hang: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _get_agent_for_call(self, call_id: str) -> AuraAgent:
        """Get or create an agent instance for a specific call."""
        if call_id not in self.active_sessions:
            logger.warning(f"No active session found for call {call_id}")
            # Create a basic session
            self.active_sessions[call_id] = {
                "call_id": call_id,
                "start_time": datetime.now().isoformat(),
                "status": "active",
                "agent_state": {},
                "interaction_count": 0
            }
        
        session = self.active_sessions[call_id]
        
        # Create or get agent instance
        if "agent" not in session:
            agent = AuraAgent()
            # Restore agent state if available
            if session.get("agent_state"):
                agent.state.update(session["agent_state"])
            session["agent"] = agent
        
        return session["agent"]
    
    async def _process_voice_input(self, agent: AuraAgent, user_input: str, call_id: str) -> Dict[str, Any]:
        """Process voice input through the agent."""
        try:
            # Update session interaction count
            if call_id in self.active_sessions:
                self.active_sessions[call_id]["interaction_count"] += 1
            
            # Process input through agent
            result = await agent.process_input(user_input, call_id)
            
            # Save updated agent state
            if call_id in self.active_sessions:
                self.active_sessions[call_id]["agent_state"] = result
            
            # Extract response for voice
            conversation_history = result.get("conversation_history", [])
            if conversation_history:
                latest_response = conversation_history[-1]
                response_text = latest_response.get("content", "I'm here to help!")
                
                # Get follow-up suggestions
                suggestions = latest_response.get("suggestions", [])
                
                return {
                    "response": response_text,
                    "suggestions": suggestions,
                    "follow_up_actions": self._generate_voice_follow_ups(result),
                    "agent_state_updated": True
                }
            else:
                return {
                    "response": "I'm processing your request. How else can I help you with your onboarding?",
                    "suggestions": ["Ask about your onboarding plan", "Get help with tasks", "Schedule a meeting"],
                    "follow_up_actions": []
                }
                
        except Exception as e:
            logger.error(f"Error processing voice input: {e}")
            return {
                "response": "I apologize, but I'm having trouble processing that right now. Could you please try rephrasing your question?",
                "suggestions": ["Try asking differently", "Contact support", "Use the web interface"],
                "error": True
            }
    
    async def _get_onboarding_status(self, agent: AuraAgent, call_id: str) -> Dict[str, Any]:
        """Get onboarding status for voice response."""
        try:
            state = agent.get_state()
            
            # Calculate progress
            total_tasks = len(state.get("onboarding_plan_steps", []))
            completed_tasks = len(state.get("completed_tasks", []))
            current_step = state.get("current_step")
            
            if total_tasks > 0:
                progress_percentage = int((completed_tasks / total_tasks) * 100)
                summary = f"You've completed {completed_tasks} out of {total_tasks} onboarding tasks, which is {progress_percentage}% progress."
            else:
                summary = "I don't see an onboarding plan set up yet. Would you like me to help you get started?"
            
            # Add current step info
            if current_step:
                current_task = next(
                    (task for task in state.get("onboarding_plan_steps", []) 
                     if task.get("step_id") == current_step), None
                )
                if current_task:
                    summary += f" You're currently working on: {current_task.get('title', 'your current task')}."
            
            # Generate next steps
            next_steps = []
            if total_tasks == 0:
                next_steps = ["Upload your resume", "Set up your onboarding plan", "Schedule initial meetings"]
            elif current_step:
                next_steps = ["Complete your current task", "Ask for help if needed", "Update your progress"]
            else:
                next_steps = ["Review remaining tasks", "Start your next task", "Check your schedule"]
            
            return {
                "summary": summary,
                "progress": {
                    "completed": completed_tasks,
                    "total": total_tasks,
                    "percentage": progress_percentage if total_tasks > 0 else 0,
                    "current_step": current_step
                },
                "next_steps": next_steps
            }
            
        except Exception as e:
            logger.error(f"Error getting onboarding status: {e}")
            return {
                "summary": "I'm having trouble accessing your onboarding status right now. Please try again in a moment.",
                "progress": {"completed": 0, "total": 0, "percentage": 0},
                "next_steps": ["Try again", "Check the web interface", "Contact support"]
            }
    
    async def _schedule_meeting_via_voice(self, agent: AuraAgent, meeting_request: Dict[str, Any], call_id: str) -> Dict[str, Any]:
        """Handle meeting scheduling through voice."""
        try:
            # Extract meeting details from voice request
            title = meeting_request.get("title", "Onboarding Meeting")
            description = meeting_request.get("description", "Meeting scheduled via voice assistant")
            duration = meeting_request.get("duration", 60)  # Default 1 hour
            
            # For voice, we'll suggest times rather than schedule immediately
            # This prevents scheduling conflicts and ensures proper confirmation
            
            response_message = f"I'd be happy to help you schedule a {title}. "
            
            # Check if we have calendar access
            state = agent.get_state()
            if "calendar_tool" in state.get("tool_states", {}):
                response_message += "I can suggest some available times for you. Would you prefer morning or afternoon slots?"
                
                return {
                    "message": response_message,
                    "success": True,
                    "meeting_details": {
                        "title": title,
                        "duration": duration,
                        "status": "pending_time_selection"
                    },
                    "next_action": "time_preference_needed"
                }
            else:
                response_message += "To complete the scheduling, please use the web interface where I can access your calendar directly."
                
                return {
                    "message": response_message,
                    "success": False,
                    "meeting_details": {
                        "title": title,
                        "duration": duration,
                        "status": "requires_web_interface"
                    },
                    "next_action": "use_web_interface"
                }
                
        except Exception as e:
            logger.error(f"Error scheduling meeting via voice: {e}")
            return {
                "message": "I'm having trouble with meeting scheduling right now. Please try using the web interface or contact your manager directly.",
                "success": False,
                "error": True
            }
    
    def _generate_voice_follow_ups(self, agent_result: Dict[str, Any]) -> List[str]:
        """Generate voice-appropriate follow-up actions."""
        follow_ups = []
        
        current_intent = agent_result.get("current_user_intent", "")
        
        if current_intent == "greeting":
            follow_ups = [
                "Ask about your onboarding progress",
                "Get help with specific tasks",
                "Schedule a meeting with your team"
            ]
        elif current_intent == "task_management":
            follow_ups = [
                "Mark a task as completed",
                "Get help with current challenges",
                "View your next tasks"
            ]
        elif current_intent == "information_request":
            follow_ups = [
                "Ask another question",
                "Get more detailed information",
                "Speak with a human advisor"
            ]
        else:
            follow_ups = [
                "Continue the conversation",
                "Ask for specific help",
                "Check your onboarding status"
            ]
        
        return follow_ups[:3]  # Limit to 3 for voice clarity
    
    async def _save_call_session(self, session_data: Dict[str, Any]) -> None:
        """Save call session data for analytics and follow-up."""
        try:
            # In a production system, this would save to a database
            # For now, we'll log the session summary
            call_id = session_data.get("call_id")
            duration = session_data.get("duration", 0)
            interaction_count = session_data.get("interaction_count", 0)
            
            logger.info(f"Call session saved: {call_id}, duration: {duration}s, interactions: {interaction_count}")
            
            # Could save to Redis, database, or analytics service
            # await redis_client.set(f"call_session:{call_id}", json.dumps(session_data), ex=86400)
            
        except Exception as e:
            logger.error(f"Error saving call session: {e}")
    
    async def _cleanup_session(self, call_id: str, delay: int = 3600) -> None:
        """Clean up session data after delay."""
        try:
            await asyncio.sleep(delay)
            if call_id in self.active_sessions:
                del self.active_sessions[call_id]
                logger.info(f"Cleaned up session for call {call_id}")
        except Exception as e:
            logger.error(f"Error cleaning up session {call_id}: {e}")
    
    async def create_vapi_assistant(self, user_profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a Vapi assistant configuration for onboarding."""
        try:
            if not self.api_key:
                return {"error": "Vapi API key not configured"}
            
            # Customize assistant based on user profile
            assistant_name = "Aura Onboarding Assistant"
            system_message = """You are Aura, an AI onboarding assistant. You help new employees with their onboarding process through voice conversations.

Your capabilities:
- Answer questions about onboarding processes
- Provide status updates on onboarding progress
- Help schedule meetings and appointments
- Guide users through onboarding tasks
- Escalate to human support when needed

Guidelines:
- Be friendly, professional, and helpful
- Keep responses concise for voice interaction
- Ask clarifying questions when needed
- Offer specific next steps
- If you can't help with something, explain how the user can get assistance"""
            
            if user_profile:
                job_role = user_profile.get("job_role", "team member")
                user_name = user_profile.get("name", "there")
                system_message += f"\n\nUser context:\n- Name: {user_name}\n- Role: {job_role}\n- Currently in onboarding process"
            
            assistant_config = {
                "name": assistant_name,
                "model": {
                    "provider": "openai",
                    "model": "gpt-4",
                    "temperature": 0.7,
                    "systemMessage": system_message,
                    "functions": [
                        {
                            "name": "process_user_input",
                            "description": "Process user input through the onboarding system",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "input": {
                                        "type": "string",
                                        "description": "The user's input to process"
                                    }
                                },
                                "required": ["input"]
                            }
                        },
                        {
                            "name": "get_onboarding_status",
                            "description": "Get the user's current onboarding status and progress",
                            "parameters": {
                                "type": "object",
                                "properties": {},
                                "required": []
                            }
                        },
                        {
                            "name": "schedule_meeting",
                            "description": "Help schedule a meeting or appointment",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "meeting_details": {
                                        "type": "object",
                                        "properties": {
                                            "title": {"type": "string"},
                                            "description": {"type": "string"},
                                            "duration": {"type": "number"}
                                        }
                                    }
                                },
                                "required": ["meeting_details"]
                            }
                        }
                    ]
                },
                "voice": self.voice_config,
                "transcriber": self.transcriber_config,
                "firstMessage": "Hello! I'm Aura, your AI onboarding assistant. I'm here to help you with your employee onboarding process. How can I assist you today?"
            }
            
            return {"assistant_config": assistant_config, "success": True}
            
        except Exception as e:
            logger.error(f"Error creating Vapi assistant: {e}")
            return {"error": str(e), "success": False}
    
    def get_active_sessions(self) -> Dict[str, Any]:
        """Get information about active voice sessions."""
        return {
            "total_active": len(self.active_sessions),
            "sessions": {
                call_id: {
                    "start_time": session.get("start_time"),
                    "status": session.get("status"),
                    "interaction_count": session.get("interaction_count", 0),
                    "duration": self._calculate_session_duration(session)
                }
                for call_id, session in self.active_sessions.items()
            }
        }
    
    def _calculate_session_duration(self, session: Dict[str, Any]) -> Optional[int]:
        """Calculate session duration in seconds."""
        try:
            start_time = session.get("start_time")
            if start_time:
                start_dt = datetime.fromisoformat(start_time)
                duration = (datetime.now() - start_dt).total_seconds()
                return int(duration)
        except Exception:
            pass
        return None

# Global Vapi service instance
vapi_service = VapiService()