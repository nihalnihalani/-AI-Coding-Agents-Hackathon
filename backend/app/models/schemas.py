from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum

class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"

class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class LLMProvider(str, Enum):
    GEMINI = "gemini"
    CLAUDE = "claude"

class UserProfile(BaseModel):
    """User profile information extracted from resume and input."""
    user_id: str
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    experience_years: Optional[int] = None
    education: List[Dict[str, Any]] = Field(default_factory=list)
    previous_roles: List[Dict[str, Any]] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)
    languages: List[str] = Field(default_factory=list)
    preferences: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class TaskStep(BaseModel):
    """Individual task step in the onboarding plan."""
    step_id: str
    title: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    estimated_duration: Optional[int] = None  # in minutes
    dependencies: List[str] = Field(default_factory=list)
    assigned_tools: List[str] = Field(default_factory=list)
    completion_criteria: List[str] = Field(default_factory=list)
    resources: List[Dict[str, str]] = Field(default_factory=list)
    deadline: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    notes: str = ""
    approval_required: bool = False

class OnboardingPlan(BaseModel):
    """Complete onboarding plan for a user."""
    plan_id: str
    user_id: str
    job_role: str
    department: Optional[str] = None
    manager: Optional[str] = None
    buddy_mentor: Optional[str] = None
    
    # Plan structure
    total_steps: int = 0
    completed_steps: int = 0
    current_step: Optional[str] = None
    steps: List[TaskStep] = Field(default_factory=list)
    
    # Timeline
    start_date: datetime
    expected_completion: Optional[datetime] = None
    actual_completion: Optional[datetime] = None
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    created_by_llm: LLMProvider = LLMProvider.GEMINI
    
    @validator('total_steps', always=True)
    def calculate_total_steps(cls, v, values):
        if 'steps' in values:
            return len(values['steps'])
        return v
    
    @validator('completed_steps', always=True)
    def calculate_completed_steps(cls, v, values):
        if 'steps' in values:
            return len([step for step in values['steps'] if step.status == TaskStatus.COMPLETED])
        return v

class ConversationMessage(BaseModel):
    """Individual message in a conversation."""
    message_id: str
    session_id: str
    role: str  # "user" or "assistant"
    content: str
    llm_used: Optional[LLMProvider] = None
    intent: Optional[str] = None
    confidence: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)

class AgentSession(BaseModel):
    """Agent session information."""
    session_id: str
    user_id: Optional[str] = None
    status: str = "active"  # active, paused, completed
    conversation_history: List[ConversationMessage] = Field(default_factory=list)
    context: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    last_activity: datetime = Field(default_factory=datetime.now)

class ApprovalRequest(BaseModel):
    """Human approval request for agent actions."""
    request_id: str
    session_id: str
    action_type: str
    action_description: str
    action_details: Dict[str, Any] = Field(default_factory=dict)
    risk_level: str = "medium"  # low, medium, high
    requester: str = "aura_agent"
    
    # Approval workflow
    status: str = "pending"  # pending, approved, rejected, expired
    approved_by: Optional[str] = None
    approval_reason: Optional[str] = None
    approved_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    
    created_at: datetime = Field(default_factory=datetime.now)

class DocumentAnalysis(BaseModel):
    """Results from document analysis."""
    document_id: str
    document_type: str  # resume, policy, handbook, etc.
    file_name: str
    analysis_summary: str
    extracted_data: Dict[str, Any] = Field(default_factory=dict)
    confidence_scores: Dict[str, float] = Field(default_factory=dict)
    llm_used: LLMProvider
    processing_time: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.now)

# Request/Response models for API endpoints

class ResumeUploadRequest(BaseModel):
    """Request for resume upload."""
    job_role: str
    department: Optional[str] = None
    additional_context: Optional[str] = None

class ResumeUploadResponse(BaseModel):
    """Response after resume processing."""
    document_id: str
    user_profile: UserProfile
    onboarding_plan: OnboardingPlan
    analysis: DocumentAnalysis
    message: str = "Resume processed successfully"

class ChatRequest(BaseModel):
    """Chat message request."""
    message: str
    session_id: str
    context: Optional[Dict[str, Any]] = None

class ChatResponse(BaseModel):
    """Chat message response."""
    response: str
    session_id: str
    message_id: str
    llm_used: LLMProvider
    intent: Optional[str] = None
    suggested_actions: List[str] = Field(default_factory=list)
    updated_plan: Optional[OnboardingPlan] = None

class ProgressUpdateRequest(BaseModel):
    """Request to update task progress."""
    step_id: str
    status: TaskStatus
    notes: Optional[str] = None
    completion_evidence: Optional[Dict[str, Any]] = None

class ProgressUpdateResponse(BaseModel):
    """Response after progress update."""
    step_id: str
    updated_status: TaskStatus
    updated_plan: OnboardingPlan
    message: str
    next_recommended_step: Optional[str] = None