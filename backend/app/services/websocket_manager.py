import asyncio
import json
import logging
from typing import Dict, Any, Optional, List, Set
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect, Query, HTTPException, status
from enum import Enum

from .notification_service import notification_service, NotificationType, NotificationPriority
from ..core.auth import verify_websocket_token
from ..core.logging import get_logger

logger = get_logger(__name__)

class ConnectionState(str, Enum):
    """WebSocket connection states."""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATED = "authenticated"
    DISCONNECTED = "disconnected"
    ERROR = "error"

class WebSocketManager:
    """Centralized WebSocket manager with authentication and real-time notifications."""
    
    def __init__(self):
        # Active connections by session_id
        self.active_connections: Dict[str, WebSocket] = {}
        
        # Connection metadata
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
        
        # Authentication status
        self.authenticated_sessions: Set[str] = set()
        
        # User information for authenticated connections
        self.session_users: Dict[str, Dict[str, Any]] = {}
        
        # Subscription management per session
        self.session_subscriptions: Dict[str, Set[NotificationType]] = {}
        
        # Connection statistics
        self.stats = {
            "total_connections": 0,
            "active_connections": 0,
            "authenticated_connections": 0,
            "messages_sent": 0,
            "authentication_failures": 0,
            "connection_errors": 0
        }
    
    async def connect(
        self, 
        websocket: WebSocket, 
        session_id: str, 
        token: Optional[str] = None,
        client_info: Optional[Dict[str, Any]] = None
    ):
        """Accept and manage a new WebSocket connection."""
        try:
            await websocket.accept()
            
            # Store connection
            self.active_connections[session_id] = websocket
            self.connection_metadata[session_id] = {
                "state": ConnectionState.CONNECTED,
                "connected_at": datetime.now().isoformat(),
                "last_activity": datetime.now().isoformat(),
                "client_info": client_info or {},
                "ip_address": getattr(websocket.client, 'host', 'unknown') if websocket.client else 'unknown',
                "user_agent": client_info.get("user_agent", "unknown") if client_info else "unknown"
            }
            
            # Initialize default subscriptions
            self.session_subscriptions[session_id] = set(NotificationType)
            
            self.stats["total_connections"] += 1
            self.stats["active_connections"] += 1
            
            logger.info(f"WebSocket connected for session {session_id}")
            
            # Send connection confirmation
            await self.send_system_message(session_id, {
                "type": "connection_established",
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
                "message": "WebSocket connection established",
                "authentication_required": True
            })
            
            # Attempt authentication if token provided
            if token:
                await self.authenticate_connection(session_id, token)
            
            # Connect to notification service
            await notification_service.connect_websocket(
                websocket, session_id, self.connection_metadata[session_id]
            )
            
        except Exception as e:
            logger.error(f"Error connecting WebSocket for session {session_id}: {e}")
            self.stats["connection_errors"] += 1
            await self.disconnect(session_id)
            raise
    
    async def authenticate_connection(self, session_id: str, token: str) -> bool:
        """Authenticate a WebSocket connection using JWT token."""
        try:
            if session_id not in self.active_connections:
                logger.warning(f"Attempted to authenticate non-existent session {session_id}")
                return False
            
            # Verify token
            user_data = verify_websocket_token(token)
            
            if not user_data:
                logger.warning(f"Authentication failed for session {session_id}")
                self.stats["authentication_failures"] += 1
                
                await self.send_system_message(session_id, {
                    "type": "authentication_failed",
                    "message": "Invalid or expired token",
                    "timestamp": datetime.now().isoformat()
                })
                
                return False
            
            # Store authenticated user data
            self.authenticated_sessions.add(session_id)
            self.session_users[session_id] = user_data
            
            # Update connection state
            if session_id in self.connection_metadata:
                self.connection_metadata[session_id]["state"] = ConnectionState.AUTHENTICATED
                self.connection_metadata[session_id]["user_id"] = user_data.get("user_id")
                self.connection_metadata[session_id]["user_email"] = user_data.get("email")
                self.connection_metadata[session_id]["user_role"] = user_data.get("role")
                self.connection_metadata[session_id]["authenticated_at"] = datetime.now().isoformat()
            
            self.stats["authenticated_connections"] += 1
            
            logger.info(f"WebSocket authenticated for session {session_id}, user: {user_data.get('email')}")
            
            # Send authentication success
            await self.send_system_message(session_id, {
                "type": "authentication_success",
                "user_info": {
                    "user_id": user_data.get("user_id"),
                    "email": user_data.get("email"),
                    "full_name": user_data.get("full_name"),
                    "role": user_data.get("role")
                },
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
                "message": "Authentication successful"
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Error authenticating WebSocket session {session_id}: {e}")
            self.stats["authentication_failures"] += 1
            
            await self.send_system_message(session_id, {
                "type": "authentication_error",
                "message": "Authentication error occurred",
                "timestamp": datetime.now().isoformat()
            })
            
            return False
    
    async def disconnect(self, session_id: str):
        """Disconnect and clean up a WebSocket connection."""
        try:
            # Disconnect from notification service
            notification_service.disconnect_websocket(session_id)
            
            # Clean up connection data
            if session_id in self.active_connections:
                del self.active_connections[session_id]
                self.stats["active_connections"] -= 1
            
            if session_id in self.authenticated_sessions:
                self.authenticated_sessions.remove(session_id)
                self.stats["authenticated_connections"] -= 1
            
            if session_id in self.session_users:
                del self.session_users[session_id]
            
            if session_id in self.session_subscriptions:
                del self.session_subscriptions[session_id]
            
            if session_id in self.connection_metadata:
                del self.connection_metadata[session_id]
            
            logger.info(f"WebSocket disconnected for session {session_id}")
            
        except Exception as e:
            logger.error(f"Error disconnecting WebSocket for session {session_id}: {e}")
    
    async def send_message(
        self, 
        session_id: str, 
        message: Dict[str, Any],
        require_auth: bool = True
    ) -> bool:
        """Send a message to a specific WebSocket connection."""
        try:
            if session_id not in self.active_connections:
                logger.warning(f"Attempted to send message to non-existent session {session_id}")
                return False
            
            # Check authentication requirement
            if require_auth and session_id not in self.authenticated_sessions:
                logger.warning(f"Attempted to send message to unauthenticated session {session_id}")
                return False
            
            websocket = self.active_connections[session_id]
            
            # Add metadata
            message_with_meta = {
                **message,
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
                "message_id": f"msg_{int(datetime.now().timestamp() * 1000)}"
            }
            
            # Send message
            await websocket.send_text(json.dumps(message_with_meta))
            
            # Update activity timestamp
            if session_id in self.connection_metadata:
                self.connection_metadata[session_id]["last_activity"] = datetime.now().isoformat()
            
            self.stats["messages_sent"] += 1
            
            logger.debug(f"Sent message to session {session_id}: {message.get('type', 'unknown')}")
            return True
            
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected while sending message to session {session_id}")
            await self.disconnect(session_id)
            return False
        except Exception as e:
            logger.error(f"Error sending message to session {session_id}: {e}")
            await self.disconnect(session_id)
            return False
    
    async def send_system_message(self, session_id: str, data: Dict[str, Any]) -> bool:
        """Send a system message (doesn't require authentication)."""
        system_message = {
            "category": "system",
            "type": data.get("type", "system_message"),
            "data": data
        }
        return await self.send_message(session_id, system_message, require_auth=False)
    
    async def broadcast_message(
        self, 
        message: Dict[str, Any], 
        target_sessions: Optional[List[str]] = None,
        require_auth: bool = True,
        role_filter: Optional[str] = None
    ) -> Dict[str, bool]:
        """Broadcast a message to multiple WebSocket connections."""
        try:
            # Determine target sessions
            if target_sessions:
                sessions = target_sessions
            else:
                if require_auth:
                    sessions = list(self.authenticated_sessions)
                else:
                    sessions = list(self.active_connections.keys())
            
            # Apply role filter if specified
            if role_filter:
                filtered_sessions = []
                for session_id in sessions:
                    user_data = self.session_users.get(session_id, {})
                    if user_data.get("role") == role_filter:
                        filtered_sessions.append(session_id)
                sessions = filtered_sessions
            
            # Send to each session
            results = {}
            for session_id in sessions:
                result = await self.send_message(session_id, message, require_auth)
                results[session_id] = result
            
            successful_sends = sum(1 for r in results.values() if r)
            logger.info(f"Broadcast message to {len(sessions)} sessions, {successful_sends} successful")
            
            return results
            
        except Exception as e:
            logger.error(f"Error broadcasting message: {e}")
            return {}
    
    async def handle_incoming_message(self, session_id: str, message: str):
        """Handle incoming WebSocket message from client."""
        try:
            data = json.loads(message)
            message_type = data.get("type", "unknown")
            
            logger.debug(f"Received message from session {session_id}: {message_type}")
            
            # Update activity timestamp
            if session_id in self.connection_metadata:
                self.connection_metadata[session_id]["last_activity"] = datetime.now().isoformat()
            
            # Handle different message types
            if message_type == "authenticate":
                token = data.get("token")
                if token:
                    await self.authenticate_connection(session_id, token)
                else:
                    await self.send_system_message(session_id, {
                        "type": "authentication_error",
                        "message": "Token is required for authentication"
                    })
            
            elif message_type == "ping":
                await self.send_system_message(session_id, {
                    "type": "pong",
                    "timestamp": datetime.now().isoformat()
                })
            
            elif message_type == "subscribe":
                notification_types = data.get("notification_types", [])
                await self.update_subscriptions(session_id, notification_types)
            
            elif message_type == "get_history":
                limit = data.get("limit", 10)
                history = notification_service.get_notification_history(session_id, limit)
                await self.send_system_message(session_id, {
                    "type": "notification_history",
                    "history": history,
                    "count": len(history)
                })
            
            elif message_type == "chat_message":
                # Forward to chat handling logic (would integrate with agent processing)
                await self.handle_chat_message(session_id, data)
            
            else:
                logger.warning(f"Unknown message type from session {session_id}: {message_type}")
                await self.send_system_message(session_id, {
                    "type": "error",
                    "message": f"Unknown message type: {message_type}"
                })
            
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received from session {session_id}")
            await self.send_system_message(session_id, {
                "type": "error",
                "message": "Invalid JSON format"
            })
        except Exception as e:
            logger.error(f"Error handling message from session {session_id}: {e}")
            await self.send_system_message(session_id, {
                "type": "error",
                "message": "Message processing error"
            })
    
    async def update_subscriptions(self, session_id: str, notification_types: List[str]):
        """Update notification subscriptions for a session."""
        try:
            if session_id not in self.authenticated_sessions:
                await self.send_system_message(session_id, {
                    "type": "error",
                    "message": "Authentication required to manage subscriptions"
                })
                return
            
            # Convert string types to enum types
            valid_types = []
            for type_str in notification_types:
                try:
                    notification_type = NotificationType(type_str)
                    valid_types.append(notification_type)
                except ValueError:
                    logger.warning(f"Invalid notification type: {type_str}")
            
            # Update subscriptions
            self.session_subscriptions[session_id] = set(valid_types)
            notification_service.update_subscriptions(session_id, valid_types)
            
            await self.send_system_message(session_id, {
                "type": "subscriptions_updated",
                "subscriptions": [t.value for t in valid_types],
                "message": f"Updated subscriptions: {len(valid_types)} types"
            })
            
            logger.info(f"Updated subscriptions for session {session_id}: {len(valid_types)} types")
            
        except Exception as e:
            logger.error(f"Error updating subscriptions for session {session_id}: {e}")
            await self.send_system_message(session_id, {
                "type": "error",
                "message": "Failed to update subscriptions"
            })
    
    async def handle_chat_message(self, session_id: str, data: Dict[str, Any]):
        """Handle chat message from WebSocket client."""
        try:
            if session_id not in self.authenticated_sessions:
                await self.send_system_message(session_id, {
                    "type": "error",
                    "message": "Authentication required for chat"
                })
                return
            
            user_data = self.session_users.get(session_id, {})
            message = data.get("message", "")
            
            if not message.strip():
                await self.send_system_message(session_id, {
                    "type": "error",
                    "message": "Message cannot be empty"
                })
                return
            
            # Send acknowledgment
            await self.send_system_message(session_id, {
                "type": "message_received",
                "message_id": data.get("message_id"),
                "timestamp": datetime.now().isoformat()
            })
            
            # This would integrate with the agent processing system
            # For now, just echo back the message
            await self.send_message(session_id, {
                "category": "chat",
                "type": "agent_response",
                "data": {
                    "message": f"Received your message: {message}",
                    "user_id": user_data.get("user_id"),
                    "timestamp": datetime.now().isoformat()
                }
            })
            
        except Exception as e:
            logger.error(f"Error handling chat message from session {session_id}: {e}")
            await self.send_system_message(session_id, {
                "type": "error",
                "message": "Failed to process chat message"
            })
    
    def get_connection_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get connection information for a session."""
        try:
            if session_id not in self.active_connections:
                return None
            
            metadata = self.connection_metadata.get(session_id, {})
            user_data = self.session_users.get(session_id, {})
            subscriptions = self.session_subscriptions.get(session_id, set())
            
            return {
                "session_id": session_id,
                "state": metadata.get("state"),
                "connected_at": metadata.get("connected_at"),
                "last_activity": metadata.get("last_activity"),
                "authenticated": session_id in self.authenticated_sessions,
                "user_info": {
                    "user_id": user_data.get("user_id"),
                    "email": user_data.get("email"),
                    "role": user_data.get("role")
                } if user_data else None,
                "subscriptions": [s.value for s in subscriptions],
                "client_info": metadata.get("client_info", {}),
                "ip_address": metadata.get("ip_address"),
                "user_agent": metadata.get("user_agent")
            }
            
        except Exception as e:
            logger.error(f"Error getting connection info for session {session_id}: {e}")
            return None
    
    def get_service_stats(self) -> Dict[str, Any]:
        """Get WebSocket service statistics."""
        try:
            return {
                **self.stats,
                "authenticated_percentage": (
                    self.stats["authenticated_connections"] / self.stats["active_connections"] * 100
                ) if self.stats["active_connections"] > 0 else 0,
                "service_health": "healthy" if self.stats["active_connections"] >= 0 else "degraded",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting service stats: {e}")
            return {"error": str(e)}
    
    async def cleanup_inactive_connections(self, max_age_hours: int = 24) -> int:
        """Clean up inactive connections and return count of cleaned connections."""
        try:
            cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
            cleaned_count = 0
            
            sessions_to_remove = []
            for session_id, metadata in self.connection_metadata.items():
                try:
                    connected_at = datetime.fromisoformat(metadata.get("connected_at", "")).timestamp()
                    if connected_at < cutoff_time:
                        sessions_to_remove.append(session_id)
                except Exception:
                    sessions_to_remove.append(session_id)  # Remove invalid entries
            
            for session_id in sessions_to_remove:
                await self.disconnect(session_id)
                cleaned_count += 1
            
            logger.info(f"Cleaned up {cleaned_count} inactive WebSocket connections")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error during WebSocket connection cleanup: {e}")
            return 0

# Global WebSocket manager instance
websocket_manager = WebSocketManager()