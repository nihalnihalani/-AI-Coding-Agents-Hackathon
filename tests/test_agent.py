import pytest
from unittest.mock import Mock, patch
import asyncio

from backend.app.agents.aura_agent import AuraAgent
from backend.app.agents.base_agent import AgentState, LLMProvider

class TestAuraAgent:
    """Test cases for the Aura agent."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.agent = AuraAgent()
    
    def test_agent_initialization(self):
        """Test that the agent initializes correctly."""
        assert self.agent is not None
        assert isinstance(self.agent.state, dict)
        assert self.agent.state["active_llm"] == LLMProvider.GEMINI
        assert self.agent.state["conversation_history"] == []
        assert self.agent.state["completed_tasks"] == []
    
    def test_intent_classification(self):
        """Test basic intent classification."""
        # Test greeting intent
        greeting_intent = self.agent._classify_intent("Hello, I'm new here")
        assert greeting_intent == "greeting"
        
        # Test document analysis intent
        doc_intent = self.agent._classify_intent("I want to upload my resume")
        assert doc_intent == "document_analysis"
        
        # Test planning intent
        plan_intent = self.agent._classify_intent("Can you help me create a schedule?")
        assert plan_intent == "planning"
    
    def test_llm_routing(self):
        """Test LLM routing logic."""
        # Test Gemini routing for document analysis
        state = self.agent.state.copy()
        state["current_user_intent"] = "document_analysis"
        
        result = self.agent.llm_router_node(state)
        assert result["active_llm"] == LLMProvider.GEMINI
        
        # Test Claude routing for conversation
        state["current_user_intent"] = "conversation"
        result = self.agent.llm_router_node(state)
        assert result["active_llm"] == LLMProvider.CLAUDE
    
    def test_response_generation(self):
        """Test response generation for different intents."""
        # Test greeting response
        response = self.agent._generate_response("greeting", LLMProvider.GEMINI, self.agent.state)
        assert "Aura" in response
        assert "onboarding" in response.lower()
        
        # Test document analysis response
        response = self.agent._generate_response("document_analysis", LLMProvider.GEMINI, self.agent.state)
        assert "analyze" in response.lower() or "upload" in response.lower()
    
    def test_route_after_response(self):
        """Test routing logic after response generation."""
        state = self.agent.state.copy()
        
        # Test tool execution routing
        state["current_user_intent"] = "document_analysis"
        route = self.agent._route_after_response(state)
        assert route == "tool_execution"
        
        # Test end routing for general inquiry
        state["current_user_intent"] = "general_inquiry"
        route = self.agent._route_after_response(state)
        assert route == "end"
    
    @pytest.mark.asyncio
    async def test_process_input(self):
        """Test the full input processing workflow."""
        user_input = "Hello, I'm starting a new job"
        session_id = "test_session_123"
        
        result = await self.agent.process_input(user_input, session_id)
        
        # Check that conversation history was updated
        assert len(result["conversation_history"]) >= 1
        assert result["conversation_history"][0]["content"] == user_input
        assert result["session_id"] == session_id
    
    def test_state_update(self):
        """Test state update functionality."""
        initial_tasks = len(self.agent.state["completed_tasks"])
        
        updates = {
            "completed_tasks": ["task_1", "task_2"],
            "current_user_intent": "planning"
        }
        
        self.agent.update_state(updates)
        
        assert len(self.agent.state["completed_tasks"]) == 2
        assert self.agent.state["current_user_intent"] == "planning"
    
    def test_workflow_compilation(self):
        """Test that the workflow compiles without errors."""
        assert self.agent.workflow is not None
        
        # Test that all nodes are accessible
        graph_dict = self.agent.workflow.get_graph().to_json()
        assert "intent_recognition" in str(graph_dict)
        assert "llm_router" in str(graph_dict)
        assert "response_generation" in str(graph_dict)

if __name__ == "__main__":
    pytest.main([__file__])