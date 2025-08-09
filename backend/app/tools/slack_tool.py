from typing import Dict, Any, List, Optional
import logging
from datetime import datetime
import json

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from .base_tool import BaseTool, ToolExecutionResult
from ..core.config import settings
from ..core.logging import get_logger

logger = get_logger(__name__)

class SlackTool(BaseTool):
    """Slack integration tool for team communication and notifications."""
    
    def __init__(self):
        super().__init__(
            name="slack_tool",
            description="Slack integration for team communication, notifications, and onboarding workflows"
        )
        
        self.client = None
        self.bot_user_id = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Slack client."""
        try:
            if not settings.slack_bot_token:
                logger.warning("Slack bot token not configured")
                return
            
            self.client = WebClient(token=settings.slack_bot_token)
            
            # Test the connection and get bot info
            response = self.client.auth_test()
            self.bot_user_id = response["user_id"]
            
            logger.info(f"Slack client initialized successfully. Bot ID: {self.bot_user_id}")
            
        except SlackApiError as e:
            logger.error(f"Error initializing Slack client: {e}")
            self.client = None
        except Exception as e:
            logger.error(f"Unexpected error initializing Slack: {e}")
            self.client = None
    
    async def execute(self, action: str, parameters: Dict[str, Any]) -> ToolExecutionResult:
        """Execute Slack actions."""
        try:
            if action == "send_message":
                return await self._send_message(parameters)
            elif action == "send_welcome_message":
                return await self._send_welcome_message(parameters)
            elif action == "create_channel":
                return await self._create_channel(parameters)
            elif action == "add_to_channel":
                return await self._add_to_channel(parameters)
            elif action == "send_notification":
                return await self._send_notification(parameters)
            elif action == "schedule_reminder":
                return await self._schedule_reminder(parameters)
            elif action == "get_user_info":
                return await self._get_user_info(parameters)
            elif action == "list_channels":
                return await self._list_channels(parameters)
            elif action == "send_onboarding_checklist":
                return await self._send_onboarding_checklist(parameters)
            elif action == "notify_manager":
                return await self._notify_manager(parameters)
            else:
                return ToolExecutionResult(
                    success=False,
                    error=f"Unknown action: {action}"
                )
                
        except Exception as e:
            logger.error(f"Error executing Slack action {action}: {e}")
            return ToolExecutionResult(
                success=False,
                error=f"Slack action failed: {str(e)}"
            )
    
    async def _send_message(self, parameters: Dict[str, Any]) -> ToolExecutionResult:
        """Send a message to a Slack channel or user."""
        try:
            channel = parameters.get("channel")
            text = parameters.get("text", "")
            blocks = parameters.get("blocks")  # For rich formatting
            thread_ts = parameters.get("thread_ts")  # For threaded replies
            
            if not channel:
                return ToolExecutionResult(
                    success=False,
                    error="Channel is required for sending messages"
                )
            
            # Prepare message
            message_args = {
                "channel": channel,
                "text": text
            }
            
            if blocks:
                message_args["blocks"] = blocks
            
            if thread_ts:
                message_args["thread_ts"] = thread_ts
            
            # Send message
            response = self.client.chat_postMessage(**message_args)
            
            return ToolExecutionResult(
                success=True,
                data={
                    "message_ts": response["ts"],
                    "channel": response["channel"],
                    "text": text,
                    "permalink": self._get_message_permalink(response["channel"], response["ts"])
                }
            )
            
        except SlackApiError as e:
            return ToolExecutionResult(
                success=False,
                error=f"Slack API error: {e.response['error']}"
            )
    
    async def _send_welcome_message(self, parameters: Dict[str, Any]) -> ToolExecutionResult:
        """Send a personalized welcome message to new employee."""
        try:
            user_id = parameters.get("user_id")
            user_name = parameters.get("user_name", "New Team Member")
            job_title = parameters.get("job_title", "Team Member")
            start_date = parameters.get("start_date", datetime.now().strftime("%Y-%m-%d"))
            manager = parameters.get("manager")
            buddy = parameters.get("buddy")
            
            if not user_id:
                return ToolExecutionResult(
                    success=False,
                    error="user_id is required for welcome messages"
                )
            
            # Create welcome message blocks
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"🎉 Welcome to the team, {user_name}!"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"We're excited to have you join us as our new *{job_title}*! Your official start date is {start_date}."
                    }
                },
                {
                    "type": "divider"
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "Here's what you can expect:"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "• 🏢 Office tour and workspace setup\n• 👥 Meet your team and key stakeholders\n• 📚 Complete essential training modules\n• 💻 Get access to all necessary tools and systems\n• 🎯 Review your role expectations and initial goals"
                    }
                }
            ]
            
            if manager:
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"Your manager is <@{manager}> - they'll help guide you through your first few weeks."
                    }
                })
            
            if buddy:
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"Your onboarding buddy is <@{buddy}> - feel free to reach out with any questions!"
                    }
                })
            
            blocks.extend([
                {
                    "type": "divider"
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "🤖 I'm Aura, your AI onboarding assistant. I'll help you navigate your first few weeks and ensure you have everything you need to succeed!"
                    }
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "View My Onboarding Plan"
                            },
                            "value": "view_onboarding_plan",
                            "action_id": "view_plan"
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Ask Aura a Question"
                            },
                            "value": "ask_question",
                            "action_id": "ask_question"
                        }
                    ]
                }
            ])
            
            # Send welcome message
            result = await self._send_message({
                "channel": user_id,
                "text": f"Welcome to the team, {user_name}!",
                "blocks": blocks
            })
            
            if result.success:
                result.data.update({
                    "message_type": "welcome",
                    "user_name": user_name,
                    "job_title": job_title
                })
            
            return result
            
        except Exception as e:
            return ToolExecutionResult(
                success=False,
                error=f"Error sending welcome message: {str(e)}"
            )
    
    async def _create_channel(self, parameters: Dict[str, Any]) -> ToolExecutionResult:
        """Create a new Slack channel."""
        try:
            name = parameters.get("name")
            is_private = parameters.get("is_private", False)
            purpose = parameters.get("purpose", "")
            topic = parameters.get("topic", "")
            
            if not name:
                return ToolExecutionResult(
                    success=False,
                    error="Channel name is required"
                )
            
            # Create channel
            response = self.client.conversations_create(
                name=name,
                is_private=is_private
            )
            
            channel_id = response["channel"]["id"]
            
            # Set purpose and topic if provided
            if purpose:
                self.client.conversations_setPurpose(
                    channel=channel_id,
                    purpose=purpose
                )
            
            if topic:
                self.client.conversations_setTopic(
                    channel=channel_id,
                    topic=topic
                )
            
            return ToolExecutionResult(
                success=True,
                data={
                    "channel_id": channel_id,
                    "channel_name": name,
                    "is_private": is_private,
                    "purpose": purpose,
                    "topic": topic
                }
            )
            
        except SlackApiError as e:
            return ToolExecutionResult(
                success=False,
                error=f"Error creating channel: {e.response['error']}"
            )
    
    async def _add_to_channel(self, parameters: Dict[str, Any]) -> ToolExecutionResult:
        """Add users to a Slack channel."""
        try:
            channel = parameters.get("channel")
            users = parameters.get("users", [])  # List of user IDs
            
            if not channel or not users:
                return ToolExecutionResult(
                    success=False,
                    error="Channel and users list are required"
                )
            
            # Add users to channel
            response = self.client.conversations_invite(
                channel=channel,
                users=",".join(users)
            )
            
            return ToolExecutionResult(
                success=True,
                data={
                    "channel": channel,
                    "added_users": users,
                    "message": f"Added {len(users)} users to channel"
                }
            )
            
        except SlackApiError as e:
            return ToolExecutionResult(
                success=False,
                error=f"Error adding users to channel: {e.response['error']}"
            )
    
    async def _send_notification(self, parameters: Dict[str, Any]) -> ToolExecutionResult:
        """Send a notification message with specific formatting."""
        try:
            channel = parameters.get("channel")
            notification_type = parameters.get("type", "info")  # info, warning, success, error
            title = parameters.get("title", "Notification")
            message = parameters.get("message", "")
            actions = parameters.get("actions", [])  # Optional action buttons
            
            # Define emoji and colors for different notification types
            type_config = {
                "info": {"emoji": "ℹ️", "color": "#2196F3"},
                "warning": {"emoji": "⚠️", "color": "#FF9800"},
                "success": {"emoji": "✅", "color": "#4CAF50"},
                "error": {"emoji": "❌", "color": "#F44336"}
            }
            
            config = type_config.get(notification_type, type_config["info"])
            
            # Create notification blocks
            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"{config['emoji']} *{title}*\n{message}"
                    }
                }
            ]
            
            # Add action buttons if provided
            if actions:
                action_elements = []
                for action in actions:
                    action_elements.append({
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": action.get("text", "Action")
                        },
                        "value": action.get("value", ""),
                        "action_id": action.get("action_id", "notification_action")
                    })
                
                blocks.append({
                    "type": "actions",
                    "elements": action_elements
                })
            
            # Send notification
            result = await self._send_message({
                "channel": channel,
                "text": f"{title}: {message}",
                "blocks": blocks
            })
            
            if result.success:
                result.data.update({
                    "notification_type": notification_type,
                    "title": title
                })
            
            return result
            
        except Exception as e:
            return ToolExecutionResult(
                success=False,
                error=f"Error sending notification: {str(e)}"
            )
    
    async def _send_onboarding_checklist(self, parameters: Dict[str, Any]) -> ToolExecutionResult:
        """Send an interactive onboarding checklist."""
        try:
            channel = parameters.get("channel")
            user_name = parameters.get("user_name", "New Employee")
            checklist_items = parameters.get("checklist_items", [])
            
            if not channel:
                return ToolExecutionResult(
                    success=False,
                    error="Channel is required for checklist"
                )
            
            # Default checklist if none provided
            if not checklist_items:
                checklist_items = [
                    {"text": "Complete HR paperwork", "completed": False},
                    {"text": "Set up workspace and equipment", "completed": False},
                    {"text": "Meet with direct manager", "completed": False},
                    {"text": "Complete security training", "completed": False},
                    {"text": "Join team channels", "completed": False},
                    {"text": "Review company handbook", "completed": False}
                ]
            
            # Create checklist blocks
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"📋 {user_name}'s Onboarding Checklist"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "Here's your personalized onboarding checklist. Check off items as you complete them!"
                    }
                },
                {
                    "type": "divider"
                }
            ]
            
            # Add checklist items
            for i, item in enumerate(checklist_items):
                checkbox = "☑️" if item.get("completed", False) else "☐"
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"{checkbox} {item['text']}"
                    },
                    "accessory": {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "✓ Complete" if not item.get("completed", False) else "Completed"
                        },
                        "value": f"checklist_item_{i}",
                        "action_id": f"complete_item_{i}"
                    }
                })
            
            blocks.extend([
                {
                    "type": "divider"
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": "💡 Need help with any of these items? Just ask me!"
                        }
                    ]
                }
            ])
            
            # Send checklist
            result = await self._send_message({
                "channel": channel,
                "text": f"Onboarding checklist for {user_name}",
                "blocks": blocks
            })
            
            if result.success:
                result.data.update({
                    "message_type": "checklist",
                    "user_name": user_name,
                    "total_items": len(checklist_items),
                    "completed_items": len([item for item in checklist_items if item.get("completed", False)])
                })
            
            return result
            
        except Exception as e:
            return ToolExecutionResult(
                success=False,
                error=f"Error sending checklist: {str(e)}"
            )
    
    async def _notify_manager(self, parameters: Dict[str, Any]) -> ToolExecutionResult:
        """Send notification to manager about employee progress."""
        try:
            manager_id = parameters.get("manager_id")
            employee_name = parameters.get("employee_name")
            notification_type = parameters.get("type", "progress_update")
            details = parameters.get("details", {})
            
            if not manager_id or not employee_name:
                return ToolExecutionResult(
                    success=False,
                    error="Manager ID and employee name are required"
                )
            
            # Create manager notification based on type
            if notification_type == "progress_update":
                title = f"📊 Onboarding Progress Update: {employee_name}"
                message = f"Here's an update on {employee_name}'s onboarding progress:\n\n"
                
                completed = details.get("completed_tasks", 0)
                total = details.get("total_tasks", 0)
                current_step = details.get("current_step", "Not specified")
                
                message += f"• Progress: {completed}/{total} tasks completed\n"
                message += f"• Current step: {current_step}\n"
                
                if details.get("blocked_items"):
                    message += f"• ⚠️ Blocked items: {len(details['blocked_items'])}"
                
            elif notification_type == "needs_attention":
                title = f"⚠️ Attention Needed: {employee_name}"
                message = f"{employee_name} needs assistance with their onboarding:\n\n"
                message += details.get("issue_description", "No details provided")
                
            else:
                title = f"📝 Onboarding Update: {employee_name}"
                message = details.get("message", "Onboarding update available")
            
            # Send notification to manager
            result = await self._send_notification({
                "channel": manager_id,
                "type": "info",
                "title": title,
                "message": message,
                "actions": [
                    {
                        "text": "View Full Report",
                        "value": f"view_report_{employee_name}",
                        "action_id": "view_employee_report"
                    }
                ]
            })
            
            if result.success:
                result.data.update({
                    "notification_type": notification_type,
                    "employee_name": employee_name,
                    "manager_id": manager_id
                })
            
            return result
            
        except Exception as e:
            return ToolExecutionResult(
                success=False,
                error=f"Error notifying manager: {str(e)}"
            )
    
    async def _get_user_info(self, parameters: Dict[str, Any]) -> ToolExecutionResult:
        """Get information about a Slack user."""
        try:
            user_id = parameters.get("user_id")
            
            if not user_id:
                return ToolExecutionResult(
                    success=False,
                    error="user_id is required"
                )
            
            response = self.client.users_info(user=user_id)
            user = response["user"]
            
            return ToolExecutionResult(
                success=True,
                data={
                    "user_id": user["id"],
                    "name": user["name"],
                    "real_name": user.get("real_name", ""),
                    "email": user.get("profile", {}).get("email", ""),
                    "title": user.get("profile", {}).get("title", ""),
                    "is_admin": user.get("is_admin", False),
                    "is_bot": user.get("is_bot", False),
                    "timezone": user.get("tz", "")
                }
            )
            
        except SlackApiError as e:
            return ToolExecutionResult(
                success=False,
                error=f"Error getting user info: {e.response['error']}"
            )
    
    async def _list_channels(self, parameters: Dict[str, Any]) -> ToolExecutionResult:
        """List Slack channels."""
        try:
            types = parameters.get("types", "public_channel,private_channel")
            limit = parameters.get("limit", 100)
            
            response = self.client.conversations_list(
                types=types,
                limit=limit
            )
            
            channels = []
            for channel in response["channels"]:
                channels.append({
                    "id": channel["id"],
                    "name": channel["name"],
                    "is_private": channel.get("is_private", False),
                    "is_archived": channel.get("is_archived", False),
                    "topic": channel.get("topic", {}).get("value", ""),
                    "purpose": channel.get("purpose", {}).get("value", ""),
                    "num_members": channel.get("num_members", 0)
                })
            
            return ToolExecutionResult(
                success=True,
                data={
                    "channels": channels,
                    "total_count": len(channels)
                }
            )
            
        except SlackApiError as e:
            return ToolExecutionResult(
                success=False,
                error=f"Error listing channels: {e.response['error']}"
            )
    
    async def _schedule_reminder(self, parameters: Dict[str, Any]) -> ToolExecutionResult:
        """Schedule a reminder message."""
        try:
            channel = parameters.get("channel")
            text = parameters.get("text", "Reminder")
            when = parameters.get("when")  # Unix timestamp or relative time
            
            if not channel or not when:
                return ToolExecutionResult(
                    success=False,
                    error="Channel and when are required for reminders"
                )
            
            response = self.client.chat_scheduleMessage(
                channel=channel,
                post_at=when,
                text=text
            )
            
            return ToolExecutionResult(
                success=True,
                data={
                    "scheduled_message_id": response["scheduled_message_id"],
                    "channel": channel,
                    "post_at": when,
                    "text": text
                }
            )
            
        except SlackApiError as e:
            return ToolExecutionResult(
                success=False,
                error=f"Error scheduling reminder: {e.response['error']}"
            )
    
    def _get_message_permalink(self, channel: str, message_ts: str) -> str:
        """Generate permalink for a message."""
        try:
            response = self.client.chat_getPermalink(
                channel=channel,
                message_ts=message_ts
            )
            return response["permalink"]
        except SlackApiError:
            return f"slack://channel?team={channel}&id={message_ts}"
    
    def is_available(self) -> bool:
        """Check if the Slack tool is available."""
        return self.client is not None and self.bot_user_id is not None
    
    def get_available_actions(self) -> List[str]:
        """Get list of available actions."""
        return [
            "send_message",
            "send_welcome_message",
            "create_channel",
            "add_to_channel",
            "send_notification",
            "schedule_reminder",
            "get_user_info",
            "list_channels",
            "send_onboarding_checklist",
            "notify_manager"
        ]