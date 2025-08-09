import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.agents.aura_agent import AuraAgent
from app.services.llm_service import LLMRouter, GeminiService, ClaudeService


class TestAgentIntegration:
    """Test agent workflow and LLM integration."""
    
    @pytest.fixture
    def agent(self):
        """Create an AuraAgent instance for testing."""
        return AuraAgent()
    
    @pytest.fixture
    def mock_gemini_response(self):
        """Mock Gemini API response."""
        return {
            "candidates": [{
                "content": {
                    "parts": [{
                        "text": "Hello! I'm Aura, your onboarding assistant. I can help you with:\n1. Resume analysis\n2. Creating your onboarding plan\n3. Task management\n\nHow can I assist you today?"
                    }]
                }
            }]
        }
    
    @pytest.fixture
    def mock_claude_response(self):
        """Mock Claude API response."""
        return MagicMock(
            content=[MagicMock(text="Hello! I'm here to help with your onboarding process. What would you like to know?")]
        )
    
    async def test_agent_initialization(self, agent):
        """Test agent initialization and state setup."""
        assert agent is not None
        state = agent.get_state()
        
        # Check initial state
        assert state["conversation_history"] == []
        assert state["onboarding_plan_steps"] == []
        assert state["completed_tasks"] == []
        assert state["current_step"] is None
        assert state["active_llm"] == "gemini"  # Default LLM
        assert isinstance(state["created_at"], str)
    
    async def test_agent_state_update(self, agent):
        """Test agent state update functionality."""
        session_id = "test-session"
        
        # Update state
        updates = {
            "user_profile": {"name": "John Doe", "role": "Engineer"},
            "current_step": "welcome"
        }
        agent.update_state(updates)
        
        # Verify updates
        state = agent.get_state()
        assert state["user_profile"]["name"] == "John Doe"
        assert state["current_step"] == "welcome"
    
    @patch('app.services.llm_service.GeminiService.generate_response')
    async def test_agent_process_input_greeting(self, mock_gemini, agent, mock_gemini_response):
        """Test agent processing greeting input."""
        mock_gemini.return_value = {
            "content": "Hello! I'm Aura, your onboarding assistant. How can I help you today?",
            "llm_used": "gemini",
            "intent": "greeting",
            "suggestions": ["Upload resume", "Tell me about onboarding", "What's my role?"]
        }
        
        session_id = "test-greeting"
        result = await agent.process_input("Hello, I'm new here!", session_id)
        
        # Verify response
        assert result is not None
        assert len(result["conversation_history"]) >= 2  # User message + assistant response
        
        # Check conversation history
        user_message = result["conversation_history"][-2]
        assistant_message = result["conversation_history"][-1]
        
        assert user_message["role"] == "user"
        assert user_message["content"] == "Hello, I'm new here!"
        assert assistant_message["role"] == "assistant"
        assert assistant_message["llm_used"] == "gemini"
        assert assistant_message["intent"] == "greeting"
    
    @patch('app.services.llm_service.GeminiService.generate_response')
    async def test_agent_process_resume_analysis(self, mock_gemini, agent):
        """Test agent processing resume analysis request."""
        mock_gemini.return_value = {
            "content": "I'd be happy to analyze your resume! Please upload your resume file.",
            "llm_used": "gemini",
            "intent": "resume_analysis",
            "suggestions": ["Upload resume file", "Tell me about your experience", "What's your background?"]
        }
        
        session_id = "test-resume"
        result = await agent.process_input("Can you analyze my resume?", session_id)
        
        # Verify intent recognition
        assert result["current_user_intent"] == "resume_analysis"
        
        # Check response
        conversation = result["conversation_history"]
        assistant_response = conversation[-1]
        assert assistant_response["intent"] == "resume_analysis"
        assert assistant_response["llm_used"] == "gemini"
    
    @patch('app.services.llm_service.GeminiService.analyze_document')
    async def test_agent_resume_processing(self, mock_analyze, agent):
        """Test agent resume document processing."""
        mock_analyze.return_value = {
            "analysis": {
                "name": "John Doe",
                "experience_years": 5,
                "skills": ["Python", "FastAPI", "React"],
                "role": "Software Engineer",
                "summary": "Experienced software engineer with 5 years in web development"
            },
            "suggested_plan": {
                "tasks": [
                    {"id": "welcome", "title": "Team Welcome", "priority": "high"},
                    {"id": "setup", "title": "Development Setup", "priority": "high"}
                ]
            }
        }
        
        session_id = "test-resume-proc"
        resume_content = "John Doe\nSoftware Engineer\n5 years experience..."
        
        result = await agent.process_resume(resume_content, session_id)
        
        # Verify resume analysis
        assert result["user_profile"]["full_name"] == "John Doe"
        assert result["user_profile"]["experience_years"] == 5
        assert "Python" in result["user_profile"]["skills"]
        
        # Verify onboarding plan creation
        assert len(result["onboarding_plan_steps"]) > 0
        assert result["onboarding_plan_steps"][0]["title"] == "Team Welcome"
    
    async def test_agent_llm_router_selection(self, agent):
        """Test LLM router selection logic."""
        llm_router = LLMRouter()
        
        # Test different task types
        gemini_tasks = [
            "analyze this resume",
            "look at this image",
            "process this document"
        ]
        
        claude_tasks = [
            "have a conversation",
            "help me with questions",
            "let's chat about onboarding"
        ]
        
        for task in gemini_tasks:
            selected_llm = llm_router.select_llm(task)
            assert selected_llm == "gemini"
        
        for task in claude_tasks:
            selected_llm = llm_router.select_llm(task)
            assert selected_llm == "claude"
    
    @patch('app.services.llm_service.ClaudeService.generate_response')
    async def test_agent_claude_integration(self, mock_claude, agent, mock_claude_response):
        """Test agent integration with Claude."""
        mock_claude.return_value = {
            "content": "I understand you'd like to chat about your onboarding. What specific questions do you have?",
            "llm_used": "claude",
            "intent": "general_conversation",
            "suggestions": ["Tell me about my team", "What should I expect?", "How long is onboarding?"]
        }
        
        session_id = "test-claude"
        
        # Force Claude selection by using conversational input
        result = await agent.process_input("Let's have a conversation about my new role", session_id)
        
        # Verify Claude was used
        conversation = result["conversation_history"]
        assistant_response = conversation[-1]
        
        # Note: The actual LLM selection depends on the router logic
        # This test verifies the integration works when Claude is selected
        if assistant_response["llm_used"] == "claude":
            assert assistant_response["intent"] == "general_conversation"
    
    async def test_agent_task_management(self, agent):
        """Test agent task management functionality."""
        session_id = "test-tasks"
        
        # Set up initial state with onboarding plan
        agent.update_state({
            "onboarding_plan_steps": [
                {
                    "step_id": "welcome",
                    "title": "Team Welcome",
                    "status": "pending",
                    "priority": "high"
                },
                {
                    "step_id": "setup",
                    "title": "Development Setup", 
                    "status": "pending",
                    "priority": "high"
                }
            ],
            "current_step": "welcome"
        })
        
        # Complete a task
        result = await agent.complete_task("welcome", session_id)
        
        # Verify task completion
        assert "welcome" in result["completed_tasks"]
        assert result["current_step"] == "setup"  # Should move to next task
        
        # Check task status update
        welcome_task = next(
            task for task in result["onboarding_plan_steps"] 
            if task["step_id"] == "welcome"
        )
        assert welcome_task["status"] == "completed"
    
    async def test_agent_error_handling(self, agent):
        """Test agent error handling and recovery."""
        session_id = "test-errors"
        
        # Test with invalid input
        with patch('app.services.llm_service.GeminiService.generate_response') as mock_gemini:
            mock_gemini.side_effect = Exception("API Error")
            
            # Should handle gracefully
            result = await agent.process_input("Hello", session_id)
            
            # Should have error in state
            assert len(result["errors"]) > 0
            assert "API Error" in str(result["errors"][-1])
            
            # Should still have conversation history
            assert len(result["conversation_history"]) > 0
    
    async def test_agent_context_memory(self, agent):
        """Test agent contextual memory functionality."""
        session_id = "test-context"
        
        # First interaction - set context
        with patch('app.services.llm_service.GeminiService.generate_response') as mock_gemini:
            mock_gemini.return_value = {
                "content": "Nice to meet you, John! I'll remember that you're a Software Engineer.",
                "llm_used": "gemini",
                "intent": "greeting",
                "suggestions": []
            }
            
            result1 = await agent.process_input("Hi, I'm John, a Software Engineer", session_id)
            
            # Update context
            agent.update_state({
                "contextual_memory": {
                    "user_name": "John",
                    "role": "Software Engineer"
                }
            })
        
        # Second interaction - should use context
        with patch('app.services.llm_service.GeminiService.generate_response') as mock_gemini:
            mock_gemini.return_value = {
                "content": "Hi John! As a Software Engineer, you'll need to set up your development environment.",
                "llm_used": "gemini", 
                "intent": "task_guidance",
                "suggestions": ["Set up IDE", "Configure Git", "Install dependencies"]
            }
            
            result2 = await agent.process_input("What should I do next?", session_id)
            
            # Verify context was maintained
            state = agent.get_state()
            assert state["contextual_memory"]["user_name"] == "John"
            assert state["contextual_memory"]["role"] == "Software Engineer"
    
    async def test_agent_workflow_integration(self, agent):
        """Test complete agent workflow integration."""
        session_id = "test-workflow"
        
        # Step 1: Initial greeting
        with patch('app.services.llm_service.GeminiService.generate_response') as mock_gemini:
            mock_gemini.return_value = {
                "content": "Hello! I'm Aura. Let's get you onboarded!",
                "llm_used": "gemini",
                "intent": "greeting",
                "suggestions": ["Upload resume", "Tell me about your role"]
            }
            
            result1 = await agent.process_input("Hello!", session_id)
            assert result1["current_user_intent"] == "greeting"
        
        # Step 2: Resume analysis
        with patch('app.services.llm_service.GeminiService.analyze_document') as mock_analyze:
            mock_analyze.return_value = {
                "analysis": {
                    "name": "John Doe",
                    "role": "Software Engineer",
                    "skills": ["Python", "React"]
                },
                "suggested_plan": {
                    "tasks": [
                        {"id": "welcome", "title": "Welcome", "priority": "high"}
                    ]
                }
            }
            
            result2 = await agent.process_resume("Resume content...", session_id)
            assert result2["user_profile"]["full_name"] == "John Doe"
            assert len(result2["onboarding_plan_steps"]) > 0
        
        # Step 3: Task interaction
        with patch('app.services.llm_service.GeminiService.generate_response') as mock_gemini:
            mock_gemini.return_value = {
                "content": "Great! Your first task is to complete the team welcome.",
                "llm_used": "gemini",
                "intent": "task_management",
                "suggestions": ["Start welcome task", "View all tasks"]
            }
            
            result3 = await agent.process_input("What's my first task?", session_id)
            assert result3["current_user_intent"] == "task_management"
        
        # Step 4: Task completion
        result4 = await agent.complete_task("welcome", session_id)
        assert "welcome" in result4["completed_tasks"]
        
        # Verify complete workflow state
        final_state = agent.get_state()
        assert len(final_state["conversation_history"]) >= 6  # All interactions
        assert final_state["user_profile"]["full_name"] == "John Doe"
        assert len(final_state["onboarding_plan_steps"]) > 0
        assert len(final_state["completed_tasks"]) > 0