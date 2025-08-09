from typing import Dict, Any, List, Optional
import logging
from datetime import datetime
import re

from ...services.llm_service import LLMRouter, LLMProvider
from ...core.logging import get_logger

logger = get_logger(__name__)

class IntentRouterNode:
    """Node for natural language intent classification and routing."""
    
    def __init__(self):
        self.llm_router = LLMRouter()
        
        # Intent categories and their characteristics
        self.intent_patterns = {
            "greeting": {
                "keywords": ["hello", "hi", "hey", "good morning", "good afternoon", "start", "begin"],
                "confidence_threshold": 0.8,
                "suggested_llm": LLMProvider.CLAUDE,
                "requires_context": False
            },
            "document_upload": {
                "keywords": ["upload", "resume", "cv", "document", "file", "attach", "submit"],
                "confidence_threshold": 0.9,
                "suggested_llm": LLMProvider.GEMINI,
                "requires_context": False
            },
            "onboarding_planning": {
                "keywords": ["plan", "schedule", "onboarding", "timeline", "roadmap", "steps", "process"],
                "confidence_threshold": 0.8,
                "suggested_llm": LLMProvider.GEMINI,
                "requires_context": True
            },
            "task_management": {
                "keywords": ["task", "complete", "done", "finished", "progress", "update", "status"],
                "confidence_threshold": 0.85,
                "suggested_llm": LLMProvider.CLAUDE,
                "requires_context": True
            },
            "information_request": {
                "keywords": ["what", "how", "when", "where", "who", "explain", "tell me", "help", "info"],
                "confidence_threshold": 0.7,
                "suggested_llm": LLMProvider.CLAUDE,
                "requires_context": False
            },
            "calendar_scheduling": {
                "keywords": ["meeting", "schedule", "calendar", "appointment", "book", "available", "time"],
                "confidence_threshold": 0.85,
                "suggested_llm": LLMProvider.CLAUDE,
                "requires_context": True
            },
            "tool_interaction": {
                "keywords": ["slack", "github", "email", "access", "login", "setup", "configure"],
                "confidence_threshold": 0.8,
                "suggested_llm": LLMProvider.CLAUDE,
                "requires_context": True
            },
            "approval_request": {
                "keywords": ["approve", "permission", "allow", "authorize", "confirm", "proceed"],
                "confidence_threshold": 0.9,
                "suggested_llm": LLMProvider.CLAUDE,
                "requires_context": True
            },
            "feedback_complaint": {
                "keywords": ["problem", "issue", "error", "bug", "complaint", "feedback", "suggestion"],
                "confidence_threshold": 0.8,
                "suggested_llm": LLMProvider.CLAUDE,
                "requires_context": False
            },
            "general_conversation": {
                "keywords": ["chat", "talk", "discuss", "conversation", "question"],
                "confidence_threshold": 0.6,
                "suggested_llm": LLMProvider.CLAUDE,
                "requires_context": False
            }
        }
    
    async def classify_intent(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Classify user intent from conversation history and context."""
        try:
            # Get the latest user message
            conversation_history = state.get("conversation_history", [])
            if not conversation_history:
                return {
                    "current_user_intent": "greeting",
                    "intent_confidence": 1.0,
                    "suggested_llm": LLMProvider.CLAUDE,
                    "routing_context": {"reason": "No conversation history, defaulting to greeting"},
                    "last_updated": datetime.now().isoformat()
                }
            
            latest_message = conversation_history[-1]
            if latest_message.get("role") != "user":
                # Find the most recent user message
                latest_message = next((msg for msg in reversed(conversation_history) if msg.get("role") == "user"), None)
            
            if not latest_message:
                return self._default_intent_response("No user message found")
            
            user_input = latest_message.get("content", "").lower().strip()
            
            # Multi-level intent classification
            intent_results = await self._classify_multi_level(user_input, state)
            
            # Validate and route based on context
            validated_intent = self._validate_intent_with_context(intent_results, state)
            
            return {
                "current_user_intent": validated_intent["intent"],
                "intent_confidence": validated_intent["confidence"],
                "suggested_llm": validated_intent["suggested_llm"],
                "routing_context": validated_intent["context"],
                "intent_metadata": validated_intent["metadata"],
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in intent classification: {e}")
            return self._default_intent_response(f"Classification error: {str(e)}")
    
    async def _classify_multi_level(self, user_input: str, state: Dict[str, Any]) -> Dict[str, Any]:
        """Multi-level intent classification using patterns and LLM."""
        
        # Level 1: Pattern-based classification
        pattern_results = self._pattern_based_classification(user_input)
        
        # Level 2: Context-aware classification
        context_results = self._context_aware_classification(user_input, state)
        
        # Level 3: LLM-based classification for complex cases
        if pattern_results["confidence"] < 0.7 or context_results["requires_llm"]:
            llm_results = await self._llm_based_classification(user_input, state)
            return self._merge_classification_results([pattern_results, context_results, llm_results])
        
        return self._merge_classification_results([pattern_results, context_results])
    
    def _pattern_based_classification(self, user_input: str) -> Dict[str, Any]:
        """Classify intent using keyword patterns and regex."""
        intent_scores = {}
        
        for intent, config in self.intent_patterns.items():
            score = 0.0
            matched_keywords = []
            
            # Keyword matching
            for keyword in config["keywords"]:
                if keyword in user_input:
                    score += 1.0
                    matched_keywords.append(keyword)
            
            # Normalize score
            if matched_keywords:
                score = min(score / len(config["keywords"]), 1.0)
            
            intent_scores[intent] = {
                "score": score,
                "matched_keywords": matched_keywords
            }
        
        # Find best match
        best_intent = max(intent_scores.keys(), key=lambda x: intent_scores[x]["score"])
        best_score = intent_scores[best_intent]["score"]
        
        return {
            "intent": best_intent,
            "confidence": best_score,
            "method": "pattern_based",
            "matched_keywords": intent_scores[best_intent]["matched_keywords"],
            "all_scores": intent_scores
        }
    
    def _context_aware_classification(self, user_input: str, state: Dict[str, Any]) -> Dict[str, Any]:
        """Classify intent based on conversation context and agent state."""
        context_factors = {
            "requires_llm": False,
            "context_boost": {},
            "state_indicators": {}
        }
        
        # Check current onboarding stage
        current_step = state.get("current_step")
        onboarding_steps = state.get("onboarding_plan_steps", [])
        
        if current_step and onboarding_steps:
            current_task = next((step for step in onboarding_steps if step.get("step_id") == current_step), None)
            if current_task:
                task_type = current_task.get("title", "").lower()
                
                # Boost relevant intents based on current task
                if "document" in task_type or "upload" in task_type:
                    context_factors["context_boost"]["document_upload"] = 0.3
                elif "meeting" in task_type or "schedule" in task_type:
                    context_factors["context_boost"]["calendar_scheduling"] = 0.3
                elif "setup" in task_type or "access" in task_type:
                    context_factors["context_boost"]["tool_interaction"] = 0.3
        
        # Check for pending approvals
        pending_approvals = state.get("pending_approvals", [])
        if pending_approvals:
            context_factors["context_boost"]["approval_request"] = 0.4
        
        # Check conversation flow
        conversation_history = state.get("conversation_history", [])
        if len(conversation_history) > 1:
            previous_intent = state.get("current_user_intent")
            if previous_intent == "document_upload":
                context_factors["context_boost"]["task_management"] = 0.2
        
        # Determine if LLM classification is needed
        if any(boost > 0.2 for boost in context_factors["context_boost"].values()):
            context_factors["requires_llm"] = True
        
        return context_factors
    
    async def _llm_based_classification(self, user_input: str, state: Dict[str, Any]) -> Dict[str, Any]:
        """Use LLM for complex intent classification."""
        try:
            # Create classification prompt
            context_info = self._build_context_for_llm(state)
            
            classification_prompt = f"""
            Classify the user's intent based on their message and the current context.
            
            User Message: "{user_input}"
            
            Current Context:
            {context_info}
            
            Available Intent Categories:
            - greeting: Initial hellos and conversation starters
            - document_upload: Uploading documents like resumes, forms
            - onboarding_planning: Creating or modifying onboarding plans
            - task_management: Updating task status or progress
            - information_request: Asking for information or help
            - calendar_scheduling: Scheduling meetings or appointments
            - tool_interaction: Working with tools like Slack, GitHub
            - approval_request: Requesting approvals or permissions
            - feedback_complaint: Reporting issues or giving feedback
            - general_conversation: General chat or questions
            
            Respond with the most likely intent and a confidence score (0-1).
            Format: Intent: [intent_name], Confidence: [0.0-1.0], Reasoning: [brief explanation]
            """
            
            llm_response = await self.llm_router.generate_response(
                "conversation",
                classification_prompt,
                max_tokens=200
            )
            
            # Parse LLM response
            return self._parse_llm_classification(llm_response.get("response", ""))
            
        except Exception as e:
            logger.error(f"Error in LLM-based classification: {e}")
            return {
                "intent": "general_conversation",
                "confidence": 0.5,
                "method": "llm_fallback",
                "error": str(e)
            }
    
    def _build_context_for_llm(self, state: Dict[str, Any]) -> str:
        """Build context string for LLM classification."""
        context_parts = []
        
        # Current step information
        current_step = state.get("current_step")
        if current_step:
            context_parts.append(f"Current onboarding step: {current_step}")
        
        # Recent conversation
        conversation_history = state.get("conversation_history", [])
        if len(conversation_history) > 1:
            recent_messages = conversation_history[-3:]  # Last 3 messages
            context_parts.append("Recent conversation:")
            for msg in recent_messages:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")[:100]  # Truncate for context
                context_parts.append(f"  {role}: {content}")
        
        # Pending items
        pending_approvals = state.get("pending_approvals", [])
        if pending_approvals:
            context_parts.append(f"Pending approvals: {len(pending_approvals)}")
        
        completed_tasks = state.get("completed_tasks", [])
        if completed_tasks:
            context_parts.append(f"Completed tasks: {len(completed_tasks)}")
        
        return "\n".join(context_parts) if context_parts else "No specific context available"
    
    def _parse_llm_classification(self, llm_response: str) -> Dict[str, Any]:
        """Parse LLM classification response."""
        try:
            # Extract intent, confidence, and reasoning using regex
            intent_match = re.search(r"Intent:\s*([a-zA-Z_]+)", llm_response)
            confidence_match = re.search(r"Confidence:\s*([0-9.]+)", llm_response)
            reasoning_match = re.search(r"Reasoning:\s*(.+)", llm_response)
            
            intent = intent_match.group(1) if intent_match else "general_conversation"
            confidence = float(confidence_match.group(1)) if confidence_match else 0.7
            reasoning = reasoning_match.group(1) if reasoning_match else "LLM classification"
            
            return {
                "intent": intent,
                "confidence": confidence,
                "method": "llm_based",
                "reasoning": reasoning,
                "raw_response": llm_response
            }
            
        except Exception as e:
            logger.error(f"Error parsing LLM classification: {e}")
            return {
                "intent": "general_conversation",
                "confidence": 0.5,
                "method": "llm_parse_error",
                "error": str(e)
            }
    
    def _merge_classification_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Merge multiple classification results into final decision."""
        if not results:
            return self._default_intent_response("No classification results")
        
        # Weight the different methods
        method_weights = {
            "pattern_based": 0.4,
            "context_aware": 0.3,
            "llm_based": 0.7
        }
        
        intent_scores = {}
        
        for result in results:
            if "intent" in result and "confidence" in result:
                intent = result["intent"]
                confidence = result["confidence"]
                method = result.get("method", "unknown")
                weight = method_weights.get(method, 0.5)
                
                weighted_score = confidence * weight
                
                if intent in intent_scores:
                    intent_scores[intent] += weighted_score
                else:
                    intent_scores[intent] = weighted_score
        
        if not intent_scores:
            return self._default_intent_response("No valid scores calculated")
        
        # Select best intent
        best_intent = max(intent_scores.keys(), key=lambda x: intent_scores[x])
        best_score = intent_scores[best_intent]
        
        # Get configuration for best intent
        intent_config = self.intent_patterns.get(best_intent, {})
        
        return {
            "intent": best_intent,
            "confidence": min(best_score, 1.0),
            "suggested_llm": intent_config.get("suggested_llm", LLMProvider.CLAUDE),
            "method": "merged",
            "all_scores": intent_scores,
            "results_merged": len(results)
        }
    
    def _validate_intent_with_context(self, intent_results: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and potentially adjust intent based on full context."""
        intent = intent_results.get("intent", "general_conversation")
        confidence = intent_results.get("confidence", 0.5)
        
        # Context-based adjustments
        adjustments = []
        
        # Check if user is mid-process
        current_step = state.get("current_step")
        if current_step and intent == "greeting":
            # User might be continuing a process, not just greeting
            intent = "task_management"
            confidence *= 0.8
            adjustments.append("Adjusted greeting to task_management due to active step")
        
        # Check for approval context
        pending_approvals = state.get("pending_approvals", [])
        if pending_approvals and intent in ["general_conversation", "information_request"]:
            # Might be responding to approval request
            intent = "approval_request"
            confidence *= 0.9
            adjustments.append("Adjusted to approval_request due to pending approvals")
        
        # Get final configuration
        intent_config = self.intent_patterns.get(intent, {})
        
        return {
            "intent": intent,
            "confidence": confidence,
            "suggested_llm": intent_config.get("suggested_llm", LLMProvider.CLAUDE),
            "context": {
                "original_results": intent_results,
                "adjustments": adjustments,
                "requires_context": intent_config.get("requires_context", False)
            },
            "metadata": {
                "threshold_met": confidence >= intent_config.get("confidence_threshold", 0.7),
                "method_used": intent_results.get("method", "unknown"),
                "validation_adjustments": len(adjustments)
            }
        }
    
    def _default_intent_response(self, reason: str) -> Dict[str, Any]:
        """Return default intent response for error cases."""
        return {
            "current_user_intent": "general_conversation",
            "intent_confidence": 0.5,
            "suggested_llm": LLMProvider.CLAUDE,
            "routing_context": {"reason": reason, "fallback": True},
            "intent_metadata": {"error": True},
            "last_updated": datetime.now().isoformat()
        }