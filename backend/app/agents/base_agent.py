from typing import TypedDict, List, Dict, Any, Optional
from enum import Enum

class OnboardingStepStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"

class LLMProvider(str, Enum):
    GEMINI = "gemini"
    CLAUDE = "claude"

class AgentState(TypedDict):
    """Core agent state schema for Aura onboarding agent."""
    
    # User context
    user_id: Optional[str]
    user_profile: Optional[Dict[str, Any]]
    resume_data: Optional[Dict[str, Any]]
    job_role: Optional[str]
    
    # Intent and conversation
    current_user_intent: Optional[str]
    conversation_history: List[Dict[str, Any]]
    contextual_memory: Dict[str, Any]
    
    # Onboarding plan
    onboarding_plan_steps: List[Dict[str, Any]]
    completed_tasks: List[str]
    current_step: Optional[str]
    
    # LLM management
    active_llm: LLMProvider
    llm_context: Dict[str, Any]
    
    # External tool states
    tool_states: Dict[str, Any]
    pending_approvals: List[Dict[str, Any]]
    
    # Session management
    session_id: str
    last_updated: Optional[str]
    errors: List[str]

class BaseOnboardingAgent:
    """Base class for the Aura onboarding agent."""
    
    def __init__(self):
        self.state: AgentState = self._initialize_state()
    
    def _initialize_state(self) -> AgentState:
        """Initialize the default agent state."""
        return AgentState(
            user_id=None,
            user_profile=None,
            resume_data=None,
            job_role=None,
            current_user_intent=None,
            conversation_history=[],
            contextual_memory={},
            onboarding_plan_steps=[],
            completed_tasks=[],
            current_step=None,
            active_llm=LLMProvider.GEMINI,
            llm_context={},
            tool_states={},
            pending_approvals=[],
            session_id="",
            last_updated=None,
            errors=[]
        )
    
    def update_state(self, updates: Dict[str, Any]) -> None:
        """Update the agent state with new values."""
        for key, value in updates.items():
            if key in self.state:
                self.state[key] = value
    
    def get_state(self) -> AgentState:
        """Get the current agent state."""
        return self.state