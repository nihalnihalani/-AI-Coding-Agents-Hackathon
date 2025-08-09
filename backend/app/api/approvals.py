from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import uuid

from ..models.schemas import ApprovalRequest
from ..core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/approvals", tags=["approvals"])

# In-memory storage for approval requests (would use database in production)
pending_approvals = {}
approval_history = {}

# Approval configuration
APPROVAL_SETTINGS = {
    "default_expiry_hours": 24,
    "high_risk_expiry_hours": 4,
    "auto_approve_low_risk": True,
    "require_reason_for_rejection": True,
    "escalation_hours": 8
}

@router.get("/pending")
async def get_pending_approvals(user_id: Optional[str] = None, risk_level: Optional[str] = None):
    """Get pending approval requests, optionally filtered by user or risk level."""
    try:
        filtered_approvals = []
        
        for approval_id, approval in pending_approvals.items():
            # Skip expired approvals
            if approval.expires_at and datetime.fromisoformat(approval.expires_at) < datetime.now():
                continue
            
            # Apply filters
            if user_id and approval.session_id != user_id:
                continue
            
            if risk_level and approval.risk_level != risk_level:
                continue
            
            # Convert to dict and add calculated fields
            approval_dict = approval.dict()
            approval_dict["time_remaining"] = _calculate_time_remaining(approval.expires_at)
            approval_dict["is_escalated"] = _is_escalated(approval.created_at)
            
            filtered_approvals.append(approval_dict)
        
        # Sort by priority (risk level and creation time)
        risk_priority = {"high": 3, "medium": 2, "low": 1}
        filtered_approvals.sort(key=lambda x: (
            -risk_priority.get(x["risk_level"], 2),
            x["created_at"]
        ))
        
        return {
            "success": True,
            "data": {
                "approvals": filtered_approvals,
                "total_count": len(filtered_approvals),
                "filters_applied": {
                    "user_id": user_id,
                    "risk_level": risk_level
                },
                "summary": {
                    "high_risk": len([a for a in filtered_approvals if a["risk_level"] == "high"]),
                    "medium_risk": len([a for a in filtered_approvals if a["risk_level"] == "medium"]),
                    "low_risk": len([a for a in filtered_approvals if a["risk_level"] == "low"]),
                    "escalated": len([a for a in filtered_approvals if a["is_escalated"]])
                }
            },
            "message": f"Retrieved {len(filtered_approvals)} pending approval requests"
        }
        
    except Exception as e:
        logger.error(f"Error getting pending approvals: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/request")
async def create_approval_request(
    session_id: str,
    action_type: str,
    action_description: str,
    action_details: Dict[str, Any],
    risk_level: str = "medium",
    requester: str = "aura_agent"
):
    """Create a new approval request."""
    try:
        # Validate risk level
        if risk_level not in ["low", "medium", "high"]:
            raise HTTPException(status_code=400, detail="Risk level must be 'low', 'medium', or 'high'")
        
        # Check if auto-approval applies
        if risk_level == "low" and APPROVAL_SETTINGS["auto_approve_low_risk"]:
            # Auto-approve low-risk actions
            logger.info(f"Auto-approving low-risk action: {action_type}")
            return {
                "success": True,
                "data": {
                    "auto_approved": True,
                    "action_type": action_type,
                    "risk_level": risk_level,
                    "approved_at": datetime.now().isoformat()
                },
                "message": "Low-risk action auto-approved"
            }
        
        # Create approval request
        request_id = str(uuid.uuid4())
        
        # Calculate expiry time
        expiry_hours = APPROVAL_SETTINGS["high_risk_expiry_hours"] if risk_level == "high" else APPROVAL_SETTINGS["default_expiry_hours"]
        expires_at = datetime.now() + timedelta(hours=expiry_hours)
        
        approval_request = ApprovalRequest(
            request_id=request_id,
            session_id=session_id,
            action_type=action_type,
            action_description=action_description,
            action_details=action_details,
            risk_level=risk_level,
            requester=requester,
            expires_at=expires_at,
            created_at=datetime.now()
        )
        
        # Store the request
        pending_approvals[request_id] = approval_request
        
        logger.info(f"Created approval request {request_id} for {action_type} (risk: {risk_level})")
        
        # Send notifications if high risk
        if risk_level == "high":
            await _send_urgent_approval_notification(approval_request)
        
        return {
            "success": True,
            "data": {
                "request_id": request_id,
                "action_type": action_type,
                "risk_level": risk_level,
                "expires_at": expires_at.isoformat(),
                "status": "pending",
                "estimated_response_time": f"{expiry_hours} hours"
            },
            "message": f"Approval request created for {action_type}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating approval request: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/approve/{request_id}")
async def approve_request(
    request_id: str,
    approver_id: str,
    approval_reason: Optional[str] = None,
    conditions: Optional[List[str]] = None
):
    """Approve a pending request."""
    try:
        if request_id not in pending_approvals:
            raise HTTPException(status_code=404, detail="Approval request not found")
        
        approval_request = pending_approvals[request_id]
        
        # Check if already processed
        if approval_request.status != "pending":
            raise HTTPException(status_code=400, detail=f"Request already {approval_request.status}")
        
        # Check if expired
        if approval_request.expires_at and datetime.fromisoformat(approval_request.expires_at) < datetime.now():
            approval_request.status = "expired"
            raise HTTPException(status_code=400, detail="Approval request has expired")
        
        # Update approval request
        approval_request.status = "approved"
        approval_request.approved_by = approver_id
        approval_request.approval_reason = approval_reason or "Approved"
        approval_request.approved_at = datetime.now()
        
        # Add conditions if specified
        if conditions:
            approval_request.action_details["approval_conditions"] = conditions
        
        # Move to history
        approval_history[request_id] = approval_request
        del pending_approvals[request_id]
        
        logger.info(f"Approved request {request_id} by {approver_id}")
        
        # Execute the approved action
        execution_result = await _execute_approved_action(approval_request)
        
        return {
            "success": True,
            "data": {
                "request_id": request_id,
                "status": "approved",
                "approved_by": approver_id,
                "approved_at": approval_request.approved_at.isoformat(),
                "approval_reason": approval_reason,
                "conditions": conditions,
                "execution_result": execution_result
            },
            "message": f"Request {request_id} approved and executed successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving request: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reject/{request_id}")
async def reject_request(
    request_id: str,
    approver_id: str,
    rejection_reason: str,
    alternative_suggestions: Optional[List[str]] = None
):
    """Reject a pending request."""
    try:
        if request_id not in pending_approvals:
            raise HTTPException(status_code=404, detail="Approval request not found")
        
        approval_request = pending_approvals[request_id]
        
        # Check if already processed
        if approval_request.status != "pending":
            raise HTTPException(status_code=400, detail=f"Request already {approval_request.status}")
        
        # Validate rejection reason
        if not rejection_reason and APPROVAL_SETTINGS["require_reason_for_rejection"]:
            raise HTTPException(status_code=400, detail="Rejection reason is required")
        
        # Update approval request
        approval_request.status = "rejected"
        approval_request.approved_by = approver_id
        approval_request.approval_reason = f"REJECTED: {rejection_reason}"
        approval_request.approved_at = datetime.now()
        
        # Add alternative suggestions
        if alternative_suggestions:
            approval_request.action_details["alternative_suggestions"] = alternative_suggestions
        
        # Move to history
        approval_history[request_id] = approval_request
        del pending_approvals[request_id]
        
        logger.info(f"Rejected request {request_id} by {approver_id}: {rejection_reason}")
        
        # Notify the agent/user about rejection
        await _send_rejection_notification(approval_request, alternative_suggestions)
        
        return {
            "success": True,
            "data": {
                "request_id": request_id,
                "status": "rejected",
                "rejected_by": approver_id,
                "rejected_at": approval_request.approved_at.isoformat(),
                "rejection_reason": rejection_reason,
                "alternative_suggestions": alternative_suggestions
            },
            "message": f"Request {request_id} rejected"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rejecting request: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history")
async def get_approval_history(
    limit: int = 50,
    user_id: Optional[str] = None,
    action_type: Optional[str] = None,
    status: Optional[str] = None
):
    """Get approval history with optional filters."""
    try:
        filtered_history = []
        
        for approval_id, approval in approval_history.items():
            # Apply filters
            if user_id and approval.session_id != user_id:
                continue
            
            if action_type and approval.action_type != action_type:
                continue
            
            if status and approval.status != status:
                continue
            
            # Convert to dict and add calculated fields
            approval_dict = approval.dict()
            approval_dict["processing_time"] = _calculate_processing_time(approval)
            
            filtered_history.append(approval_dict)
        
        # Sort by most recent first
        filtered_history.sort(key=lambda x: x["created_at"], reverse=True)
        
        # Apply limit
        if limit:
            filtered_history = filtered_history[:limit]
        
        # Calculate statistics
        total_requests = len(filtered_history)
        approved_count = len([a for a in filtered_history if a["status"] == "approved"])
        rejected_count = len([a for a in filtered_history if a["status"] == "rejected"])
        expired_count = len([a for a in filtered_history if a["status"] == "expired"])
        
        return {
            "success": True,
            "data": {
                "approvals": filtered_history,
                "total_count": total_requests,
                "statistics": {
                    "total_requests": total_requests,
                    "approved": approved_count,
                    "rejected": rejected_count,
                    "expired": expired_count,
                    "approval_rate": (approved_count / total_requests * 100) if total_requests > 0 else 0
                },
                "filters_applied": {
                    "user_id": user_id,
                    "action_type": action_type,
                    "status": status,
                    "limit": limit
                }
            },
            "message": f"Retrieved {total_requests} approval records"
        }
        
    except Exception as e:
        logger.error(f"Error getting approval history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/request/{request_id}")
async def get_approval_request_details(request_id: str):
    """Get detailed information about a specific approval request."""
    try:
        # Check pending requests first
        if request_id in pending_approvals:
            approval = pending_approvals[request_id]
            location = "pending"
        elif request_id in approval_history:
            approval = approval_history[request_id]
            location = "history"
        else:
            raise HTTPException(status_code=404, detail="Approval request not found")
        
        # Convert to dict and add calculated fields
        approval_dict = approval.dict()
        approval_dict["location"] = location
        
        if location == "pending":
            approval_dict["time_remaining"] = _calculate_time_remaining(approval.expires_at)
            approval_dict["is_escalated"] = _is_escalated(approval.created_at)
        else:
            approval_dict["processing_time"] = _calculate_processing_time(approval)
        
        return {
            "success": True,
            "data": approval_dict,
            "message": f"Retrieved approval request details from {location}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting approval request details: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/bulk-approve")
async def bulk_approve_requests(
    request_ids: List[str],
    approver_id: str,
    approval_reason: Optional[str] = None
):
    """Approve multiple requests in bulk."""
    try:
        results = []
        
        for request_id in request_ids:
            try:
                # Use the individual approve endpoint logic
                result = await approve_request(request_id, approver_id, approval_reason)
                results.append({
                    "request_id": request_id,
                    "success": True,
                    "message": f"Approved successfully"
                })
            except HTTPException as e:
                results.append({
                    "request_id": request_id,
                    "success": False,
                    "error": e.detail
                })
            except Exception as e:
                results.append({
                    "request_id": request_id,
                    "success": False,
                    "error": str(e)
                })
        
        # Calculate success rate
        successful = len([r for r in results if r["success"]])
        total = len(results)
        
        return {
            "success": True,
            "data": {
                "results": results,
                "summary": {
                    "total_requests": total,
                    "successful_approvals": successful,
                    "failed_approvals": total - successful,
                    "success_rate": (successful / total * 100) if total > 0 else 0
                }
            },
            "message": f"Bulk approval completed: {successful}/{total} successful"
        }
        
    except Exception as e:
        logger.error(f"Error in bulk approval: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dashboard")
async def get_approval_dashboard():
    """Get approval dashboard with statistics and insights."""
    try:
        # Calculate pending statistics
        pending_stats = {
            "total": len(pending_approvals),
            "high_risk": len([a for a in pending_approvals.values() if a.risk_level == "high"]),
            "medium_risk": len([a for a in pending_approvals.values() if a.risk_level == "medium"]),
            "low_risk": len([a for a in pending_approvals.values() if a.risk_level == "low"]),
            "escalated": len([a for a in pending_approvals.values() if _is_escalated(a.created_at)]),
            "expiring_soon": len([a for a in pending_approvals.values() 
                                 if a.expires_at and datetime.fromisoformat(a.expires_at) < datetime.now() + timedelta(hours=2)])
        }
        
        # Calculate historical statistics (last 30 days)
        cutoff_date = datetime.now() - timedelta(days=30)
        recent_history = [a for a in approval_history.values() 
                         if a.created_at > cutoff_date]
        
        historical_stats = {
            "total_last_30_days": len(recent_history),
            "approved": len([a for a in recent_history if a.status == "approved"]),
            "rejected": len([a for a in recent_history if a.status == "rejected"]),
            "expired": len([a for a in recent_history if a.status == "expired"]),
            "approval_rate": (len([a for a in recent_history if a.status == "approved"]) / len(recent_history) * 100) if recent_history else 0
        }
        
        # Calculate average processing time
        processed_requests = [a for a in recent_history if a.approved_at]
        if processed_requests:
            avg_processing_time = sum(_calculate_processing_time_seconds(a) for a in processed_requests) / len(processed_requests)
            avg_processing_hours = avg_processing_time / 3600
        else:
            avg_processing_hours = 0
        
        # Action type breakdown
        action_types = {}
        for approval in list(pending_approvals.values()) + recent_history:
            action_type = approval.action_type
            if action_type not in action_types:
                action_types[action_type] = {"total": 0, "pending": 0, "approved": 0, "rejected": 0}
            
            action_types[action_type]["total"] += 1
            if approval.request_id in pending_approvals:
                action_types[action_type]["pending"] += 1
            elif approval.status == "approved":
                action_types[action_type]["approved"] += 1
            elif approval.status == "rejected":
                action_types[action_type]["rejected"] += 1
        
        return {
            "success": True,
            "data": {
                "pending_approvals": pending_stats,
                "historical_stats": historical_stats,
                "performance_metrics": {
                    "average_processing_hours": round(avg_processing_hours, 2),
                    "approval_rate_30_days": round(historical_stats["approval_rate"], 1),
                    "escalation_rate": round((pending_stats["escalated"] / pending_stats["total"] * 100) if pending_stats["total"] > 0 else 0, 1)
                },
                "action_type_breakdown": action_types,
                "alerts": _generate_approval_alerts(pending_stats, historical_stats)
            },
            "message": "Approval dashboard data retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"Error getting approval dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Helper functions

def _calculate_time_remaining(expires_at: Optional[str]) -> Optional[str]:
    """Calculate human-readable time remaining until expiry."""
    if not expires_at:
        return None
    
    try:
        expiry_time = datetime.fromisoformat(expires_at)
        remaining = expiry_time - datetime.now()
        
        if remaining.total_seconds() <= 0:
            return "Expired"
        
        hours = int(remaining.total_seconds() // 3600)
        minutes = int((remaining.total_seconds() % 3600) // 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"
    except Exception:
        return "Unknown"

def _is_escalated(created_at: datetime) -> bool:
    """Check if a request should be escalated based on age."""
    escalation_time = datetime.now() - timedelta(hours=APPROVAL_SETTINGS["escalation_hours"])
    return created_at < escalation_time

def _calculate_processing_time(approval: ApprovalRequest) -> Optional[str]:
    """Calculate human-readable processing time."""
    if not approval.approved_at:
        return None
    
    processing_seconds = _calculate_processing_time_seconds(approval)
    
    hours = int(processing_seconds // 3600)
    minutes = int((processing_seconds % 3600) // 60)
    
    if hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m"

def _calculate_processing_time_seconds(approval: ApprovalRequest) -> float:
    """Calculate processing time in seconds."""
    if not approval.approved_at:
        return 0
    
    return (approval.approved_at - approval.created_at).total_seconds()

async def _execute_approved_action(approval_request: ApprovalRequest) -> Dict[str, Any]:
    """Execute an approved action (placeholder implementation)."""
    try:
        # This would contain the actual execution logic
        # For now, return a success result
        logger.info(f"Executing approved action: {approval_request.action_type}")
        
        return {
            "executed": True,
            "action_type": approval_request.action_type,
            "execution_time": datetime.now().isoformat(),
            "result": "Action executed successfully"
        }
    except Exception as e:
        logger.error(f"Error executing approved action: {e}")
        return {
            "executed": False,
            "error": str(e),
            "action_type": approval_request.action_type
        }

async def _send_urgent_approval_notification(approval_request: ApprovalRequest):
    """Send urgent notification for high-risk approval requests."""
    # Placeholder for notification logic (Slack, email, etc.)
    logger.info(f"URGENT: High-risk approval request {approval_request.request_id} requires immediate attention")

async def _send_rejection_notification(approval_request: ApprovalRequest, alternatives: Optional[List[str]]):
    """Send notification about request rejection."""
    # Placeholder for rejection notification logic
    logger.info(f"Approval request {approval_request.request_id} was rejected")

def _generate_approval_alerts(pending_stats: Dict, historical_stats: Dict) -> List[Dict[str, str]]:
    """Generate alerts based on approval statistics."""
    alerts = []
    
    if pending_stats["high_risk"] > 5:
        alerts.append({
            "level": "warning",
            "message": f"{pending_stats['high_risk']} high-risk requests pending approval"
        })
    
    if pending_stats["escalated"] > 3:
        alerts.append({
            "level": "critical",
            "message": f"{pending_stats['escalated']} requests have been escalated"
        })
    
    if pending_stats["expiring_soon"] > 0:
        alerts.append({
            "level": "info",
            "message": f"{pending_stats['expiring_soon']} requests expiring within 2 hours"
        })
    
    if historical_stats["approval_rate"] < 70:
        alerts.append({
            "level": "warning",
            "message": f"Low approval rate: {historical_stats['approval_rate']:.1f}% in last 30 days"
        })
    
    return alerts