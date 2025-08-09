import asyncio
import json
import logging
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
from fastapi import WebSocket
from enum import Enum

from ..core.logging import get_logger

logger = get_logger(__name__)

class NotificationType(str, Enum):
    """Types of notifications that can be sent."""
    CHAT_MESSAGE = "chat_message"
    TASK_UPDATE = "task_update"
    PLAN_UPDATED = "plan_updated"
    TOOL_EXECUTED = "tool_executed"
    APPROVAL_REQUEST = "approval_request"
    APPROVAL_RESPONSE = "approval_response"
    SYSTEM_ALERT = "system_alert"
    SESSION_UPDATE = "session_update"
    VOICE_UPDATE = "voice_update"
    ERROR_NOTIFICATION = "error_notification"

class NotificationPriority(str, Enum):
    """Priority levels for notifications."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class NotificationService:
    """Service for managing real-time notifications and WebSocket connections."""
    
    def __init__(self):
        # WebSocket connections by session_id
        self.connections: Dict[str, WebSocket] = {}
        
        # Notification queues for offline sessions
        self.notification_queues: Dict[str, List[Dict[str, Any]]] = {}
        
        # Subscription management
        self.subscriptions: Dict[str, Set[NotificationType]] = {}
        
        # Connection metadata
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
        
        # Notification history (limited in-memory storage)
        self.notification_history: Dict[str, List[Dict[str, Any]]] = {}
        self.max_history_per_session = 100
        
        # Statistics
        self.stats = {
            "total_connections": 0,
            "messages_sent": 0,
            "messages_queued": 0,
            "connection_errors": 0
        }
    
    async def connect_websocket(self, websocket: WebSocket, session_id: str, metadata: Optional[Dict[str, Any]] = None):
        """Connect a WebSocket for a session."""
        try:
            await websocket.accept()
            
            # Store connection
            self.connections[session_id] = websocket
            self.connection_metadata[session_id] = {
                "connected_at": datetime.now().isoformat(),
                "last_activity": datetime.now().isoformat(),
                "metadata": metadata or {}
            }
            
            # Initialize subscriptions (default to all notifications)
            self.subscriptions[session_id] = set(NotificationType)
            
            # Initialize notification history
            if session_id not in self.notification_history:
                self.notification_history[session_id] = []
            
            self.stats["total_connections"] += 1
            
            logger.info(f"WebSocket connected for session {session_id}")
            
            # Send connection confirmation
            await self.send_notification(
                session_id,
                NotificationType.SYSTEM_ALERT,
                {
                    "message": "Real-time notifications connected",
                    "session_id": session_id,
                    "available_types": [t.value for t in NotificationType]
                },
                priority=NotificationPriority.LOW
            )
            
            # Send any queued notifications
            await self._send_queued_notifications(session_id)
            
        except Exception as e:
            logger.error(f"Error connecting WebSocket for session {session_id}: {e}")
            self.stats["connection_errors"] += 1
            raise
    
    def disconnect_websocket(self, session_id: str):
        """Disconnect WebSocket for a session."""
        try:
            if session_id in self.connections:
                del self.connections[session_id]
            
            if session_id in self.connection_metadata:
                del self.connection_metadata[session_id]
            
            if session_id in self.subscriptions:
                del self.subscriptions[session_id]
            
            logger.info(f"WebSocket disconnected for session {session_id}")
            
        except Exception as e:
            logger.error(f"Error disconnecting WebSocket for session {session_id}: {e}")
    
    async def send_notification(
        self,
        session_id: str,
        notification_type: NotificationType,
        data: Dict[str, Any],
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        persistent: bool = True
    ) -> bool:
        """Send a notification to a specific session."""
        try:
            notification = {
                "type": notification_type.value,
                "data": data,
                "priority": priority.value,
                "timestamp": datetime.now().isoformat(),
                "session_id": session_id,
                "id": f"notif_{int(datetime.now().timestamp() * 1000)}"
            }
            
            # Add to history if persistent
            if persistent:
                self._add_to_history(session_id, notification)
            
            # Check if session is subscribed to this notification type
            if session_id in self.subscriptions:
                if notification_type not in self.subscriptions[session_id]:
                    logger.debug(f"Session {session_id} not subscribed to {notification_type}")
                    return False
            
            # Try to send via WebSocket if connected
            if session_id in self.connections:
                try:
                    websocket = self.connections[session_id]
                    await websocket.send_text(json.dumps(notification))
                    
                    # Update connection metadata
                    if session_id in self.connection_metadata:
                        self.connection_metadata[session_id]["last_activity"] = datetime.now().isoformat()
                    
                    self.stats["messages_sent"] += 1
                    logger.debug(f"Sent {notification_type} notification to session {session_id}")
                    return True
                    
                except Exception as e:
                    logger.warning(f"Failed to send WebSocket message to {session_id}: {e}")
                    # Remove broken connection
                    self.disconnect_websocket(session_id)
                    
                    # Queue the notification instead
                    self._queue_notification(session_id, notification)
                    return False
            else:
                # Queue notification for offline session
                self._queue_notification(session_id, notification)
                return False
                
        except Exception as e:
            logger.error(f"Error sending notification to session {session_id}: {e}")
            return False
    
    async def broadcast_notification(
        self,
        notification_type: NotificationType,
        data: Dict[str, Any],
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        session_filter: Optional[List[str]] = None
    ) -> Dict[str, bool]:
        """Broadcast a notification to multiple sessions."""
        try:
            # Determine target sessions
            if session_filter:
                target_sessions = session_filter
            else:
                target_sessions = list(self.connections.keys())
            
            results = {}
            
            # Send to each target session
            for session_id in target_sessions:
                result = await self.send_notification(
                    session_id, notification_type, data, priority
                )
                results[session_id] = result
            
            successful_sends = sum(1 for r in results.values() if r)
            logger.info(f"Broadcast {notification_type} to {len(target_sessions)} sessions, {successful_sends} successful")
            
            return results
            
        except Exception as e:
            logger.error(f"Error broadcasting notification: {e}")
            return {}
    
    async def send_task_update_notification(self, session_id: str, task_data: Dict[str, Any]):
        """Send task update notification."""
        await self.send_notification(
            session_id,
            NotificationType.TASK_UPDATE,
            {
                "task_id": task_data.get("step_id"),
                "title": task_data.get("title"),
                "status": task_data.get("status"),
                "progress": task_data.get("progress", {}),
                "message": f"Task '{task_data.get('title', 'Task')}' updated to {task_data.get('status', 'unknown')}"
            },
            priority=NotificationPriority.MEDIUM
        )
    
    async def send_plan_updated_notification(self, session_id: str, plan_summary: Dict[str, Any]):
        """Send onboarding plan update notification."""
        await self.send_notification(
            session_id,
            NotificationType.PLAN_UPDATED,
            {
                "total_tasks": plan_summary.get("total_tasks", 0),
                "completed_tasks": plan_summary.get("completed_tasks", 0),
                "current_step": plan_summary.get("current_step"),
                "progress_percentage": plan_summary.get("progress_percentage", 0),
                "message": "Your onboarding plan has been updated"
            },
            priority=NotificationPriority.HIGH
        )
    
    async def send_tool_execution_notification(self, session_id: str, tool_result: Dict[str, Any]):
        """Send tool execution result notification."""
        priority = NotificationPriority.HIGH if tool_result.get("success") else NotificationPriority.CRITICAL
        
        await self.send_notification(
            session_id,
            NotificationType.TOOL_EXECUTED,
            {
                "tool_name": tool_result.get("tool_name"),
                "action": tool_result.get("action"),
                "success": tool_result.get("success", False),
                "result": tool_result.get("result", {}),
                "execution_time": tool_result.get("execution_time", 0),
                "message": f"Tool {tool_result.get('tool_name', 'unknown')} {'completed successfully' if tool_result.get('success') else 'failed'}"
            },
            priority=priority
        )
    
    async def send_approval_request_notification(self, session_id: str, approval_data: Dict[str, Any]):
        """Send approval request notification."""
        await self.send_notification(
            session_id,
            NotificationType.APPROVAL_REQUEST,
            {
                "request_id": approval_data.get("request_id"),
                "action_type": approval_data.get("action_type"),
                "action_description": approval_data.get("action_description"),
                "risk_level": approval_data.get("risk_level"),
                "expires_at": approval_data.get("expires_at"),
                "message": f"Approval required for: {approval_data.get('action_description', 'action')}"
            },
            priority=NotificationPriority.HIGH if approval_data.get("risk_level") == "high" else NotificationPriority.MEDIUM
        )
    
    async def send_approval_response_notification(self, session_id: str, response_data: Dict[str, Any]):
        """Send approval response notification."""
        status = response_data.get("status", "unknown")
        priority = NotificationPriority.HIGH if status == "approved" else NotificationPriority.MEDIUM
        
        await self.send_notification(
            session_id,
            NotificationType.APPROVAL_RESPONSE,
            {
                "request_id": response_data.get("request_id"),
                "status": status,
                "approved_by": response_data.get("approved_by"),
                "reason": response_data.get("reason"),
                "message": f"Your approval request has been {status}"
            },
            priority=priority
        )
    
    async def send_error_notification(self, session_id: str, error_data: Dict[str, Any]):
        """Send error notification."""
        await self.send_notification(
            session_id,
            NotificationType.ERROR_NOTIFICATION,
            {
                "error_type": error_data.get("error_type", "unknown"),
                "error_message": error_data.get("error_message"),
                "component": error_data.get("component"),
                "timestamp": error_data.get("timestamp", datetime.now().isoformat()),
                "recovery_suggestions": error_data.get("recovery_suggestions", []),
                "message": f"Error in {error_data.get('component', 'system')}: {error_data.get('error_message', 'Unknown error')}"
            },
            priority=NotificationPriority.CRITICAL
        )
    
    async def send_voice_update_notification(self, session_id: str, voice_data: Dict[str, Any]):
        """Send voice interaction update notification."""
        await self.send_notification(
            session_id,
            NotificationType.VOICE_UPDATE,
            {
                "call_id": voice_data.get("call_id"),
                "status": voice_data.get("status"),
                "duration": voice_data.get("duration"),
                "transcript_update": voice_data.get("transcript_update"),
                "message": f"Voice call {voice_data.get('status', 'updated')}"
            },
            priority=NotificationPriority.LOW
        )
    
    def update_subscriptions(self, session_id: str, notification_types: List[NotificationType]):
        """Update notification subscriptions for a session."""
        try:
            self.subscriptions[session_id] = set(notification_types)
            logger.info(f"Updated subscriptions for session {session_id}: {[t.value for t in notification_types]}")
            
        except Exception as e:
            logger.error(f"Error updating subscriptions for session {session_id}: {e}")
    
    def get_notification_history(self, session_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get notification history for a session."""
        try:
            history = self.notification_history.get(session_id, [])
            
            if limit:
                history = history[-limit:]
            
            return history
            
        except Exception as e:
            logger.error(f"Error getting notification history for session {session_id}: {e}")
            return []
    
    def get_connection_status(self, session_id: str) -> Dict[str, Any]:
        """Get connection status for a session."""
        try:
            is_connected = session_id in self.connections
            metadata = self.connection_metadata.get(session_id, {})
            subscriptions = list(self.subscriptions.get(session_id, []))
            queued_count = len(self.notification_queues.get(session_id, []))
            
            return {
                "session_id": session_id,
                "connected": is_connected,
                "connection_metadata": metadata,
                "subscriptions": [s.value if hasattr(s, 'value') else str(s) for s in subscriptions],
                "queued_notifications": queued_count,
                "notification_history_count": len(self.notification_history.get(session_id, []))
            }
            
        except Exception as e:
            logger.error(f"Error getting connection status for session {session_id}: {e}")
            return {"session_id": session_id, "connected": False, "error": str(e)}
    
    def get_service_statistics(self) -> Dict[str, Any]:
        """Get service statistics and health information."""
        try:
            return {
                "active_connections": len(self.connections),
                "total_sessions": len(set(list(self.connections.keys()) + list(self.notification_queues.keys()))),
                "queued_notifications": sum(len(queue) for queue in self.notification_queues.values()),
                "statistics": self.stats.copy(),
                "service_health": "healthy" if len(self.connections) >= 0 else "degraded",
                "notification_types": [t.value for t in NotificationType],
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting service statistics: {e}")
            return {"error": str(e)}
    
    # Private helper methods
    
    def _queue_notification(self, session_id: str, notification: Dict[str, Any]):
        """Queue notification for offline session."""
        try:
            if session_id not in self.notification_queues:
                self.notification_queues[session_id] = []
            
            self.notification_queues[session_id].append(notification)
            self.stats["messages_queued"] += 1
            
            # Limit queue size
            max_queue_size = 50
            if len(self.notification_queues[session_id]) > max_queue_size:
                self.notification_queues[session_id] = self.notification_queues[session_id][-max_queue_size:]
            
            logger.debug(f"Queued notification for offline session {session_id}")
            
        except Exception as e:
            logger.error(f"Error queuing notification for session {session_id}: {e}")
    
    async def _send_queued_notifications(self, session_id: str):
        """Send queued notifications when session comes online."""
        try:
            if session_id not in self.notification_queues:
                return
            
            queued_notifications = self.notification_queues[session_id]
            if not queued_notifications:
                return
            
            websocket = self.connections.get(session_id)
            if not websocket:
                return
            
            # Send queued notifications
            sent_count = 0
            for notification in queued_notifications:
                try:
                    await websocket.send_text(json.dumps(notification))
                    sent_count += 1
                    self.stats["messages_sent"] += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to send queued notification to {session_id}: {e}")
                    break
            
            # Clear sent notifications
            del self.notification_queues[session_id]
            
            logger.info(f"Sent {sent_count} queued notifications to session {session_id}")
            
        except Exception as e:
            logger.error(f"Error sending queued notifications to session {session_id}: {e}")
    
    def _add_to_history(self, session_id: str, notification: Dict[str, Any]):
        """Add notification to history."""
        try:
            if session_id not in self.notification_history:
                self.notification_history[session_id] = []
            
            self.notification_history[session_id].append(notification)
            
            # Limit history size
            if len(self.notification_history[session_id]) > self.max_history_per_session:
                self.notification_history[session_id] = self.notification_history[session_id][-self.max_history_per_session:]
            
        except Exception as e:
            logger.error(f"Error adding notification to history for session {session_id}: {e}")
    
    async def cleanup_inactive_sessions(self, max_age_hours: int = 24) -> int:
        """Clean up inactive sessions and return count of cleaned sessions."""
        try:
            cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
            cleaned_count = 0
            
            # Clean up connection metadata
            sessions_to_remove = []
            for session_id, metadata in self.connection_metadata.items():
                try:
                    connected_at = datetime.fromisoformat(metadata.get("connected_at", "")).timestamp()
                    if connected_at < cutoff_time:
                        sessions_to_remove.append(session_id)
                except Exception:
                    sessions_to_remove.append(session_id)  # Remove invalid entries
            
            for session_id in sessions_to_remove:
                self.disconnect_websocket(session_id)
                
                # Clean up queues and history
                if session_id in self.notification_queues:
                    del self.notification_queues[session_id]
                
                if session_id in self.notification_history:
                    del self.notification_history[session_id]
                
                cleaned_count += 1
            
            logger.info(f"Cleaned up {cleaned_count} inactive notification sessions")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error during notification session cleanup: {e}")
            return 0

# Global notification service instance
notification_service = NotificationService()