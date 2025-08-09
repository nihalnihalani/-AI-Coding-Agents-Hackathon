from langgraph.graph import StateGraph, END
from typing import Dict, Any
import logging
from datetime import datetime

from .base_agent import AgentState, BaseOnboardingAgent, LLMProvider
from ..core.logging import get_logger

logger = get_logger(__name__)

class AuraAgent(BaseOnboardingAgent):
    """Main Aura onboarding agent using LangGraph workflow."""
    
    def __init__(self):
        super().__init__()
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow for the Aura agent."""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("intent_recognition", self.intent_recognition_node)
        workflow.add_node("llm_router", self.llm_router_node)
        workflow.add_node("response_generation", self.response_generation_node)
        workflow.add_node("tool_execution", self.tool_execution_node)
        workflow.add_node("approval_check", self.approval_check_node)
        
        # Define entry point
        workflow.set_entry_point("intent_recognition")
        
        # Add edges
        workflow.add_edge("intent_recognition", "llm_router")
        workflow.add_edge("llm_router", "response_generation")
        workflow.add_conditional_edges(
            "response_generation",
            self._route_after_response,
            {
                "tool_execution": "tool_execution",
                "approval_check": "approval_check",
                "end": END
            }
        )
        workflow.add_edge("tool_execution", "approval_check")
        workflow.add_edge("approval_check", END)
        
        return workflow.compile()
    
    def intent_recognition_node(self, state: AgentState) -> Dict[str, Any]:
        """Recognize user intent from the current input."""
        logger.info("Processing intent recognition node")
        
        # Get the latest message from conversation history
        if state["conversation_history"]:
            latest_message = state["conversation_history"][-1]
            user_input = latest_message.get("content", "")
            
            # Basic intent classification (will be enhanced with LLM)
            intent = self._classify_intent(user_input)
            
            return {
                "current_user_intent": intent,
                "last_updated": datetime.now().isoformat()
            }
        
        return {"current_user_intent": "greeting"}
    
    def llm_router_node(self, state: AgentState) -> Dict[str, Any]:
        """Route to appropriate LLM based on task requirements."""
        logger.info("Processing LLM router node")
        
        intent = state.get("current_user_intent", "")
        
        # Route based on intent type
        if intent in ["document_analysis", "resume_processing", "multimodal"]:
            selected_llm = LLMProvider.GEMINI
        elif intent in ["conversation", "safety_check", "planning"]:
            selected_llm = LLMProvider.CLAUDE
        else:
            selected_llm = state.get("active_llm", LLMProvider.GEMINI)
        
        return {
            "active_llm": selected_llm,
            "llm_context": {"routing_reason": f"Selected {selected_llm} for intent: {intent}"}
        }
    
    def response_generation_node(self, state: AgentState) -> Dict[str, Any]:
        """Generate response using the selected LLM."""
        logger.info("Processing response generation node")
        
        intent = state.get("current_user_intent", "")
        active_llm = state.get("active_llm", LLMProvider.GEMINI)
        
        # Generate appropriate response based on intent and LLM
        response = self._generate_response(intent, active_llm, state)
        
        # Add response to conversation history
        conversation_history = state.get("conversation_history", [])
        conversation_history.append({
            "role": "assistant",
            "content": response,
            "llm_used": active_llm,
            "timestamp": datetime.now().isoformat()
        })
        
        return {
            "conversation_history": conversation_history,
            "last_updated": datetime.now().isoformat()
        }
    
    def tool_execution_node(self, state: AgentState) -> Dict[str, Any]:
        """Execute external tools if needed."""
        logger.info("Processing tool execution node")
        
        # Placeholder for tool execution logic
        tool_results = {"status": "no_tools_executed"}
        
        return {
            "tool_states": {**state.get("tool_states", {}), "last_execution": tool_results},
            "last_updated": datetime.now().isoformat()
        }
    
    def approval_check_node(self, state: AgentState) -> Dict[str, Any]:
        """Check if human approval is needed for actions."""
        logger.info("Processing approval check node")
        
        # For now, assume no approvals needed
        return {
            "pending_approvals": [],
            "last_updated": datetime.now().isoformat()
        }
    
    def _classify_intent(self, user_input: str) -> str:
        """Basic intent classification (will be enhanced with LLM)."""
        user_input_lower = user_input.lower()
        
        if any(keyword in user_input_lower for keyword in ["resume", "cv", "upload", "document"]):
            return "document_analysis"
        elif any(keyword in user_input_lower for keyword in ["hello", "hi", "hey", "start"]):
            return "greeting"
        elif any(keyword in user_input_lower for keyword in ["plan", "schedule", "calendar"]):
            return "planning"
        elif any(keyword in user_input_lower for keyword in ["help", "question", "how"]):
            return "conversation"
        else:
            return "general_inquiry"
    
    def _generate_response(self, intent: str, llm: LLMProvider, state: AgentState) -> str:
        """Generate response based on intent and selected LLM."""
        if intent == "greeting":
            return "Hello! I'm Aura, your AI onboarding assistant. I'm here to help you get started with your new role. How can I assist you today?"
        elif intent == "document_analysis":
            return "I'd be happy to help analyze your resume or other documents. Please upload your file and I'll process it to create a personalized onboarding plan."
        elif intent == "planning":
            return "Let me help you create an onboarding plan. What role are you starting, and do you have any specific goals or timelines?"
        else:
            return f"I understand you're asking about {intent}. Let me help you with that using {llm}."
    
    def _route_after_response(self, state: AgentState) -> str:
        """Determine next step after response generation."""
        intent = state.get("current_user_intent", "")
        
        if intent in ["document_analysis", "planning"]:
            return "tool_execution"
        elif state.get("pending_approvals"):
            return "approval_check"
        else:
            return "end"
    
    async def process_input(self, user_input: str, session_id: str) -> Dict[str, Any]:
        """Process user input through the workflow."""
        # Update state with new input
        conversation_history = self.state.get("conversation_history", [])
        conversation_history.append({
            "role": "user",
            "content": user_input,
            "timestamp": datetime.now().isoformat()
        })
        
        self.state["conversation_history"] = conversation_history
        self.state["session_id"] = session_id
        
        # Run the workflow
        try:
            result = await self.workflow.ainvoke(self.state)
            return result
        except Exception as e:
            logger.error(f"Error processing input: {e}")
            self.state["errors"].append(str(e))
            return self.state