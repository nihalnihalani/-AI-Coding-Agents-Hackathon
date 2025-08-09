from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from fastapi.responses import JSONResponse
import logging
from typing import Dict, Any, Optional, List
import uuid
from datetime import datetime

from ..agents.aura_agent import AuraAgent
from ..services.document_service import DocumentService
from ..tools.registry import tool_registry
from ..models.schemas import (
    ResumeUploadRequest, ResumeUploadResponse, 
    ProgressUpdateRequest, ProgressUpdateResponse,
    OnboardingPlan, TaskStep, UserProfile
)
from ..core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/onboarding", tags=["onboarding"])

# In-memory storage for demo (would use Redis/database in production)
active_agents = {}
document_service = DocumentService()

@router.post("/upload-resume", response_model=ResumeUploadResponse)
async def upload_resume(
    file: UploadFile = File(...),
    job_role: str = Form(...),
    department: Optional[str] = Form(None),
    additional_context: Optional[str] = Form(None)
):
    """Upload and process resume to create personalized onboarding plan."""
    try:
        # Validate file type
        if not file.filename.lower().endswith(('.pdf', '.doc', '.docx', '.txt')):
            raise HTTPException(
                status_code=400, 
                detail="Unsupported file type. Please upload PDF, DOC, DOCX, or TXT files."
            )
        
        # Read file content
        file_content = await file.read()
        if len(file_content) == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")
        
        logger.info(f"Processing resume upload: {file.filename}, role: {job_role}")
        
        # Process resume through document service
        user_profile, doc_analysis = await document_service.process_resume(
            file_content, file.filename, job_role
        )
        
        # Create or get agent for this user
        session_id = str(uuid.uuid4())
        agent = AuraAgent()
        
        # Process resume through agent to create onboarding plan
        initial_input = f"I've uploaded my resume for the {job_role} position."
        if additional_context:
            initial_input += f" Additional context: {additional_context}"
        
        # Update agent state with resume data
        agent.update_state({
            "user_profile": user_profile.dict(),
            "resume_data": doc_analysis.dict(),
            "job_role": job_role,
            "department": department,
            "session_id": session_id
        })
        
        # Process input to generate onboarding plan
        result = await agent.process_input(initial_input, session_id)
        
        # Store agent for future interactions
        active_agents[session_id] = agent
        
        # Extract onboarding plan from result
        onboarding_steps = result.get("onboarding_plan_steps", [])
        if onboarding_steps:
            # Convert to OnboardingPlan object
            plan = OnboardingPlan(
                plan_id=str(uuid.uuid4()),
                user_id=user_profile.user_id,
                job_role=job_role,
                department=department,
                steps=[TaskStep(**step) if isinstance(step, dict) else step for step in onboarding_steps],
                start_date=datetime.now()
            )
        else:
            # Create a basic plan if none generated
            plan = OnboardingPlan(
                plan_id=str(uuid.uuid4()),
                user_id=user_profile.user_id,
                job_role=job_role,
                department=department,
                steps=[],
                start_date=datetime.now()
            )
        
        response = ResumeUploadResponse(
            document_id=doc_analysis.document_id,
            user_profile=user_profile,
            onboarding_plan=plan,
            analysis=doc_analysis,
            message="Resume processed successfully! Your personalized onboarding plan has been created."
        )
        
        logger.info(f"Resume processed successfully for session {session_id}")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing resume upload: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process resume: {str(e)}")

@router.get("/plan/{session_id}")
async def get_onboarding_plan(session_id: str):
    """Retrieve current onboarding plan for a session."""
    try:
        if session_id not in active_agents:
            raise HTTPException(status_code=404, detail="Session not found")
        
        agent = active_agents[session_id]
        state = agent.get_state()
        
        # Extract plan information
        plan_steps = state.get("onboarding_plan_steps", [])
        completed_tasks = state.get("completed_tasks", [])
        current_step = state.get("current_step")
        user_profile = state.get("user_profile", {})
        
        # Calculate progress
        total_tasks = len(plan_steps)
        completed_count = len(completed_tasks)
        progress_percentage = (completed_count / total_tasks * 100) if total_tasks > 0 else 0
        
        return {
            "success": True,
            "data": {
                "session_id": session_id,
                "user_profile": user_profile,
                "plan_steps": plan_steps,
                "current_step": current_step,
                "progress": {
                    "total_tasks": total_tasks,
                    "completed_tasks": completed_count,
                    "percentage": round(progress_percentage, 1),
                    "remaining_tasks": total_tasks - completed_count
                },
                "completed_task_ids": completed_tasks,
                "job_role": state.get("job_role"),
                "department": state.get("department")
            },
            "message": f"Retrieved onboarding plan with {total_tasks} tasks ({completed_count} completed)"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving onboarding plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/update-progress", response_model=ProgressUpdateResponse)
async def update_task_progress(request: ProgressUpdateRequest, session_id: str):
    """Update progress on a specific onboarding task."""
    try:
        if session_id not in active_agents:
            raise HTTPException(status_code=404, detail="Session not found")
        
        agent = active_agents[session_id]
        state = agent.get_state()
        
        # Find the task to update
        plan_steps = state.get("onboarding_plan_steps", [])
        task_to_update = None
        
        for step in plan_steps:
            if step.get("step_id") == request.step_id:
                task_to_update = step
                break
        
        if not task_to_update:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Update task status
        old_status = task_to_update.get("status")
        task_to_update["status"] = request.status.value
        
        if request.notes:
            task_to_update["notes"] = request.notes
        
        if request.completion_evidence:
            task_to_update["completion_evidence"] = request.completion_evidence
        
        # If task is being marked as completed, add to completed tasks
        if request.status.value == "completed" and request.step_id not in state.get("completed_tasks", []):
            completed_tasks = state.get("completed_tasks", [])
            completed_tasks.append(request.step_id)
            agent.update_state({"completed_tasks": completed_tasks})
            
            # Update current step to next pending task
            next_pending = None
            for step in plan_steps:
                if step.get("status") == "pending":
                    next_pending = step.get("step_id")
                    break
            
            agent.update_state({"current_step": next_pending})
        
        # Update the plan steps in agent state
        agent.update_state({"onboarding_plan_steps": plan_steps})
        
        # Process through agent for any follow-up actions
        progress_message = f"I've marked the task '{task_to_update.get('title', 'Task')}' as {request.status.value}."
        if request.notes:
            progress_message += f" Notes: {request.notes}"
        
        await agent.process_input(progress_message, session_id)
        
        # Create updated plan object
        updated_state = agent.get_state()
        updated_plan = OnboardingPlan(
            plan_id=str(uuid.uuid4()),
            user_id=updated_state.get("user_profile", {}).get("user_id", "unknown"),
            job_role=updated_state.get("job_role", "Unknown"),
            steps=[TaskStep(**step) if isinstance(step, dict) else step 
                   for step in updated_state.get("onboarding_plan_steps", [])],
            start_date=datetime.now()
        )
        
        # Determine next recommended step
        next_step = None
        for step in plan_steps:
            if step.get("status") in ["pending", "in_progress"]:
                next_step = step.get("step_id")
                break
        
        response = ProgressUpdateResponse(
            step_id=request.step_id,
            updated_status=request.status,
            updated_plan=updated_plan,
            message=f"Task progress updated successfully. Status changed from {old_status} to {request.status.value}.",
            next_recommended_step=next_step
        )
        
        logger.info(f"Updated task {request.step_id} status to {request.status.value} for session {session_id}")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating task progress: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/agent-state/{session_id}")
async def get_agent_state(session_id: str):
    """Get current agent state for UI updates."""
    try:
        if session_id not in active_agents:
            raise HTTPException(status_code=404, detail="Session not found")
        
        agent = active_agents[session_id]
        state = agent.get_state()
        
        # Calculate additional metrics
        plan_steps = state.get("onboarding_plan_steps", [])
        completed_tasks = state.get("completed_tasks", [])
        
        # Task status breakdown
        status_counts = {"pending": 0, "in_progress": 0, "completed": 0, "blocked": 0}
        for step in plan_steps:
            status = step.get("status", "pending")
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Upcoming deadlines
        upcoming_deadlines = []
        for step in plan_steps:
            if step.get("deadline") and step.get("status") not in ["completed"]:
                upcoming_deadlines.append({
                    "step_id": step.get("step_id"),
                    "title": step.get("title"),
                    "deadline": step.get("deadline"),
                    "priority": step.get("priority")
                })
        
        # Sort by deadline
        upcoming_deadlines.sort(key=lambda x: x["deadline"])
        
        return {
            "success": True,
            "data": {
                "session_id": session_id,
                "agent_state": {
                    "current_user_intent": state.get("current_user_intent"),
                    "current_step": state.get("current_step"),
                    "active_llm": state.get("active_llm"),
                    "last_updated": state.get("last_updated")
                },
                "conversation_summary": {
                    "total_messages": len(state.get("conversation_history", [])),
                    "last_interaction": state.get("conversation_history", [])[-1] if state.get("conversation_history") else None
                },
                "progress_metrics": {
                    "status_breakdown": status_counts,
                    "completion_rate": len(completed_tasks) / len(plan_steps) * 100 if plan_steps else 0,
                    "total_tasks": len(plan_steps),
                    "completed_tasks": len(completed_tasks)
                },
                "upcoming_deadlines": upcoming_deadlines[:5],  # Next 5 deadlines
                "tool_activity": state.get("tool_states", {}),
                "pending_approvals": len(state.get("pending_approvals", [])),
                "errors": state.get("errors", [])
            },
            "message": "Agent state retrieved successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting agent state: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/regenerate-plan/{session_id}")
async def regenerate_onboarding_plan(session_id: str, preferences: Optional[Dict[str, Any]] = None):
    """Regenerate onboarding plan with new preferences or after significant changes."""
    try:
        if session_id not in active_agents:
            raise HTTPException(status_code=404, detail="Session not found")
        
        agent = active_agents[session_id]
        state = agent.get_state()
        
        # Build regeneration request
        regeneration_request = "Please regenerate my onboarding plan"
        if preferences:
            if preferences.get("focus_areas"):
                regeneration_request += f" with focus on: {', '.join(preferences['focus_areas'])}"
            if preferences.get("timeline_preference"):
                regeneration_request += f" with {preferences['timeline_preference']} timeline"
            if preferences.get("learning_style"):
                regeneration_request += f" optimized for {preferences['learning_style']} learning style"
        
        # Process through agent
        result = await agent.process_input(regeneration_request, session_id)
        
        # Get updated plan
        updated_steps = result.get("onboarding_plan_steps", [])
        
        return {
            "success": True,
            "data": {
                "session_id": session_id,
                "regenerated_plan": updated_steps,
                "total_tasks": len(updated_steps),
                "preferences_applied": preferences or {},
                "message": "Onboarding plan regenerated successfully"
            },
            "message": f"Plan regenerated with {len(updated_steps)} tasks based on your preferences"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error regenerating plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tasks/{session_id}")
async def get_tasks_by_status(session_id: str, status: Optional[str] = None, priority: Optional[str] = None):
    """Get tasks filtered by status and/or priority."""
    try:
        if session_id not in active_agents:
            raise HTTPException(status_code=404, detail="Session not found")
        
        agent = active_agents[session_id]
        state = agent.get_state()
        plan_steps = state.get("onboarding_plan_steps", [])
        
        # Filter tasks
        filtered_tasks = plan_steps
        
        if status:
            filtered_tasks = [task for task in filtered_tasks if task.get("status") == status]
        
        if priority:
            filtered_tasks = [task for task in filtered_tasks if task.get("priority") == priority]
        
        # Sort by priority and deadline
        priority_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        filtered_tasks.sort(key=lambda x: (
            -priority_order.get(x.get("priority", "medium"), 2),
            x.get("deadline", "2099-12-31")
        ))
        
        return {
            "success": True,
            "data": {
                "session_id": session_id,
                "tasks": filtered_tasks,
                "total_count": len(filtered_tasks),
                "filters_applied": {
                    "status": status,
                    "priority": priority
                }
            },
            "message": f"Retrieved {len(filtered_tasks)} tasks matching filters"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting filtered tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/execute-tool/{session_id}")
async def execute_tool_action(session_id: str, tool_name: str, action: str, parameters: Dict[str, Any]):
    """Execute a tool action for the onboarding process."""
    try:
        if session_id not in active_agents:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Execute tool through registry
        result = await tool_registry.execute_tool(tool_name, action, parameters)
        
        # Update agent state with tool result
        agent = active_agents[session_id]
        tool_message = f"Executed {tool_name}.{action}"
        if result.success:
            tool_message += f" successfully. {result.data.get('message', '')}"
        else:
            tool_message += f" with error: {result.error}"
        
        # Process through agent
        await agent.process_input(tool_message, session_id)
        
        return {
            "success": result.success,
            "data": {
                "tool_name": tool_name,
                "action": action,
                "result": result.to_dict(),
                "execution_time": result.execution_time
            },
            "message": f"Tool action {'completed' if result.success else 'failed'}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing tool action: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/available-tools")
async def get_available_tools():
    """Get list of available tools and their capabilities."""
    try:
        tools_summary = tool_registry.get_registry_summary()
        health_check = await tool_registry.health_check()
        
        return {
            "success": True,
            "data": {
                "registry_summary": tools_summary,
                "health_status": health_check,
                "tool_categories": tool_registry.get_categories(),
                "available_tools": tool_registry.get_available_tools()
            },
            "message": f"Retrieved {tools_summary['total_tools']} available tools"
        }
        
    except Exception as e:
        logger.error(f"Error getting available tools: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/session/{session_id}")
async def end_onboarding_session(session_id: str):
    """End an onboarding session and clean up resources."""
    try:
        if session_id not in active_agents:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get final state for archival
        agent = active_agents[session_id]
        final_state = agent.get_state()
        
        # Archive session data (in production, save to database)
        session_summary = {
            "session_id": session_id,
            "end_time": datetime.now().isoformat(),
            "total_tasks": len(final_state.get("onboarding_plan_steps", [])),
            "completed_tasks": len(final_state.get("completed_tasks", [])),
            "total_interactions": len(final_state.get("conversation_history", [])),
            "job_role": final_state.get("job_role"),
            "user_id": final_state.get("user_profile", {}).get("user_id")
        }
        
        # Remove from active sessions
        del active_agents[session_id]
        
        logger.info(f"Ended onboarding session {session_id}")
        
        return {
            "success": True,
            "data": session_summary,
            "message": f"Onboarding session {session_id} ended successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ending session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sessions")
async def get_active_sessions():
    """Get list of all active onboarding sessions."""
    try:
        sessions_info = []
        
        for session_id, agent in active_agents.items():
            state = agent.get_state()
            sessions_info.append({
                "session_id": session_id,
                "job_role": state.get("job_role"),
                "user_name": state.get("user_profile", {}).get("name"),
                "total_tasks": len(state.get("onboarding_plan_steps", [])),
                "completed_tasks": len(state.get("completed_tasks", [])),
                "current_step": state.get("current_step"),
                "last_activity": state.get("last_updated"),
                "active_llm": state.get("active_llm")
            })
        
        return {
            "success": True,
            "data": {
                "total_sessions": len(sessions_info),
                "sessions": sessions_info
            },
            "message": f"Retrieved {len(sessions_info)} active onboarding sessions"
        }
        
    except Exception as e:
        logger.error(f"Error getting active sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))