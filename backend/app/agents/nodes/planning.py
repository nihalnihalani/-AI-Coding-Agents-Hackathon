from typing import Dict, Any, List, Optional, Tuple
import logging
from datetime import datetime, timedelta
import uuid

from ...models.schemas import OnboardingPlan, TaskStep, TaskStatus, TaskPriority, UserProfile
from ...services.llm_service import LLMRouter
from ...tools.registry import tool_registry
from ...core.logging import get_logger

logger = get_logger(__name__)

class PlanningNode:
    """Node for multi-step task decomposition and intelligent onboarding planning."""
    
    def __init__(self):
        self.llm_router = LLMRouter()
        
        # Planning templates for different scenarios
        self.planning_templates = {
            "technical_role": {
                "phases": ["setup", "training", "integration", "contribution"],
                "duration_weeks": 8,
                "key_focus_areas": ["technical_skills", "team_integration", "project_familiarity"]
            },
            "management_role": {
                "phases": ["orientation", "team_building", "strategic_alignment", "leadership"],
                "duration_weeks": 12,
                "key_focus_areas": ["team_dynamics", "business_strategy", "stakeholder_relations"]
            },
            "entry_level": {
                "phases": ["basics", "skill_building", "mentorship", "independence"],
                "duration_weeks": 6,
                "key_focus_areas": ["foundational_knowledge", "skill_development", "guidance"]
            },
            "experienced_hire": {
                "phases": ["context_setting", "quick_integration", "value_delivery", "optimization"],
                "duration_weeks": 4,
                "key_focus_areas": ["company_context", "immediate_impact", "process_optimization"]
            }
        }
        
        # Task complexity scoring
        self.complexity_factors = {
            "requires_approval": 2.0,
            "involves_multiple_stakeholders": 1.5,
            "technical_setup": 1.3,
            "training_dependent": 1.2,
            "documentation_heavy": 1.1
        }
    
    async def create_comprehensive_plan(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Create a comprehensive onboarding plan with intelligent task decomposition."""
        try:
            # Extract planning context
            user_profile = state.get("user_profile", {})
            job_role = state.get("job_role", "General Employee")
            contextual_memory = state.get("contextual_memory", {})
            
            # Determine planning approach
            planning_approach = self._determine_planning_approach(user_profile, job_role, contextual_memory)
            
            # Generate high-level plan structure
            plan_structure = await self._generate_plan_structure(user_profile, job_role, planning_approach)
            
            # Decompose into detailed tasks
            detailed_tasks = await self._decompose_into_tasks(plan_structure, user_profile, job_role)
            
            # Optimize task dependencies and scheduling
            optimized_tasks = self._optimize_task_scheduling(detailed_tasks)
            
            # Create final onboarding plan
            onboarding_plan = self._create_onboarding_plan(
                optimized_tasks, user_profile, job_role, planning_approach
            )
            
            # Generate tool assignments
            tool_assignments = self._assign_tools_to_tasks(optimized_tasks)
            
            return {
                "onboarding_plan_steps": [task.dict() for task in optimized_tasks],
                "planning_metadata": {
                    "approach": planning_approach,
                    "total_tasks": len(optimized_tasks),
                    "estimated_duration_weeks": plan_structure.get("duration_weeks", 8),
                    "key_milestones": plan_structure.get("milestones", []),
                    "tool_assignments": tool_assignments
                },
                "current_step": optimized_tasks[0].step_id if optimized_tasks else None,
                "contextual_memory": {
                    **contextual_memory,
                    "plan_created": True,
                    "planning_approach": planning_approach["template_name"],
                    "plan_complexity": self._calculate_plan_complexity(optimized_tasks)
                },
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error creating comprehensive plan: {e}")
            return {
                "errors": state.get("errors", []) + [f"Planning failed: {str(e)}"],
                "last_updated": datetime.now().isoformat()
            }
    
    async def adjust_plan_dynamically(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Dynamically adjust the onboarding plan based on progress and feedback."""
        try:
            current_plan = state.get("onboarding_plan_steps", [])
            completed_tasks = state.get("completed_tasks", [])
            current_step = state.get("current_step")
            contextual_memory = state.get("contextual_memory", {})
            
            if not current_plan:
                # No plan exists, create one
                return await self.create_comprehensive_plan(state)
            
            # Analyze current progress
            progress_analysis = self._analyze_progress(current_plan, completed_tasks, current_step)
            
            # Identify adjustment needs
            adjustment_needs = await self._identify_adjustment_needs(
                progress_analysis, contextual_memory, state
            )
            
            # Apply adjustments
            adjusted_plan = self._apply_plan_adjustments(
                current_plan, adjustment_needs, progress_analysis
            )
            
            # Re-optimize if significant changes
            if adjustment_needs.get("requires_reoptimization", False):
                adjusted_plan = self._optimize_task_scheduling(adjusted_plan)
            
            return {
                "onboarding_plan_steps": [task.dict() if hasattr(task, 'dict') else task for task in adjusted_plan],
                "plan_adjustments": {
                    "adjustments_made": adjustment_needs.get("adjustments", []),
                    "reason": adjustment_needs.get("reason", "Dynamic optimization"),
                    "impact_assessment": adjustment_needs.get("impact", "minimal")
                },
                "contextual_memory": {
                    **contextual_memory,
                    "last_plan_adjustment": datetime.now().isoformat(),
                    "adjustment_count": contextual_memory.get("adjustment_count", 0) + 1
                },
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error adjusting plan dynamically: {e}")
            return {
                "errors": state.get("errors", []) + [f"Plan adjustment failed: {str(e)}"],
                "last_updated": datetime.now().isoformat()
            }
    
    def _determine_planning_approach(self, user_profile: Dict[str, Any], job_role: str,
                                   contextual_memory: Dict[str, Any]) -> Dict[str, Any]:
        """Determine the most appropriate planning approach based on context."""
        
        # Extract relevant factors
        experience_years = user_profile.get("experience_years", 0)
        skills = user_profile.get("skills", [])
        job_role_lower = job_role.lower()
        
        # Determine base template
        if any(keyword in job_role_lower for keyword in ["manager", "director", "lead", "head"]):
            base_template = "management_role"
        elif experience_years >= 5:
            base_template = "experienced_hire"
        elif experience_years <= 1:
            base_template = "entry_level"
        else:
            base_template = "technical_role"
        
        # Get template configuration
        template_config = self.planning_templates.get(base_template, self.planning_templates["technical_role"])
        
        # Customize based on specific context
        customizations = []
        
        # Technical skills adjustment
        technical_skills = [skill for skill in skills if any(tech in skill.lower() 
                           for tech in ["python", "javascript", "sql", "aws", "docker", "react"])]
        if len(technical_skills) > 5:
            customizations.append("advanced_technical")
            template_config["duration_weeks"] -= 1
        elif len(technical_skills) < 2 and "technical" in base_template:
            customizations.append("technical_training_focus")
            template_config["duration_weeks"] += 2
        
        # Remote work adjustment
        if contextual_memory.get("remote_employee", False):
            customizations.append("remote_onboarding")
            template_config["key_focus_areas"].append("virtual_collaboration")
        
        return {
            "template_name": base_template,
            "customizations": customizations,
            "config": template_config,
            "reasoning": f"Selected {base_template} based on {experience_years} years experience and {job_role} role"
        }
    
    async def _generate_plan_structure(self, user_profile: Dict[str, Any], job_role: str,
                                     planning_approach: Dict[str, Any]) -> Dict[str, Any]:
        """Generate high-level plan structure using LLM."""
        try:
            # Build planning prompt
            planning_prompt = self._build_planning_prompt(user_profile, job_role, planning_approach)
            
            # Get LLM response for high-level planning
            llm_response = await self.llm_router.generate_response(
                "planning",
                planning_prompt,
                max_tokens=1500
            )
            
            # Parse the response into structured format
            plan_structure = self._parse_plan_structure(llm_response.get("response", ""), planning_approach)
            
            return plan_structure
            
        except Exception as e:
            logger.error(f"Error generating plan structure: {e}")
            # Fallback to template-based structure
            return self._create_fallback_structure(planning_approach)
    
    def _build_planning_prompt(self, user_profile: Dict[str, Any], job_role: str,
                             planning_approach: Dict[str, Any]) -> str:
        """Build comprehensive planning prompt for LLM."""
        
        template_config = planning_approach.get("config", {})
        phases = template_config.get("phases", [])
        duration_weeks = template_config.get("duration_weeks", 8)
        focus_areas = template_config.get("key_focus_areas", [])
        
        prompt = f"""Create a comprehensive onboarding plan for a new {job_role} with the following profile:

Employee Profile:
- Experience: {user_profile.get('experience_years', 0)} years
- Key Skills: {', '.join(user_profile.get('skills', [])[:5])}
- Education: {user_profile.get('education', 'Not specified')}
- Previous Roles: {user_profile.get('previous_roles', 'Not specified')}

Planning Parameters:
- Template: {planning_approach.get('template_name')}
- Duration: {duration_weeks} weeks
- Key Phases: {', '.join(phases)}
- Focus Areas: {', '.join(focus_areas)}
- Customizations: {', '.join(planning_approach.get('customizations', []))}

Create a structured plan with:

1. **Phase Breakdown**: Divide the {duration_weeks}-week period into logical phases
2. **Milestone Definition**: Key achievements for each phase
3. **Priority Areas**: Most critical aspects for this specific employee
4. **Success Metrics**: How to measure progress and success
5. **Risk Mitigation**: Potential challenges and mitigation strategies

Format the response as a structured plan with clear phases, objectives, and timelines.
"""
        
        return prompt
    
    def _parse_plan_structure(self, llm_response: str, planning_approach: Dict[str, Any]) -> Dict[str, Any]:
        """Parse LLM response into structured plan format."""
        try:
            # This is a simplified parser - in production, you'd have more sophisticated parsing
            lines = llm_response.split('\n')
            
            structure = {
                "phases": [],
                "milestones": [],
                "duration_weeks": planning_approach.get("config", {}).get("duration_weeks", 8),
                "success_metrics": [],
                "risk_factors": []
            }
            
            current_section = None
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Identify sections
                if "phase" in line.lower() and ("1" in line or "2" in line or "3" in line or "4" in line):
                    phase_info = {"name": line, "objectives": [], "duration": "2 weeks"}
                    structure["phases"].append(phase_info)
                    current_section = "phase"
                elif "milestone" in line.lower():
                    current_section = "milestone"
                elif "success" in line.lower() or "metric" in line.lower():
                    current_section = "success"
                elif "risk" in line.lower() or "challenge" in line.lower():
                    current_section = "risk"
                elif line.startswith('-') or line.startswith('•'):
                    # Handle bullet points
                    content = line.lstrip('- •').strip()
                    if current_section == "phase" and structure["phases"]:
                        structure["phases"][-1]["objectives"].append(content)
                    elif current_section == "milestone":
                        structure["milestones"].append(content)
                    elif current_section == "success":
                        structure["success_metrics"].append(content)
                    elif current_section == "risk":
                        structure["risk_factors"].append(content)
            
            return structure
            
        except Exception as e:
            logger.error(f"Error parsing plan structure: {e}")
            return self._create_fallback_structure(planning_approach)
    
    def _create_fallback_structure(self, planning_approach: Dict[str, Any]) -> Dict[str, Any]:
        """Create fallback plan structure when LLM parsing fails."""
        config = planning_approach.get("config", {})
        
        return {
            "phases": [
                {
                    "name": f"Phase {i+1}: {phase.title()}",
                    "objectives": [f"Complete {phase} activities", f"Meet {phase} milestones"],
                    "duration": f"{config.get('duration_weeks', 8) // len(config.get('phases', [])))} weeks"
                }
                for i, phase in enumerate(config.get("phases", ["setup", "learning", "integration", "contribution"]))
            ],
            "milestones": ["Initial setup complete", "Training milestones achieved", "First contribution made"],
            "duration_weeks": config.get("duration_weeks", 8),
            "success_metrics": ["All tasks completed on time", "Positive feedback from team", "Successful integration"],
            "risk_factors": ["Technology learning curve", "Team integration challenges", "Workload management"]
        }
    
    async def _decompose_into_tasks(self, plan_structure: Dict[str, Any], user_profile: Dict[str, Any],
                                  job_role: str) -> List[TaskStep]:
        """Decompose high-level plan into detailed, actionable tasks."""
        try:
            tasks = []
            task_counter = 1
            
            phases = plan_structure.get("phases", [])
            base_date = datetime.now()
            
            for phase_idx, phase in enumerate(phases):
                phase_name = phase.get("name", f"Phase {phase_idx + 1}")
                objectives = phase.get("objectives", [])
                
                # Calculate phase timing
                phase_start_weeks = phase_idx * 2  # Assume 2 weeks per phase
                phase_start_date = base_date + timedelta(weeks=phase_start_weeks)
                
                # Create tasks for each objective
                for obj_idx, objective in enumerate(objectives):
                    task_tasks = self._create_tasks_for_objective(
                        objective, phase_name, task_counter, phase_start_date, user_profile, job_role
                    )
                    tasks.extend(task_tasks)
                    task_counter += len(task_tasks)
                
                # Add phase milestone task
                milestone_task = self._create_milestone_task(
                    phase_name, task_counter, phase_start_date + timedelta(weeks=2), phase_idx
                )
                tasks.append(milestone_task)
                task_counter += 1
            
            return tasks
            
        except Exception as e:
            logger.error(f"Error decomposing into tasks: {e}")
            return self._create_fallback_tasks(user_profile, job_role)
    
    def _create_tasks_for_objective(self, objective: str, phase_name: str, start_counter: int,
                                  phase_start_date: datetime, user_profile: Dict[str, Any],
                                  job_role: str) -> List[TaskStep]:
        """Create specific tasks for a given objective."""
        
        tasks = []
        
        # Map objectives to task templates
        objective_lower = objective.lower()
        
        if "setup" in objective_lower or "installation" in objective_lower:
            tasks.extend(self._create_setup_tasks(start_counter, phase_start_date))
        elif "training" in objective_lower or "learning" in objective_lower:
            tasks.extend(self._create_training_tasks(start_counter, phase_start_date, user_profile, job_role))
        elif "meeting" in objective_lower or "introduction" in objective_lower:
            tasks.extend(self._create_meeting_tasks(start_counter, phase_start_date))
        elif "documentation" in objective_lower or "review" in objective_lower:
            tasks.extend(self._create_documentation_tasks(start_counter, phase_start_date, job_role))
        elif "project" in objective_lower or "contribution" in objective_lower:
            tasks.extend(self._create_project_tasks(start_counter, phase_start_date, user_profile))
        else:
            # Generic task for unrecognized objectives
            tasks.append(self._create_generic_task(objective, start_counter, phase_start_date))
        
        return tasks
    
    def _create_setup_tasks(self, start_counter: int, start_date: datetime) -> List[TaskStep]:
        """Create setup-related tasks."""
        return [
            TaskStep(
                step_id=f"task_{start_counter:03d}",
                title="Complete Workspace Setup",
                description="Set up your physical workspace, equipment, and basic tools",
                priority=TaskPriority.HIGH,
                estimated_duration=120,
                assigned_tools=["slack_tool"],
                completion_criteria=["Workspace fully functional", "Equipment tested and working"],
                deadline=start_date + timedelta(days=1)
            ),
            TaskStep(
                step_id=f"task_{start_counter+1:03d}",
                title="IT Systems Access Setup",
                description="Configure access to company systems, VPN, and security tools",
                priority=TaskPriority.HIGH,
                estimated_duration=90,
                assigned_tools=["slack_tool"],
                completion_criteria=["All systems accessible", "Security protocols configured"],
                deadline=start_date + timedelta(days=2)
            )
        ]
    
    def _create_training_tasks(self, start_counter: int, start_date: datetime,
                             user_profile: Dict[str, Any], job_role: str) -> List[TaskStep]:
        """Create training-related tasks."""
        tasks = [
            TaskStep(
                step_id=f"task_{start_counter:03d}",
                title=f"Complete {job_role} Fundamentals Training",
                description=f"Essential training modules for {job_role} role",
                priority=TaskPriority.MEDIUM,
                estimated_duration=240,
                assigned_tools=["document_tool"],
                completion_criteria=["Training modules completed", "Knowledge check passed"],
                deadline=start_date + timedelta(days=7)
            )
        ]
        
        # Add technical training if needed
        skills = user_profile.get("skills", [])
        if len(skills) < 3:  # Needs additional technical training
            tasks.append(
                TaskStep(
                    step_id=f"task_{start_counter+1:03d}",
                    title="Technical Skills Development",
                    description="Complete technical skills training relevant to your role",
                    priority=TaskPriority.MEDIUM,
                    estimated_duration=360,
                    assigned_tools=["document_tool"],
                    completion_criteria=["Technical assessment passed", "Skills demonstrated"],
                    deadline=start_date + timedelta(days=14)
                )
            )
        
        return tasks
    
    def _create_meeting_tasks(self, start_counter: int, start_date: datetime) -> List[TaskStep]:
        """Create meeting and introduction tasks."""
        return [
            TaskStep(
                step_id=f"task_{start_counter:03d}",
                title="Schedule Team Introduction Meetings",
                description="Set up meetings with key team members and stakeholders",
                priority=TaskPriority.MEDIUM,
                estimated_duration=60,
                assigned_tools=["calendar_tool", "slack_tool"],
                completion_criteria=["All meetings scheduled", "Calendar invites sent"],
                deadline=start_date + timedelta(days=3)
            ),
            TaskStep(
                step_id=f"task_{start_counter+1:03d}",
                title="Complete Team Introduction Sessions",
                description="Attend scheduled meetings and get to know your team",
                priority=TaskPriority.MEDIUM,
                estimated_duration=180,
                assigned_tools=["calendar_tool"],
                completion_criteria=["All meetings attended", "Team contacts established"],
                deadline=start_date + timedelta(days=7),
                dependencies=[f"task_{start_counter:03d}"]
            )
        ]
    
    def _create_documentation_tasks(self, start_counter: int, start_date: datetime, job_role: str) -> List[TaskStep]:
        """Create documentation review tasks."""
        return [
            TaskStep(
                step_id=f"task_{start_counter:03d}",
                title="Review Company Documentation",
                description="Read and understand key company documents and policies",
                priority=TaskPriority.LOW,
                estimated_duration=180,
                assigned_tools=["document_tool"],
                completion_criteria=["Key documents reviewed", "Policy understanding confirmed"],
                deadline=start_date + timedelta(days=5)
            ),
            TaskStep(
                step_id=f"task_{start_counter+1:03d}",
                title=f"Study {job_role} Specific Documentation",
                description=f"Review role-specific guides, processes, and best practices",
                priority=TaskPriority.MEDIUM,
                estimated_duration=240,
                assigned_tools=["document_tool"],
                completion_criteria=["Role documentation mastered", "Processes understood"],
                deadline=start_date + timedelta(days=10)
            )
        ]
    
    def _create_project_tasks(self, start_counter: int, start_date: datetime,
                            user_profile: Dict[str, Any]) -> List[TaskStep]:
        """Create project-related tasks."""
        experience_years = user_profile.get("experience_years", 0)
        
        if experience_years >= 3:
            # Experienced hire - quicker project involvement
            return [
                TaskStep(
                    step_id=f"task_{start_counter:03d}",
                    title="Project Assignment and Planning",
                    description="Receive project assignment and create execution plan",
                    priority=TaskPriority.HIGH,
                    estimated_duration=120,
                    assigned_tools=["github_tool", "calendar_tool"],
                    completion_criteria=["Project scope understood", "Plan approved"],
                    deadline=start_date + timedelta(days=3)
                ),
                TaskStep(
                    step_id=f"task_{start_counter+1:03d}",
                    title="First Project Contribution",
                    description="Complete first meaningful contribution to assigned project",
                    priority=TaskPriority.HIGH,
                    estimated_duration=480,
                    assigned_tools=["github_tool", "slack_tool"],
                    completion_criteria=["Contribution completed", "Code reviewed and merged"],
                    deadline=start_date + timedelta(days=14),
                    dependencies=[f"task_{start_counter:03d}"]
                )
            ]
        else:
            # Less experienced - more gradual introduction
            return [
                TaskStep(
                    step_id=f"task_{start_counter:03d}",
                    title="Shadow Project Work",
                    description="Observe and learn from ongoing project activities",
                    priority=TaskPriority.MEDIUM,
                    estimated_duration=240,
                    assigned_tools=["github_tool"],
                    completion_criteria=["Project processes understood", "Shadowing completed"],
                    deadline=start_date + timedelta(days=7)
                ),
                TaskStep(
                    step_id=f"task_{start_counter+1:03d}",
                    title="First Small Task Assignment",
                    description="Complete a small, well-defined task with guidance",
                    priority=TaskPriority.MEDIUM,
                    estimated_duration=360,
                    assigned_tools=["github_tool", "slack_tool"],
                    completion_criteria=["Task completed successfully", "Feedback incorporated"],
                    deadline=start_date + timedelta(days=21),
                    dependencies=[f"task_{start_counter:03d}"]
                )
            ]
    
    def _create_generic_task(self, objective: str, counter: int, start_date: datetime) -> TaskStep:
        """Create a generic task for unrecognized objectives."""
        return TaskStep(
            step_id=f"task_{counter:03d}",
            title=objective[:50] + ("..." if len(objective) > 50 else ""),
            description=f"Complete objective: {objective}",
            priority=TaskPriority.MEDIUM,
            estimated_duration=120,
            assigned_tools=["slack_tool"],
            completion_criteria=["Objective completed", "Progress confirmed"],
            deadline=start_date + timedelta(days=7)
        )
    
    def _create_milestone_task(self, phase_name: str, counter: int, deadline: datetime, phase_idx: int) -> TaskStep:
        """Create a milestone task for phase completion."""
        return TaskStep(
            step_id=f"milestone_{counter:03d}",
            title=f"{phase_name} Completion Review",
            description=f"Review and confirm completion of all {phase_name} objectives",
            priority=TaskPriority.HIGH,
            estimated_duration=60,
            assigned_tools=["calendar_tool", "slack_tool"],
            completion_criteria=[f"{phase_name} objectives met", "Milestone review completed"],
            deadline=deadline,
            approval_required=True
        )
    
    def _optimize_task_scheduling(self, tasks: List[TaskStep]) -> List[TaskStep]:
        """Optimize task scheduling considering dependencies and resource constraints."""
        try:
            # Sort tasks by priority and dependencies
            optimized_tasks = []
            remaining_tasks = tasks.copy()
            
            while remaining_tasks:
                # Find tasks with no unmet dependencies
                ready_tasks = []
                for task in remaining_tasks:
                    dependencies = task.dependencies
                    if not dependencies or all(
                        any(completed.step_id == dep for completed in optimized_tasks)
                        for dep in dependencies
                    ):
                        ready_tasks.append(task)
                
                if not ready_tasks:
                    # Handle circular dependencies by taking the highest priority task
                    ready_tasks = [max(remaining_tasks, key=lambda t: self._get_priority_weight(t.priority))]
                
                # Sort ready tasks by priority and complexity
                ready_tasks.sort(key=lambda t: (
                    -self._get_priority_weight(t.priority),
                    -self._calculate_task_complexity(t)
                ))
                
                # Add the highest priority task to optimized list
                selected_task = ready_tasks[0]
                optimized_tasks.append(selected_task)
                remaining_tasks.remove(selected_task)
            
            # Adjust deadlines based on dependencies
            self._adjust_deadlines_for_dependencies(optimized_tasks)
            
            return optimized_tasks
            
        except Exception as e:
            logger.error(f"Error optimizing task scheduling: {e}")
            return tasks  # Return original tasks if optimization fails
    
    def _get_priority_weight(self, priority: TaskPriority) -> int:
        """Convert priority to numerical weight."""
        weights = {
            TaskPriority.CRITICAL: 4,
            TaskPriority.HIGH: 3,
            TaskPriority.MEDIUM: 2,
            TaskPriority.LOW: 1
        }
        return weights.get(priority, 2)
    
    def _calculate_task_complexity(self, task: TaskStep) -> float:
        """Calculate task complexity score."""
        base_complexity = task.estimated_duration / 60  # Base on duration
        
        # Apply complexity factors
        if task.approval_required:
            base_complexity *= self.complexity_factors["requires_approval"]
        
        if len(task.assigned_tools) > 2:
            base_complexity *= self.complexity_factors["involves_multiple_stakeholders"]
        
        if any(tool in task.assigned_tools for tool in ["github_tool", "calendar_tool"]):
            base_complexity *= self.complexity_factors["technical_setup"]
        
        if "training" in task.title.lower() or "documentation" in task.title.lower():
            base_complexity *= self.complexity_factors["documentation_heavy"]
        
        return base_complexity
    
    def _adjust_deadlines_for_dependencies(self, tasks: List[TaskStep]) -> None:
        """Adjust deadlines to respect task dependencies."""
        task_dict = {task.step_id: task for task in tasks}
        
        for task in tasks:
            if task.dependencies:
                # Find the latest deadline among dependencies
                dep_deadlines = []
                for dep_id in task.dependencies:
                    if dep_id in task_dict:
                        dep_deadlines.append(task_dict[dep_id].deadline)
                
                if dep_deadlines:
                    latest_dep_deadline = max(dep_deadlines)
                    # Ensure current task deadline is after dependency deadlines
                    if task.deadline <= latest_dep_deadline:
                        task.deadline = latest_dep_deadline + timedelta(days=1)
    
    def _create_onboarding_plan(self, tasks: List[TaskStep], user_profile: Dict[str, Any],
                              job_role: str, planning_approach: Dict[str, Any]) -> OnboardingPlan:
        """Create the final OnboardingPlan object."""
        
        plan_id = str(uuid.uuid4())
        user_id = user_profile.get("user_id", str(uuid.uuid4()))
        
        # Calculate timeline
        start_date = datetime.now()
        if tasks:
            expected_completion = max(task.deadline for task in tasks)
        else:
            duration_weeks = planning_approach.get("config", {}).get("duration_weeks", 8)
            expected_completion = start_date + timedelta(weeks=duration_weeks)
        
        return OnboardingPlan(
            plan_id=plan_id,
            user_id=user_id,
            job_role=job_role,
            start_date=start_date,
            expected_completion=expected_completion,
            steps=tasks,
            created_by_llm=LLMProvider.GEMINI  # Planning typically uses Gemini
        )
    
    def _assign_tools_to_tasks(self, tasks: List[TaskStep]) -> Dict[str, List[str]]:
        """Create tool assignment mapping."""
        tool_assignments = {}
        
        for task in tasks:
            for tool in task.assigned_tools:
                if tool not in tool_assignments:
                    tool_assignments[tool] = []
                tool_assignments[tool].append(task.step_id)
        
        return tool_assignments
    
    def _calculate_plan_complexity(self, tasks: List[TaskStep]) -> str:
        """Calculate overall plan complexity."""
        total_complexity = sum(self._calculate_task_complexity(task) for task in tasks)
        avg_complexity = total_complexity / len(tasks) if tasks else 0
        
        if avg_complexity > 3:
            return "high"
        elif avg_complexity > 2:
            return "medium"
        else:
            return "low"
    
    def _analyze_progress(self, current_plan: List[Dict], completed_tasks: List[str],
                         current_step: Optional[str]) -> Dict[str, Any]:
        """Analyze current progress against the plan."""
        total_tasks = len(current_plan)
        completed_count = len(completed_tasks)
        completion_rate = completed_count / total_tasks if total_tasks > 0 else 0
        
        # Find current task details
        current_task = None
        if current_step:
            current_task = next((task for task in current_plan if task.get("step_id") == current_step), None)
        
        # Calculate if on track
        if current_task and current_task.get("deadline"):
            deadline = datetime.fromisoformat(current_task["deadline"])
            is_on_track = datetime.now() <= deadline
        else:
            is_on_track = True
        
        return {
            "completion_rate": completion_rate,
            "completed_count": completed_count,
            "total_tasks": total_tasks,
            "current_task": current_task,
            "is_on_track": is_on_track,
            "analysis_timestamp": datetime.now().isoformat()
        }
    
    async def _identify_adjustment_needs(self, progress_analysis: Dict[str, Any],
                                       contextual_memory: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
        """Identify what adjustments are needed to the plan."""
        adjustments = []
        requires_reoptimization = False
        impact = "minimal"
        
        completion_rate = progress_analysis.get("completion_rate", 0)
        is_on_track = progress_analysis.get("is_on_track", True)
        
        # Check if behind schedule
        if completion_rate < 0.3 and not is_on_track:
            adjustments.append("extend_deadlines")
            adjustments.append("simplify_tasks")
            requires_reoptimization = True
            impact = "moderate"
        
        # Check if ahead of schedule
        elif completion_rate > 0.8 and is_on_track:
            adjustments.append("add_advanced_tasks")
            adjustments.append("accelerate_timeline")
            impact = "positive"
        
        # Check for errors or blockers
        errors = state.get("errors", [])
        if errors:
            adjustments.append("address_blockers")
            adjustments.append("add_support_tasks")
            requires_reoptimization = True
            impact = "moderate"
        
        # Check for feedback patterns
        adjustment_count = contextual_memory.get("adjustment_count", 0)
        if adjustment_count > 2:
            adjustments.append("stabilize_plan")
            impact = "stabilizing"
        
        return {
            "adjustments": adjustments,
            "requires_reoptimization": requires_reoptimization,
            "impact": impact,
            "reason": f"Progress analysis: {completion_rate:.1%} complete, on track: {is_on_track}"
        }
    
    def _apply_plan_adjustments(self, current_plan: List[Dict], adjustment_needs: Dict[str, Any],
                              progress_analysis: Dict[str, Any]) -> List[TaskStep]:
        """Apply identified adjustments to the plan."""
        adjustments = adjustment_needs.get("adjustments", [])
        
        # Convert current plan to TaskStep objects if needed
        tasks = []
        for task_data in current_plan:
            if isinstance(task_data, dict):
                # Convert dict to TaskStep
                task = TaskStep(**task_data)
                tasks.append(task)
            else:
                tasks.append(task_data)
        
        # Apply adjustments
        if "extend_deadlines" in adjustments:
            for task in tasks:
                if task.status == TaskStatus.PENDING:
                    task.deadline = task.deadline + timedelta(days=3)
        
        if "simplify_tasks" in adjustments:
            for task in tasks:
                if task.status == TaskStatus.PENDING and task.estimated_duration > 240:
                    task.estimated_duration = min(task.estimated_duration, 180)
                    task.description = f"Simplified: {task.description}"
        
        if "add_advanced_tasks" in adjustments:
            # Add one additional advanced task
            advanced_task = TaskStep(
                step_id=f"advanced_{len(tasks)+1:03d}",
                title="Advanced Integration Challenge",
                description="Take on additional responsibilities and advanced projects",
                priority=TaskPriority.LOW,
                estimated_duration=240,
                assigned_tools=["github_tool", "slack_tool"],
                completion_criteria=["Advanced task completed", "Skills demonstrated"],
                deadline=datetime.now() + timedelta(weeks=2)
            )
            tasks.append(advanced_task)
        
        if "accelerate_timeline" in adjustments:
            for task in tasks:
                if task.status == TaskStatus.PENDING:
                    task.deadline = task.deadline - timedelta(days=2)
        
        return tasks
    
    def _create_fallback_tasks(self, user_profile: Dict[str, Any], job_role: str) -> List[TaskStep]:
        """Create basic fallback tasks when detailed planning fails."""
        base_date = datetime.now()
        
        return [
            TaskStep(
                step_id="task_001",
                title="Complete Initial Setup",
                description="Set up workspace and basic access",
                priority=TaskPriority.HIGH,
                estimated_duration=120,
                assigned_tools=["slack_tool"],
                completion_criteria=["Setup completed"],
                deadline=base_date + timedelta(days=1)
            ),
            TaskStep(
                step_id="task_002",
                title="Team Introductions",
                description="Meet your team and key stakeholders",
                priority=TaskPriority.MEDIUM,
                estimated_duration=180,
                assigned_tools=["calendar_tool", "slack_tool"],
                completion_criteria=["Team meetings completed"],
                deadline=base_date + timedelta(days=7)
            ),
            TaskStep(
                step_id="task_003",
                title="Role Training",
                description=f"Complete training for {job_role} role",
                priority=TaskPriority.MEDIUM,
                estimated_duration=240,
                assigned_tools=["document_tool"],
                completion_criteria=["Training completed"],
                deadline=base_date + timedelta(days=14)
            )
        ]