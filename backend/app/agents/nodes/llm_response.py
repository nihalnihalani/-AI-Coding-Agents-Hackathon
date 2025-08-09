from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

from ...services.llm_service import LLMRouter, LLMProvider
from ...tools.registry import tool_registry
from ...core.logging import get_logger

logger = get_logger(__name__)

class LLMResponseNode:
    """Node for generating contextual responses using appropriate LLMs."""
    
    def __init__(self):
        self.llm_router = LLMRouter()
        
        # Response templates for different contexts
        self.response_templates = {
            "greeting": {
                "template": "Hello! I'm Aura, your AI onboarding assistant. {context_info} How can I help you today?",
                "follow_up_suggestions": [
                    "Upload your resume to get started",
                    "Ask me about your onboarding plan",
                    "Get help with specific onboarding tasks"
                ]
            },
            "document_analysis_complete": {
                "template": "I've successfully analyzed your {document_type}. {analysis_summary} {next_steps}",
                "follow_up_suggestions": [
                    "Review your personalized onboarding plan",
                    "Schedule your first team meeting",
                    "Ask questions about your role"
                ]
            },
            "task_progress": {
                "template": "Great progress on your onboarding! {progress_info} {encouragement} {next_actions}",
                "follow_up_suggestions": [
                    "View your remaining tasks",
                    "Get help with current challenges",
                    "Schedule additional support"
                ]
            },
            "help_request": {
                "template": "I'm here to help! {specific_guidance} {available_resources} {escalation_options}",
                "follow_up_suggestions": [
                    "Contact your onboarding buddy",
                    "Schedule time with your manager",
                    "Access additional resources"
                ]
            },
            "error_handling": {
                "template": "I encountered an issue: {error_description} {recovery_actions} Let me help you resolve this.",
                "follow_up_suggestions": [
                    "Try the action again",
                    "Contact technical support",
                    "Use alternative approach"
                ]
            }
        }
    
    async def generate_response(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Generate contextual response based on current state and intent."""
        try:
            intent = state.get("current_user_intent", "general_conversation")
            conversation_history = state.get("conversation_history", [])
            contextual_memory = state.get("contextual_memory", {})
            
            # Determine response strategy
            response_strategy = self._determine_response_strategy(intent, state)
            
            # Generate base response using appropriate LLM
            base_response = await self._generate_base_response(
                intent, conversation_history, contextual_memory, response_strategy
            )
            
            # Enhance response with context and tools
            enhanced_response = await self._enhance_response_with_context(
                base_response, state, response_strategy
            )
            
            # Add follow-up suggestions and actions
            final_response = self._add_follow_up_suggestions(
                enhanced_response, intent, state
            )
            
            # Update conversation history
            updated_history = conversation_history + [{
                "role": "assistant",
                "content": final_response["response"],
                "timestamp": datetime.now().isoformat(),
                "intent": intent,
                "llm_used": final_response.get("llm_used"),
                "response_type": response_strategy["type"],
                "suggestions": final_response.get("suggestions", [])
            }]
            
            return {
                "conversation_history": updated_history,
                "last_response": final_response,
                "response_metadata": {
                    "strategy_used": response_strategy,
                    "context_factors": self._analyze_context_factors(state),
                    "confidence": final_response.get("confidence", 0.8)
                },
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating LLM response: {e}")
            return await self._handle_response_error(state, str(e))
    
    def _determine_response_strategy(self, intent: str, state: Dict[str, Any]) -> Dict[str, Any]:
        """Determine the best response strategy based on intent and context."""
        
        # Analyze current context
        current_step = state.get("current_step")
        completed_tasks = state.get("completed_tasks", [])
        onboarding_steps = state.get("onboarding_plan_steps", [])
        errors = state.get("errors", [])
        
        # Base strategy mapping
        strategy_mapping = {
            "greeting": {
                "type": "welcoming",
                "llm_preference": LLMProvider.CLAUDE,
                "tone": "friendly_professional",
                "include_context": True
            },
            "document_upload": {
                "type": "instructional",
                "llm_preference": LLMProvider.GEMINI,
                "tone": "helpful_technical",
                "include_context": False
            },
            "onboarding_planning": {
                "type": "strategic",
                "llm_preference": LLMProvider.GEMINI,
                "tone": "organized_detailed",
                "include_context": True
            },
            "task_management": {
                "type": "progress_focused",
                "llm_preference": LLMProvider.CLAUDE,
                "tone": "encouraging_practical",
                "include_context": True
            },
            "information_request": {
                "type": "informative",
                "llm_preference": LLMProvider.CLAUDE,
                "tone": "clear_comprehensive",
                "include_context": True
            },
            "approval_request": {
                "type": "procedural",
                "llm_preference": LLMProvider.CLAUDE,
                "tone": "formal_clear",
                "include_context": True
            },
            "general_conversation": {
                "type": "conversational",
                "llm_preference": LLMProvider.CLAUDE,
                "tone": "natural_helpful",
                "include_context": False
            }
        }
        
        base_strategy = strategy_mapping.get(intent, strategy_mapping["general_conversation"])
        
        # Adjust strategy based on context
        if errors:
            base_strategy["type"] = "error_recovery"
            base_strategy["tone"] = "apologetic_solution_focused"
        
        if current_step and len(completed_tasks) > len(onboarding_steps) * 0.7:
            base_strategy["tone"] = "congratulatory_forward_looking"
        
        if not onboarding_steps and intent != "greeting":
            base_strategy["include_setup_prompt"] = True
        
        return base_strategy
    
    async def _generate_base_response(self, intent: str, conversation_history: List[Dict[str, Any]],
                                    contextual_memory: Dict[str, Any], strategy: Dict[str, Any]) -> Dict[str, Any]:
        """Generate base response using selected LLM."""
        try:
            # Build context for LLM
            context_prompt = self._build_context_prompt(
                intent, conversation_history, contextual_memory, strategy
            )
            
            # Select LLM based on strategy
            preferred_llm = strategy.get("llm_preference", LLMProvider.CLAUDE)
            
            # Generate response
            llm_response = await self.llm_router.generate_response(
                task_type=self._map_intent_to_task_type(intent),
                prompt=context_prompt,
                requirements={"llm_preference": preferred_llm, "max_tokens": 500}
            )
            
            return {
                "response": llm_response.get("response", "I'm here to help with your onboarding!"),
                "llm_used": llm_response.get("llm_used", "unknown"),
                "success": llm_response.get("success", True),
                "confidence": 0.8 if llm_response.get("success") else 0.4
            }
            
        except Exception as e:
            logger.error(f"Error generating base response: {e}")
            return {
                "response": "I'm experiencing a technical issue, but I'm still here to help you with your onboarding!",
                "llm_used": "fallback",
                "success": False,
                "confidence": 0.3,
                "error": str(e)
            }
    
    def _build_context_prompt(self, intent: str, conversation_history: List[Dict[str, Any]],
                            contextual_memory: Dict[str, Any], strategy: Dict[str, Any]) -> str:
        """Build comprehensive context prompt for LLM."""
        
        # Base system prompt
        system_prompt = f"""You are Aura, an AI onboarding assistant. You help new employees navigate their onboarding process with a {strategy.get('tone', 'helpful')} tone.

Current Intent: {intent}
Response Type: {strategy.get('type', 'general')}

Guidelines:
- Be concise but comprehensive
- Provide actionable advice
- Show empathy and encouragement
- Reference specific onboarding context when available
- Suggest next steps when appropriate
"""
        
        # Add conversation context
        if conversation_history and len(conversation_history) > 0:
            recent_messages = conversation_history[-3:]  # Last 3 messages for context
            conversation_context = "Recent Conversation:\n"
            for msg in recent_messages:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")[:200]  # Truncate long messages
                conversation_context += f"{role.title()}: {content}\n"
            system_prompt += f"\n{conversation_context}"
        
        # Add contextual memory
        if strategy.get("include_context") and contextual_memory:
            context_info = []
            
            if contextual_memory.get("job_role"):
                context_info.append(f"Job Role: {contextual_memory['job_role']}")
            
            if contextual_memory.get("resume_processed"):
                context_info.append("Resume has been processed")
            
            if contextual_memory.get("skills_identified"):
                skills = contextual_memory["skills_identified"][:3]  # Top 3 skills
                context_info.append(f"Key Skills: {', '.join(skills)}")
            
            if contextual_memory.get("experience_level"):
                context_info.append(f"Experience Level: {contextual_memory['experience_level']} years")
            
            if context_info:
                system_prompt += f"\nEmployee Context: {'; '.join(context_info)}"
        
        # Get the user's latest message
        user_message = "Hello"  # Default
        if conversation_history:
            latest_user_msg = next(
                (msg for msg in reversed(conversation_history) if msg.get("role") == "user"),
                None
            )
            if latest_user_msg:
                user_message = latest_user_msg.get("content", "Hello")
        
        return f"{system_prompt}\n\nUser Message: {user_message}\n\nResponse:"
    
    async def _enhance_response_with_context(self, base_response: Dict[str, Any], 
                                           state: Dict[str, Any], strategy: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance response with contextual information and tool integration."""
        try:
            response_text = base_response.get("response", "")
            
            # Add progress information for task-related intents
            if strategy.get("type") == "progress_focused":
                progress_info = self._generate_progress_summary(state)
                if progress_info:
                    response_text += f"\n\n{progress_info}"
            
            # Add setup prompts for new users
            if strategy.get("include_setup_prompt"):
                setup_prompt = "\n\nTo get started, I recommend uploading your resume so I can create a personalized onboarding plan for you."
                response_text += setup_prompt
            
            # Add tool-specific information
            suggested_tools = self._suggest_relevant_tools(state.get("current_user_intent", ""))
            if suggested_tools:
                tools_info = self._format_tool_suggestions(suggested_tools)
                response_text += f"\n\n{tools_info}"
            
            base_response["response"] = response_text
            return base_response
            
        except Exception as e:
            logger.error(f"Error enhancing response: {e}")
            return base_response
    
    def _add_follow_up_suggestions(self, response: Dict[str, Any], intent: str, 
                                 state: Dict[str, Any]) -> Dict[str, Any]:
        """Add contextual follow-up suggestions."""
        try:
            # Get base suggestions from templates
            template_key = self._map_intent_to_template(intent)
            base_suggestions = self.response_templates.get(template_key, {}).get("follow_up_suggestions", [])
            
            # Customize suggestions based on current state
            contextual_suggestions = self._generate_contextual_suggestions(state, intent)
            
            # Combine and prioritize suggestions
            all_suggestions = base_suggestions + contextual_suggestions
            response["suggestions"] = all_suggestions[:3]  # Limit to top 3
            
            return response
            
        except Exception as e:
            logger.error(f"Error adding follow-up suggestions: {e}")
            response["suggestions"] = ["Ask me any questions about your onboarding"]
            return response
    
    def _generate_progress_summary(self, state: Dict[str, Any]) -> Optional[str]:
        """Generate progress summary for task-focused responses."""
        try:
            completed_tasks = state.get("completed_tasks", [])
            onboarding_steps = state.get("onboarding_plan_steps", [])
            current_step = state.get("current_step")
            
            if not onboarding_steps:
                return None
            
            total_steps = len(onboarding_steps)
            completed_count = len(completed_tasks)
            completion_percentage = int((completed_count / total_steps) * 100) if total_steps > 0 else 0
            
            progress_text = f"📊 **Progress Update**: You've completed {completed_count} out of {total_steps} onboarding tasks ({completion_percentage}%)."
            
            if current_step:
                current_task = next((step for step in onboarding_steps if step.get("step_id") == current_step), None)
                if current_task:
                    progress_text += f" Currently working on: {current_task.get('title', 'Current task')}."
            
            # Add encouragement based on progress
            if completion_percentage >= 75:
                progress_text += " You're almost there! 🎉"
            elif completion_percentage >= 50:
                progress_text += " Great progress! Keep it up! 💪"
            elif completion_percentage >= 25:
                progress_text += " You're off to a good start! 🚀"
            else:
                progress_text += " Let's get started on your onboarding journey! ✨"
            
            return progress_text
            
        except Exception as e:
            logger.error(f"Error generating progress summary: {e}")
            return None
    
    def _suggest_relevant_tools(self, intent: str) -> List[Dict[str, Any]]:
        """Suggest relevant tools based on current intent."""
        try:
            # Get tool suggestions from registry
            suggested_tools = tool_registry.suggest_tools_for_intent(intent)
            
            # Filter to available tools only
            available_tools = [tool for tool in suggested_tools if tool.get("available", False)]
            
            return available_tools[:2]  # Limit to top 2 suggestions
            
        except Exception as e:
            logger.error(f"Error suggesting tools: {e}")
            return []
    
    def _format_tool_suggestions(self, suggested_tools: List[Dict[str, Any]]) -> str:
        """Format tool suggestions for response."""
        if not suggested_tools:
            return ""
        
        suggestions_text = "🔧 **Available Actions**:\n"
        for tool in suggested_tools:
            tool_name = tool.get("tool_name", "Tool")
            description = tool.get("description", "Available tool")
            suggestions_text += f"• {description}\n"
        
        return suggestions_text
    
    def _generate_contextual_suggestions(self, state: Dict[str, Any], intent: str) -> List[str]:
        """Generate contextual suggestions based on current state."""
        suggestions = []
        
        current_step = state.get("current_step")
        onboarding_steps = state.get("onboarding_plan_steps", [])
        pending_approvals = state.get("pending_approvals", [])
        
        # Suggestions based on current step
        if current_step and onboarding_steps:
            current_task = next((step for step in onboarding_steps if step.get("step_id") == current_step), None)
            if current_task:
                task_title = current_task.get("title", "current task")
                suggestions.append(f"Get help with: {task_title}")
        
        # Suggestions based on pending approvals
        if pending_approvals:
            suggestions.append("Review pending approval requests")
        
        # Intent-specific suggestions
        if intent == "document_upload":
            suggestions.append("Schedule your first team meeting")
        elif intent == "calendar_scheduling":
            suggestions.append("View your onboarding timeline")
        elif intent == "task_management":
            suggestions.append("Update task progress")
        
        return suggestions
    
    def _analyze_context_factors(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze context factors that influenced the response."""
        return {
            "has_onboarding_plan": len(state.get("onboarding_plan_steps", [])) > 0,
            "current_progress": len(state.get("completed_tasks", [])),
            "has_pending_approvals": len(state.get("pending_approvals", [])) > 0,
            "conversation_length": len(state.get("conversation_history", [])),
            "has_errors": len(state.get("errors", [])) > 0,
            "contextual_memory_items": len(state.get("contextual_memory", {}))
        }
    
    def _map_intent_to_task_type(self, intent: str) -> str:
        """Map intent to LLM task type."""
        mapping = {
            "document_upload": "document_analysis",
            "onboarding_planning": "planning",
            "calendar_scheduling": "conversation",
            "task_management": "conversation",
            "approval_request": "conversation",
            "information_request": "conversation",
            "general_conversation": "conversation"
        }
        return mapping.get(intent, "conversation")
    
    def _map_intent_to_template(self, intent: str) -> str:
        """Map intent to response template."""
        mapping = {
            "greeting": "greeting",
            "document_upload": "document_analysis_complete",
            "task_management": "task_progress",
            "information_request": "help_request",
            "general_conversation": "help_request"
        }
        return mapping.get(intent, "help_request")
    
    async def _handle_response_error(self, state: Dict[str, Any], error_message: str) -> Dict[str, Any]:
        """Handle errors in response generation."""
        try:
            # Create error response
            error_response = {
                "response": "I apologize, but I'm having a technical issue right now. However, I'm still here to help you with your onboarding! Please try asking your question again, or let me know if you need assistance with something specific.",
                "llm_used": "error_handler",
                "success": False,
                "confidence": 0.3,
                "error": error_message,
                "suggestions": [
                    "Try your request again",
                    "Ask a different question",
                    "Contact your onboarding buddy for assistance"
                ]
            }
            
            # Update conversation history with error
            conversation_history = state.get("conversation_history", [])
            updated_history = conversation_history + [{
                "role": "assistant",
                "content": error_response["response"],
                "timestamp": datetime.now().isoformat(),
                "error": True,
                "error_message": error_message
            }]
            
            return {
                "conversation_history": updated_history,
                "last_response": error_response,
                "errors": state.get("errors", []) + [f"Response generation error: {error_message}"],
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in error handler: {e}")
            return {
                "conversation_history": state.get("conversation_history", []),
                "errors": state.get("errors", []) + [f"Critical error: {str(e)}"],
                "last_updated": datetime.now().isoformat()
            }