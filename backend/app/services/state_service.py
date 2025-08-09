import redis
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import pickle
import uuid

from ..core.config import settings
from ..core.logging import get_logger

logger = get_logger(__name__)

class StateService:
    """Redis-based state management service for agent persistence."""
    
    def __init__(self):
        self.redis_client = None
        self._initialize_redis()
        
        # Cache settings
        self.default_ttl = 86400  # 24 hours
        self.session_ttl = 7200   # 2 hours for active sessions
        self.long_term_ttl = 604800  # 1 week for completed sessions
        
        # Key prefixes
        self.prefixes = {
            "agent_state": "aura:agent:",
            "conversation": "aura:conversation:",
            "onboarding_plan": "aura:plan:",
            "user_profile": "aura:user:",
            "tool_state": "aura:tools:",
            "approvals": "aura:approvals:",
            "session_meta": "aura:session:",
            "analytics": "aura:analytics:"
        }
    
    def _initialize_redis(self):
        """Initialize Redis connection."""
        try:
            self.redis_client = redis.from_url(
                settings.redis_url,
                decode_responses=False,  # We'll handle encoding manually
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # Test connection
            self.redis_client.ping()
            logger.info("Redis connection established successfully")
            
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis_client = None
        except Exception as e:
            logger.error(f"Unexpected error connecting to Redis: {e}")
            self.redis_client = None
    
    def is_available(self) -> bool:
        """Check if Redis is available."""
        try:
            return self.redis_client is not None and self.redis_client.ping()
        except Exception:
            return False
    
    # Agent State Management
    
    async def save_agent_state(self, session_id: str, agent_state: Dict[str, Any]) -> bool:
        """Save complete agent state to Redis."""
        try:
            if not self.is_available():
                logger.warning("Redis not available, cannot save agent state")
                return False
            
            key = f"{self.prefixes['agent_state']}{session_id}"
            
            # Add metadata
            state_with_meta = {
                "state": agent_state,
                "session_id": session_id,
                "last_updated": datetime.now().isoformat(),
                "version": 1
            }
            
            # Serialize and save
            serialized_state = pickle.dumps(state_with_meta)
            
            # Set with TTL based on session activity
            ttl = self._calculate_state_ttl(agent_state)
            
            result = self.redis_client.setex(key, ttl, serialized_state)
            
            if result:
                logger.debug(f"Saved agent state for session {session_id}")
                
                # Also save session metadata
                await self._save_session_metadata(session_id, agent_state)
                
            return result
            
        except Exception as e:
            logger.error(f"Error saving agent state for session {session_id}: {e}")
            return False
    
    async def load_agent_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load agent state from Redis."""
        try:
            if not self.is_available():
                logger.warning("Redis not available, cannot load agent state")
                return None
            
            key = f"{self.prefixes['agent_state']}{session_id}"
            
            serialized_state = self.redis_client.get(key)
            if not serialized_state:
                logger.debug(f"No agent state found for session {session_id}")
                return None
            
            # Deserialize
            state_with_meta = pickle.loads(serialized_state)
            
            # Update last accessed time
            state_with_meta["last_accessed"] = datetime.now().isoformat()
            await self.save_agent_state(session_id, state_with_meta["state"])
            
            logger.debug(f"Loaded agent state for session {session_id}")
            return state_with_meta["state"]
            
        except Exception as e:
            logger.error(f"Error loading agent state for session {session_id}: {e}")
            return None
    
    async def delete_agent_state(self, session_id: str) -> bool:
        """Delete agent state from Redis."""
        try:
            if not self.is_available():
                return False
            
            keys_to_delete = [
                f"{self.prefixes['agent_state']}{session_id}",
                f"{self.prefixes['conversation']}{session_id}",
                f"{self.prefixes['onboarding_plan']}{session_id}",
                f"{self.prefixes['user_profile']}{session_id}",
                f"{self.prefixes['tool_state']}{session_id}",
                f"{self.prefixes['session_meta']}{session_id}"
            ]
            
            deleted_count = self.redis_client.delete(*keys_to_delete)
            
            logger.info(f"Deleted {deleted_count} keys for session {session_id}")
            return deleted_count > 0
            
        except Exception as e:
            logger.error(f"Error deleting agent state for session {session_id}: {e}")
            return False
    
    # Conversation Management
    
    async def save_conversation_history(self, session_id: str, conversation_history: List[Dict[str, Any]]) -> bool:
        """Save conversation history separately for efficient access."""
        try:
            if not self.is_available():
                return False
            
            key = f"{self.prefixes['conversation']}{session_id}"
            
            conversation_data = {
                "session_id": session_id,
                "messages": conversation_history,
                "total_messages": len(conversation_history),
                "last_updated": datetime.now().isoformat()
            }
            
            serialized_data = json.dumps(conversation_data, default=str)
            result = self.redis_client.setex(key, self.session_ttl, serialized_data)
            
            logger.debug(f"Saved {len(conversation_history)} messages for session {session_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error saving conversation history: {e}")
            return False
    
    async def load_conversation_history(self, session_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Load conversation history from Redis."""
        try:
            if not self.is_available():
                return []
            
            key = f"{self.prefixes['conversation']}{session_id}"
            
            data = self.redis_client.get(key)
            if not data:
                return []
            
            conversation_data = json.loads(data.decode('utf-8'))
            messages = conversation_data.get("messages", [])
            
            # Apply limit if specified
            if limit and len(messages) > limit:
                messages = messages[-limit:]
            
            return messages
            
        except Exception as e:
            logger.error(f"Error loading conversation history: {e}")
            return []
    
    # Onboarding Plan Management
    
    async def save_onboarding_plan(self, session_id: str, plan_data: Dict[str, Any]) -> bool:
        """Save onboarding plan data."""
        try:
            if not self.is_available():
                return False
            
            key = f"{self.prefixes['onboarding_plan']}{session_id}"
            
            plan_with_meta = {
                "session_id": session_id,
                "plan": plan_data,
                "created_at": plan_data.get("created_at", datetime.now().isoformat()),
                "last_updated": datetime.now().isoformat()
            }
            
            serialized_data = json.dumps(plan_with_meta, default=str)
            result = self.redis_client.setex(key, self.default_ttl, serialized_data)
            
            return result
            
        except Exception as e:
            logger.error(f"Error saving onboarding plan: {e}")
            return False
    
    async def load_onboarding_plan(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load onboarding plan data."""
        try:
            if not self.is_available():
                return None
            
            key = f"{self.prefixes['onboarding_plan']}{session_id}"
            
            data = self.redis_client.get(key)
            if not data:
                return None
            
            plan_data = json.loads(data.decode('utf-8'))
            return plan_data.get("plan")
            
        except Exception as e:
            logger.error(f"Error loading onboarding plan: {e}")
            return None
    
    # User Profile Management
    
    async def save_user_profile(self, user_id: str, profile_data: Dict[str, Any]) -> bool:
        """Save user profile data."""
        try:
            if not self.is_available():
                return False
            
            key = f"{self.prefixes['user_profile']}{user_id}"
            
            profile_with_meta = {
                "user_id": user_id,
                "profile": profile_data,
                "created_at": profile_data.get("created_at", datetime.now().isoformat()),
                "last_updated": datetime.now().isoformat()
            }
            
            serialized_data = json.dumps(profile_with_meta, default=str)
            result = self.redis_client.setex(key, self.long_term_ttl, serialized_data)
            
            return result
            
        except Exception as e:
            logger.error(f"Error saving user profile: {e}")
            return False
    
    async def load_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Load user profile data."""
        try:
            if not self.is_available():
                return None
            
            key = f"{self.prefixes['user_profile']}{user_id}"
            
            data = self.redis_client.get(key)
            if not data:
                return None
            
            profile_data = json.loads(data.decode('utf-8'))
            return profile_data.get("profile")
            
        except Exception as e:
            logger.error(f"Error loading user profile: {e}")
            return None
    
    # Tool State Management
    
    async def save_tool_state(self, session_id: str, tool_states: Dict[str, Any]) -> bool:
        """Save tool execution states."""
        try:
            if not self.is_available():
                return False
            
            key = f"{self.prefixes['tool_state']}{session_id}"
            
            tool_data = {
                "session_id": session_id,
                "tool_states": tool_states,
                "last_updated": datetime.now().isoformat()
            }
            
            serialized_data = json.dumps(tool_data, default=str)
            result = self.redis_client.setex(key, self.session_ttl, serialized_data)
            
            return result
            
        except Exception as e:
            logger.error(f"Error saving tool state: {e}")
            return False
    
    async def load_tool_state(self, session_id: str) -> Dict[str, Any]:
        """Load tool execution states."""
        try:
            if not self.is_available():
                return {}
            
            key = f"{self.prefixes['tool_state']}{session_id}"
            
            data = self.redis_client.get(key)
            if not data:
                return {}
            
            tool_data = json.loads(data.decode('utf-8'))
            return tool_data.get("tool_states", {})
            
        except Exception as e:
            logger.error(f"Error loading tool state: {e}")
            return {}
    
    # Session Management
    
    async def _save_session_metadata(self, session_id: str, agent_state: Dict[str, Any]) -> bool:
        """Save session metadata for management and analytics."""
        try:
            key = f"{self.prefixes['session_meta']}{session_id}"
            
            metadata = {
                "session_id": session_id,
                "user_id": agent_state.get("user_profile", {}).get("user_id"),
                "job_role": agent_state.get("job_role"),
                "created_at": agent_state.get("created_at", datetime.now().isoformat()),
                "last_activity": datetime.now().isoformat(),
                "message_count": len(agent_state.get("conversation_history", [])),
                "task_count": len(agent_state.get("onboarding_plan_steps", [])),
                "completed_tasks": len(agent_state.get("completed_tasks", [])),
                "current_step": agent_state.get("current_step"),
                "active_llm": agent_state.get("active_llm"),
                "status": "active"
            }
            
            serialized_data = json.dumps(metadata, default=str)
            result = self.redis_client.setex(key, self.default_ttl, serialized_data)
            
            return result
            
        except Exception as e:
            logger.error(f"Error saving session metadata: {e}")
            return False
    
    async def get_active_sessions(self) -> List[Dict[str, Any]]:
        """Get list of all active sessions."""
        try:
            if not self.is_available():
                return []
            
            pattern = f"{self.prefixes['session_meta']}*"
            session_keys = self.redis_client.keys(pattern)
            
            sessions = []
            for key in session_keys:
                try:
                    data = self.redis_client.get(key)
                    if data:
                        session_data = json.loads(data.decode('utf-8'))
                        sessions.append(session_data)
                except Exception as e:
                    logger.warning(f"Error loading session metadata for key {key}: {e}")
                    continue
            
            # Sort by last activity
            sessions.sort(key=lambda x: x.get("last_activity", ""), reverse=True)
            
            return sessions
            
        except Exception as e:
            logger.error(f"Error getting active sessions: {e}")
            return []
    
    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions and return count of cleaned sessions."""
        try:
            if not self.is_available():
                return 0
            
            # Get all session metadata
            sessions = await self.get_active_sessions()
            cleaned_count = 0
            
            cutoff_time = datetime.now() - timedelta(hours=24)
            
            for session in sessions:
                try:
                    last_activity = datetime.fromisoformat(session.get("last_activity", ""))
                    
                    if last_activity < cutoff_time:
                        session_id = session.get("session_id")
                        if await self.delete_agent_state(session_id):
                            cleaned_count += 1
                            logger.info(f"Cleaned up expired session: {session_id}")
                
                except Exception as e:
                    logger.warning(f"Error processing session for cleanup: {e}")
                    continue
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error during session cleanup: {e}")
            return 0
    
    # Analytics and Monitoring
    
    async def save_analytics_event(self, event_type: str, event_data: Dict[str, Any]) -> bool:
        """Save analytics event for monitoring and insights."""
        try:
            if not self.is_available():
                return False
            
            event_id = str(uuid.uuid4())
            key = f"{self.prefixes['analytics']}{event_type}:{event_id}"
            
            analytics_event = {
                "event_id": event_id,
                "event_type": event_type,
                "data": event_data,
                "timestamp": datetime.now().isoformat()
            }
            
            serialized_data = json.dumps(analytics_event, default=str)
            
            # Analytics events have shorter TTL
            result = self.redis_client.setex(key, 86400 * 7, serialized_data)  # 1 week
            
            return result
            
        except Exception as e:
            logger.error(f"Error saving analytics event: {e}")
            return False
    
    async def get_analytics_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get analytics summary for the specified time period."""
        try:
            if not self.is_available():
                return {}
            
            pattern = f"{self.prefixes['analytics']}*"
            event_keys = self.redis_client.keys(pattern)
            
            # Time filter
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            events_by_type = {}
            total_events = 0
            
            for key in event_keys:
                try:
                    data = self.redis_client.get(key)
                    if data:
                        event = json.loads(data.decode('utf-8'))
                        event_time = datetime.fromisoformat(event.get("timestamp", ""))
                        
                        if event_time >= cutoff_time:
                            event_type = event.get("event_type", "unknown")
                            events_by_type[event_type] = events_by_type.get(event_type, 0) + 1
                            total_events += 1
                
                except Exception as e:
                    logger.warning(f"Error processing analytics event: {e}")
                    continue
            
            return {
                "time_period_hours": hours,
                "total_events": total_events,
                "events_by_type": events_by_type,
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting analytics summary: {e}")
            return {}
    
    # Cache Management
    
    def _calculate_state_ttl(self, agent_state: Dict[str, Any]) -> int:
        """Calculate appropriate TTL based on agent state activity."""
        # Active sessions (recent messages) get longer TTL
        conversation_history = agent_state.get("conversation_history", [])
        
        if not conversation_history:
            return self.default_ttl
        
        try:
            # Check if there's recent activity
            latest_message = conversation_history[-1]
            message_time = datetime.fromisoformat(latest_message.get("timestamp", ""))
            time_since_last = datetime.now() - message_time
            
            if time_since_last < timedelta(hours=1):
                return self.session_ttl  # Active session
            elif time_since_last < timedelta(hours=12):
                return self.default_ttl  # Recent session
            else:
                return self.default_ttl // 2  # Older session
                
        except Exception:
            return self.default_ttl
    
    async def invalidate_cache(self, pattern: str) -> int:
        """Invalidate cache entries matching pattern."""
        try:
            if not self.is_available():
                return 0
            
            keys = self.redis_client.keys(pattern)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
            
        except Exception as e:
            logger.error(f"Error invalidating cache with pattern {pattern}: {e}")
            return 0
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get Redis connection information and statistics."""
        try:
            if not self.is_available():
                return {"connected": False, "error": "Redis not available"}
            
            info = self.redis_client.info()
            
            return {
                "connected": True,
                "redis_version": info.get("redis_version"),
                "used_memory": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "total_commands_processed": info.get("total_commands_processed"),
                "keyspace": info.get("db0", {}),
                "server_time": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting Redis connection info: {e}")
            return {"connected": False, "error": str(e)}

# Global state service instance
state_service = StateService()