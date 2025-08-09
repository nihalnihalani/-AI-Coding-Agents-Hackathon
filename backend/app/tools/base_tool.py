from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from enum import Enum
import logging
import asyncio
from datetime import datetime, timedelta
import time

from ..core.logging import get_logger

logger = get_logger(__name__)

class ToolStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    RATE_LIMITED = "rate_limited"

class ToolPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ToolExecutionResult:
    """Result of tool execution with metadata."""
    
    def __init__(
        self,
        success: bool,
        data: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        execution_time: float = 0.0
    ):
        self.success = success
        self.data = data or {}
        self.error = error
        self.metadata = metadata or {}
        self.execution_time = execution_time
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "metadata": self.metadata,
            "execution_time": self.execution_time,
            "timestamp": self.timestamp.isoformat()
        }

class BaseTool(ABC):
    """Abstract base class for external tools."""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.status = ToolStatus.IDLE
        self.last_execution = None
        self.execution_count = 0
        self.error_count = 0
        self.rate_limit_reset = None
        
        # Rate limiting configuration
        self.max_requests_per_minute = 60
        self.max_requests_per_hour = 1000
        self.request_history = []
        
        # Retry configuration
        self.max_retries = 3
        self.retry_delay = 1.0  # seconds
        self.backoff_multiplier = 2.0
    
    @abstractmethod
    async def execute(self, action: str, parameters: Dict[str, Any]) -> ToolExecutionResult:
        """Execute a tool action with parameters."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the tool is available and properly configured."""
        pass
    
    @abstractmethod
    def get_available_actions(self) -> List[str]:
        """Get list of available actions for this tool."""
        pass
    
    async def execute_with_retry(self, action: str, parameters: Dict[str, Any]) -> ToolExecutionResult:
        """Execute tool action with automatic retry logic."""
        start_time = time.time()
        
        try:
            # Check if tool is available
            if not self.is_available():
                return ToolExecutionResult(
                    success=False,
                    error=f"Tool {self.name} is not available",
                    execution_time=time.time() - start_time
                )
            
            # Check rate limits
            rate_limit_check = await self._check_rate_limits()
            if not rate_limit_check["allowed"]:
                return ToolExecutionResult(
                    success=False,
                    error=f"Rate limit exceeded. Reset at {rate_limit_check['reset_time']}",
                    metadata={"rate_limited": True, "reset_time": rate_limit_check["reset_time"]},
                    execution_time=time.time() - start_time
                )
            
            # Validate action
            if action not in self.get_available_actions():
                return ToolExecutionResult(
                    success=False,
                    error=f"Action '{action}' not available for tool {self.name}",
                    execution_time=time.time() - start_time
                )
            
            # Execute with retry logic
            last_error = None
            for attempt in range(self.max_retries):
                try:
                    self.status = ToolStatus.RUNNING
                    logger.info(f"Executing {self.name}.{action} (attempt {attempt + 1}/{self.max_retries})")
                    
                    # Add to request history for rate limiting
                    self.request_history.append(datetime.now())
                    
                    # Execute the actual tool action
                    result = await self.execute(action, parameters)
                    
                    # Update execution stats
                    self.execution_count += 1
                    self.last_execution = datetime.now()
                    
                    if result.success:
                        self.status = ToolStatus.SUCCESS
                        result.execution_time = time.time() - start_time
                        result.metadata.update({
                            "tool_name": self.name,
                            "action": action,
                            "attempt": attempt + 1,
                            "total_executions": self.execution_count
                        })
                        return result
                    else:
                        last_error = result.error
                        self.error_count += 1
                        
                        # Don't retry on certain types of errors
                        if self._should_not_retry(result.error):
                            break
                
                except Exception as e:
                    last_error = str(e)
                    self.error_count += 1
                    logger.error(f"Error executing {self.name}.{action} (attempt {attempt + 1}): {e}")
                
                # Wait before retry (with exponential backoff)
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (self.backoff_multiplier ** attempt)
                    await asyncio.sleep(delay)
            
            # All retries failed
            self.status = ToolStatus.ERROR
            return ToolExecutionResult(
                success=False,
                error=f"All {self.max_retries} attempts failed. Last error: {last_error}",
                metadata={
                    "tool_name": self.name,
                    "action": action,
                    "total_attempts": self.max_retries,
                    "total_executions": self.execution_count,
                    "error_count": self.error_count
                },
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            self.status = ToolStatus.ERROR
            logger.error(f"Unexpected error in {self.name} execution: {e}")
            return ToolExecutionResult(
                success=False,
                error=f"Unexpected error: {str(e)}",
                execution_time=time.time() - start_time
            )
        finally:
            if self.status == ToolStatus.RUNNING:
                self.status = ToolStatus.IDLE
    
    async def _check_rate_limits(self) -> Dict[str, Any]:
        """Check if the tool is within rate limits."""
        now = datetime.now()
        
        # Clean old requests from history
        minute_ago = now - timedelta(minutes=1)
        hour_ago = now - timedelta(hours=1)
        
        self.request_history = [
            req_time for req_time in self.request_history 
            if req_time > hour_ago
        ]
        
        # Count recent requests
        recent_minute = len([
            req_time for req_time in self.request_history 
            if req_time > minute_ago
        ])
        recent_hour = len(self.request_history)
        
        # Check limits
        if recent_minute >= self.max_requests_per_minute:
            return {
                "allowed": False,
                "reason": "per_minute_limit_exceeded",
                "reset_time": (minute_ago + timedelta(minutes=1)).isoformat(),
                "current_requests": recent_minute,
                "limit": self.max_requests_per_minute
            }
        
        if recent_hour >= self.max_requests_per_hour:
            return {
                "allowed": False,
                "reason": "per_hour_limit_exceeded",
                "reset_time": (hour_ago + timedelta(hours=1)).isoformat(),
                "current_requests": recent_hour,
                "limit": self.max_requests_per_hour
            }
        
        return {
            "allowed": True,
            "requests_minute": recent_minute,
            "requests_hour": recent_hour,
            "limit_minute": self.max_requests_per_minute,
            "limit_hour": self.max_requests_per_hour
        }
    
    def _should_not_retry(self, error_message: str) -> bool:
        """Determine if an error should not be retried."""
        no_retry_indicators = [
            "authentication failed",
            "invalid credentials",
            "permission denied",
            "not found",
            "bad request",
            "invalid parameters",
            "unauthorized",
            "forbidden"
        ]
        
        error_lower = error_message.lower()
        return any(indicator in error_lower for indicator in no_retry_indicators)
    
    def get_status(self) -> Dict[str, Any]:
        """Get current tool status and statistics."""
        return {
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "available": self.is_available(),
            "execution_count": self.execution_count,
            "error_count": self.error_count,
            "last_execution": self.last_execution.isoformat() if self.last_execution else None,
            "available_actions": self.get_available_actions(),
            "rate_limit_info": {
                "max_per_minute": self.max_requests_per_minute,
                "max_per_hour": self.max_requests_per_hour,
                "recent_requests": len(self.request_history)
            }
        }
    
    def reset_stats(self) -> None:
        """Reset execution statistics."""
        self.execution_count = 0
        self.error_count = 0
        self.last_execution = None
        self.request_history = []
        self.status = ToolStatus.IDLE

class MockTool(BaseTool):
    """Mock tool implementation for testing and development."""
    
    def __init__(self, name: str = "mock_tool"):
        super().__init__(
            name=name,
            description="Mock tool for testing and development"
        )
        self.mock_responses = {}
        self.simulate_delays = False
        self.delay_range = (0.1, 0.5)  # seconds
    
    async def execute(self, action: str, parameters: Dict[str, Any]) -> ToolExecutionResult:
        """Execute mock action."""
        # Simulate processing delay
        if self.simulate_delays:
            import random
            delay = random.uniform(*self.delay_range)
            await asyncio.sleep(delay)
        
        # Check for pre-configured mock responses
        if action in self.mock_responses:
            response = self.mock_responses[action]
            if isinstance(response, Exception):
                raise response
            return ToolExecutionResult(
                success=True,
                data=response,
                metadata={"mock": True, "action": action}
            )
        
        # Default mock response
        return ToolExecutionResult(
            success=True,
            data={
                "message": f"Mock execution of {action}",
                "parameters": parameters,
                "timestamp": datetime.now().isoformat()
            },
            metadata={"mock": True, "action": action}
        )
    
    def is_available(self) -> bool:
        """Mock tool is always available."""
        return True
    
    def get_available_actions(self) -> List[str]:
        """Get available mock actions."""
        return ["test_action", "simulate_success", "simulate_error", "echo"]
    
    def set_mock_response(self, action: str, response: Any) -> None:
        """Set a mock response for a specific action."""
        self.mock_responses[action] = response
    
    def enable_delays(self, min_delay: float = 0.1, max_delay: float = 0.5) -> None:
        """Enable simulated processing delays."""
        self.simulate_delays = True
        self.delay_range = (min_delay, max_delay)