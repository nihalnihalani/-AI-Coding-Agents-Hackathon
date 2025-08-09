from typing import Dict, Any, List
import logging
from datetime import datetime, timedelta
import uuid

from ...models.schemas import OnboardingPlan, TaskStep, TaskStatus, TaskPriority, UserProfile
from ...services.document_service import DocumentService
from ...services.llm_service import LLMRouter
from ...core.logging import get_logger

logger = get_logger(__name__)

class ResumeProcessorNode:
    """Node for processing resumes and generating initial onboarding plans."""
    
    def __init__(self):
        self.document_service = DocumentService()
        self.llm_router = LLMRouter()
    
    async def process_resume(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process uploaded resume and generate onboarding plan."""
        try:
            # Extract resume data and job role from state
            resume_data = state.get("resume_data", {})
            job_role = state.get("job_role", "General Employee")
            
            if not resume_data:
                logger.warning("No resume data found in state")
                return {
                    "errors": state.get("errors", []) + ["No resume data provided"],
                    "last_updated": datetime.now().isoformat()
                }
            
            # Create user profile from resume analysis
            user_profile = await self._create_user_profile_from_resume(resume_data, job_role)
            
            # Generate comprehensive onboarding plan
            onboarding_plan = await self._generate_onboarding_plan(user_profile, job_role)
            
            return {
                "user_profile": user_profile.dict(),
                "onboarding_plan_steps": [step.dict() for step in onboarding_plan.steps],
                "current_step": onboarding_plan.steps[0].step_id if onboarding_plan.steps else None,
                "contextual_memory": {
                    **state.get("contextual_memory", {}),
                    "resume_processed": True,
                    "job_role": job_role,
                    "skills_identified": user_profile.skills,
                    "experience_level": user_profile.experience_years or 0
                },
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in resume processing node: {e}")
            return {
                "errors": state.get("errors", []) + [f"Resume processing failed: {str(e)}"],
                "last_updated": datetime.now().isoformat()
            }
    
    async def _create_user_profile_from_resume(self, resume_data: Dict[str, Any], job_role: str) -> UserProfile:
        """Create detailed user profile from resume analysis."""
        try:
            # Extract basic information
            extracted_data = resume_data.get("extracted_data", {})
            
            return UserProfile(
                user_id=str(uuid.uuid4()),
                name=extracted_data.get("name", "New Employee"),
                email=extracted_data.get("email"),
                phone=extracted_data.get("phone"),
                skills=extracted_data.get("skills", []),
                experience_years=extracted_data.get("experience_years", 0),
                education=extracted_data.get("education", []),
                previous_roles=extracted_data.get("previous_roles", []),
                certifications=extracted_data.get("certifications", []),
                languages=extracted_data.get("languages", ["English"]),
                preferences={
                    "target_role": job_role,
                    "communication_preference": "email",
                    "learning_style": "hands-on",
                    "availability": "full-time"
                }
            )
        except Exception as e:
            logger.error(f"Error creating user profile: {e}")
            raise
    
    async def _generate_onboarding_plan(self, user_profile: UserProfile, job_role: str) -> OnboardingPlan:
        """Generate comprehensive onboarding plan based on user profile and role."""
        try:
            # Create planning prompt for LLM
            planning_prompt = f"""
            Create a comprehensive onboarding plan for a new {job_role} with the following profile:
            
            Name: {user_profile.name}
            Experience: {user_profile.experience_years} years
            Skills: {', '.join(user_profile.skills)}
            Education: {user_profile.education}
            Previous Roles: {user_profile.previous_roles}
            
            Generate a structured onboarding plan with the following phases:
            1. Pre-boarding (before first day)
            2. First Day/Week orientation
            3. Role-specific training (weeks 2-4)
            4. Integration and project assignment (month 2)
            5. Performance review and adjustment (month 3)
            
            For each phase, include specific tasks with:
            - Clear descriptions and objectives
            - Estimated time requirements
            - Required resources and tools
            - Success criteria
            - Dependencies between tasks
            """
            
            # Get LLM response for planning
            llm_response = await self.llm_router.generate_response(
                "planning",
                planning_prompt,
                max_tokens=2000
            )
            
            # Generate structured task steps
            task_steps = await self._create_structured_tasks(user_profile, job_role, llm_response)
            
            # Create onboarding plan
            plan = OnboardingPlan(
                plan_id=str(uuid.uuid4()),
                user_id=user_profile.user_id,
                job_role=job_role,
                start_date=datetime.now(),
                expected_completion=datetime.now() + timedelta(days=90),
                steps=task_steps,
                created_by_llm=llm_response.get("llm_used", "gemini")
            )
            
            return plan
            
        except Exception as e:
            logger.error(f"Error generating onboarding plan: {e}")
            raise
    
    async def _create_structured_tasks(self, user_profile: UserProfile, job_role: str, llm_response: Dict[str, Any]) -> List[TaskStep]:
        """Create structured task steps from LLM planning response."""
        try:
            # Pre-defined task templates based on common onboarding needs
            base_tasks = [
                # Pre-boarding tasks
                {
                    "title": "Complete HR Documentation",
                    "description": "Fill out all required HR forms, tax documents, and employment agreements",
                    "phase": "pre-boarding",
                    "priority": TaskPriority.HIGH,
                    "estimated_duration": 60,
                    "approval_required": True
                },
                {
                    "title": "IT Setup and Account Creation",
                    "description": "Set up email account, access credentials, and necessary software installations",
                    "phase": "pre-boarding",
                    "priority": TaskPriority.HIGH,
                    "estimated_duration": 90,
                    "approval_required": False
                },
                
                # First day/week tasks
                {
                    "title": "Office Tour and Introduction",
                    "description": "Meet team members, understand office layout, and learn basic procedures",
                    "phase": "orientation",
                    "priority": TaskPriority.HIGH,
                    "estimated_duration": 120,
                    "approval_required": False
                },
                {
                    "title": "Company Culture and Values Training",
                    "description": "Learn about company mission, values, culture, and expectations",
                    "phase": "orientation",
                    "priority": TaskPriority.MEDIUM,
                    "estimated_duration": 180,
                    "approval_required": False
                },
                
                # Role-specific training
                {
                    "title": f"{job_role} Role Overview",
                    "description": f"Understand responsibilities, expectations, and success metrics for {job_role}",
                    "phase": "role-training",
                    "priority": TaskPriority.HIGH,
                    "estimated_duration": 240,
                    "approval_required": False
                },
                {
                    "title": "Tools and Systems Training",
                    "description": "Learn to use role-specific tools, software, and internal systems",
                    "phase": "role-training",
                    "priority": TaskPriority.HIGH,
                    "estimated_duration": 300,
                    "approval_required": False
                },
                
                # Integration tasks
                {
                    "title": "First Project Assignment",
                    "description": "Begin working on initial project to apply learned skills",
                    "phase": "integration",
                    "priority": TaskPriority.MEDIUM,
                    "estimated_duration": 480,
                    "approval_required": True
                },
                {
                    "title": "30-Day Performance Check-in",
                    "description": "Review progress, address concerns, and adjust plan as needed",
                    "phase": "review",
                    "priority": TaskPriority.HIGH,
                    "estimated_duration": 60,
                    "approval_required": False
                }
            ]
            
            # Create TaskStep objects
            tasks = []
            for i, task_data in enumerate(base_tasks):
                task_step = TaskStep(
                    step_id=f"task_{i+1:03d}",
                    title=task_data["title"],
                    description=task_data["description"],
                    status=TaskStatus.PENDING,
                    priority=task_data["priority"],
                    estimated_duration=task_data["estimated_duration"],
                    dependencies=self._calculate_dependencies(i, task_data["phase"]),
                    assigned_tools=self._assign_tools_for_task(task_data),
                    completion_criteria=self._generate_completion_criteria(task_data),
                    resources=self._generate_resources(task_data, job_role),
                    deadline=self._calculate_deadline(i, task_data["phase"]),
                    approval_required=task_data["approval_required"]
                )
                tasks.append(task_step)
            
            return tasks
            
        except Exception as e:
            logger.error(f"Error creating structured tasks: {e}")
            return []
    
    def _calculate_dependencies(self, task_index: int, phase: str) -> List[str]:
        """Calculate task dependencies based on phase and order."""
        if task_index == 0:
            return []
        elif phase == "pre-boarding":
            return []
        elif phase == "orientation":
            return ["task_001", "task_002"]  # Depend on pre-boarding tasks
        elif phase == "role-training":
            return ["task_003"]  # Depend on orientation
        elif phase == "integration":
            return ["task_005", "task_006"]  # Depend on role training
        else:
            return [f"task_{task_index:03d}"]
    
    def _assign_tools_for_task(self, task_data: Dict[str, Any]) -> List[str]:
        """Assign appropriate tools for each task."""
        phase = task_data["phase"]
        if phase == "pre-boarding":
            return ["slack_tool", "calendar_tool"]
        elif phase == "orientation":
            return ["slack_tool", "calendar_tool"]
        elif phase == "role-training":
            return ["github_tool", "document_tool"]
        elif phase == "integration":
            return ["github_tool", "calendar_tool", "slack_tool"]
        else:
            return ["calendar_tool"]
    
    def _generate_completion_criteria(self, task_data: Dict[str, Any]) -> List[str]:
        """Generate completion criteria for tasks."""
        title = task_data["title"].lower()
        if "documentation" in title:
            return ["All required forms completed", "Documents submitted to HR", "Confirmation received"]
        elif "setup" in title or "account" in title:
            return ["Email account active", "Software installed", "Access credentials working"]
        elif "tour" in title or "introduction" in title:
            return ["Met all team members", "Familiar with office layout", "Basic procedures understood"]
        elif "training" in title:
            return ["Training materials completed", "Quiz passed (if applicable)", "Understanding confirmed by supervisor"]
        elif "project" in title:
            return ["Project requirements understood", "Initial deliverables completed", "Progress reviewed with team"]
        else:
            return ["Task completed successfully", "Documentation updated", "Stakeholders notified"]
    
    def _generate_resources(self, task_data: Dict[str, Any], job_role: str) -> List[Dict[str, str]]:
        """Generate relevant resources for each task."""
        phase = task_data["phase"]
        resources = []
        
        if phase == "pre-boarding":
            resources.extend([
                {"type": "document", "title": "Employee Handbook", "url": "/resources/handbook.pdf"},
                {"type": "form", "title": "HR Forms Portal", "url": "/hr/forms"},
                {"type": "contact", "title": "HR Support", "url": "mailto:hr@company.com"}
            ])
        elif phase == "orientation":
            resources.extend([
                {"type": "document", "title": "Company Culture Guide", "url": "/resources/culture.pdf"},
                {"type": "video", "title": "Welcome Video", "url": "/resources/welcome-video"},
                {"type": "directory", "title": "Team Directory", "url": "/directory"}
            ])
        elif phase == "role-training":
            resources.extend([
                {"type": "document", "title": f"{job_role} Training Manual", "url": f"/training/{job_role.lower().replace(' ', '-')}"},
                {"type": "tool", "title": "Learning Management System", "url": "/lms"},
                {"type": "contact", "title": "Training Coordinator", "url": "mailto:training@company.com"}
            ])
        
        return resources
    
    def _calculate_deadline(self, task_index: int, phase: str) -> datetime:
        """Calculate appropriate deadlines for tasks."""
        base_date = datetime.now()
        
        if phase == "pre-boarding":
            return base_date + timedelta(days=-1)  # Before start date
        elif phase == "orientation":
            return base_date + timedelta(days=1 + task_index)
        elif phase == "role-training":
            return base_date + timedelta(weeks=2 + (task_index * 0.5))
        elif phase == "integration":
            return base_date + timedelta(weeks=6 + task_index)
        else:
            return base_date + timedelta(weeks=12)