from typing import Dict, List, Optional, Any, Type
import logging
from datetime import datetime

from .base_tool import BaseTool, ToolExecutionResult, ToolStatus
from ..core.logging import get_logger

logger = get_logger(__name__)

class ToolRegistry:
    """Registry for managing and discovering external tools."""
    
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._tool_categories: Dict[str, List[str]] = {}
        self._initialized = False
    
    def register_tool(self, tool: BaseTool, category: str = "general") -> None:
        """Register a tool in the registry."""
        try:
            if tool.name in self._tools:
                logger.warning(f"Tool {tool.name} is already registered, overwriting")
            
            self._tools[tool.name] = tool
            
            # Add to category
            if category not in self._tool_categories:
                self._tool_categories[category] = []
            
            if tool.name not in self._tool_categories[category]:
                self._tool_categories[category].append(tool.name)
            
            logger.info(f"Registered tool: {tool.name} in category: {category}")
            
        except Exception as e:
            logger.error(f"Error registering tool {tool.name}: {e}")
            raise
    
    def unregister_tool(self, tool_name: str) -> bool:
        """Unregister a tool from the registry."""
        try:
            if tool_name not in self._tools:
                logger.warning(f"Tool {tool_name} not found in registry")
                return False
            
            # Remove from tools
            del self._tools[tool_name]
            
            # Remove from categories
            for category, tools in self._tool_categories.items():
                if tool_name in tools:
                    tools.remove(tool_name)
            
            logger.info(f"Unregistered tool: {tool_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error unregistering tool {tool_name}: {e}")
            return False
    
    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """Get a tool by name."""
        return self._tools.get(tool_name)
    
    def get_available_tools(self, category: Optional[str] = None) -> List[str]:
        """Get list of available tool names, optionally filtered by category."""
        if category:
            return self._tool_categories.get(category, [])
        return list(self._tools.keys())
    
    def get_tools_by_category(self, category: str) -> List[BaseTool]:
        """Get all tools in a specific category."""
        tool_names = self._tool_categories.get(category, [])
        return [self._tools[name] for name in tool_names if name in self._tools]
    
    def get_categories(self) -> List[str]:
        """Get all available categories."""
        return list(self._tool_categories.keys())
    
    async def execute_tool(self, tool_name: str, action: str, parameters: Dict[str, Any]) -> ToolExecutionResult:
        """Execute a tool action."""
        try:
            tool = self.get_tool(tool_name)
            if not tool:
                return ToolExecutionResult(
                    success=False,
                    error=f"Tool {tool_name} not found in registry"
                )
            
            if not tool.is_available():
                return ToolExecutionResult(
                    success=False,
                    error=f"Tool {tool_name} is not available"
                )
            
            result = await tool.execute_with_retry(action, parameters)
            
            # Log execution
            logger.info(
                f"Tool execution: {tool_name}.{action} - "
                f"Success: {result.success}, Time: {result.execution_time:.2f}s"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}.{action}: {e}")
            return ToolExecutionResult(
                success=False,
                error=f"Tool execution error: {str(e)}"
            )
    
    def get_tool_status(self, tool_name: Optional[str] = None) -> Dict[str, Any]:
        """Get status of one or all tools."""
        if tool_name:
            tool = self.get_tool(tool_name)
            if tool:
                return tool.get_status()
            return {"error": f"Tool {tool_name} not found"}
        
        # Return status of all tools
        return {
            tool_name: tool.get_status()
            for tool_name, tool in self._tools.items()
        }
    
    def get_registry_summary(self) -> Dict[str, Any]:
        """Get summary of the tool registry."""
        total_tools = len(self._tools)
        available_tools = len([t for t in self._tools.values() if t.is_available()])
        
        category_summary = {}
        for category, tool_names in self._tool_categories.items():
            category_tools = [self._tools[name] for name in tool_names if name in self._tools]
            category_summary[category] = {
                "total": len(category_tools),
                "available": len([t for t in category_tools if t.is_available()]),
                "tools": tool_names
            }
        
        return {
            "total_tools": total_tools,
            "available_tools": available_tools,
            "categories": category_summary,
            "registry_initialized": self._initialized,
            "last_updated": datetime.now().isoformat()
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all registered tools."""
        health_results = {}
        
        for tool_name, tool in self._tools.items():
            try:
                start_time = datetime.now()
                is_available = tool.is_available()
                response_time = (datetime.now() - start_time).total_seconds()
                
                health_results[tool_name] = {
                    "available": is_available,
                    "response_time": response_time,
                    "status": tool.status,
                    "execution_count": tool.execution_count,
                    "error_count": tool.error_count,
                    "error_rate": tool.error_count / max(tool.execution_count, 1)
                }
                
            except Exception as e:
                health_results[tool_name] = {
                    "available": False,
                    "error": str(e),
                    "response_time": None
                }
        
        # Calculate overall health
        total_tools = len(health_results)
        healthy_tools = len([r for r in health_results.values() if r.get("available", False)])
        
        return {
            "overall_health": healthy_tools / max(total_tools, 1) * 100,
            "total_tools": total_tools,
            "healthy_tools": healthy_tools,
            "tool_details": health_results,
            "timestamp": datetime.now().isoformat()
        }
    
    def find_tools_for_action(self, action_keyword: str) -> List[Dict[str, Any]]:
        """Find tools that support actions containing a keyword."""
        matching_tools = []
        
        for tool_name, tool in self._tools.items():
            try:
                available_actions = tool.get_available_actions()
                matching_actions = [
                    action for action in available_actions
                    if action_keyword.lower() in action.lower()
                ]
                
                if matching_actions:
                    matching_tools.append({
                        "tool_name": tool_name,
                        "matching_actions": matching_actions,
                        "all_actions": available_actions,
                        "available": tool.is_available(),
                        "description": tool.description
                    })
                    
            except Exception as e:
                logger.error(f"Error checking actions for tool {tool_name}: {e}")
        
        return matching_tools
    
    def suggest_tools_for_intent(self, intent: str) -> List[Dict[str, Any]]:
        """Suggest appropriate tools based on user intent."""
        intent_tool_mapping = {
            "calendar_scheduling": ["calendar_tool"],
            "document_upload": ["document_tool"],
            "tool_interaction": ["slack_tool", "github_tool"],
            "onboarding_planning": ["calendar_tool", "slack_tool", "github_tool"],
            "task_management": ["github_tool", "calendar_tool"],
            "approval_request": ["slack_tool"],
            "information_request": ["document_tool"]
        }
        
        suggested_tool_names = intent_tool_mapping.get(intent, [])
        suggested_tools = []
        
        for tool_name in suggested_tool_names:
            tool = self.get_tool(tool_name)
            if tool:
                suggested_tools.append({
                    "tool_name": tool_name,
                    "available": tool.is_available(),
                    "description": tool.description,
                    "actions": tool.get_available_actions(),
                    "confidence": 0.8  # Could be made more sophisticated
                })
        
        return suggested_tools
    
    def initialize_default_tools(self) -> None:
        """Initialize default tools (to be called during app startup)."""
        try:
            # Import and register default tools
            from .calendar_tool import CalendarTool
            from .slack_tool import SlackTool
            from .github_tool import GitHubTool
            from .document_tool import DocumentTool
            
            # Register tools in appropriate categories
            self.register_tool(CalendarTool(), "productivity")
            self.register_tool(SlackTool(), "communication")
            self.register_tool(GitHubTool(), "development")
            self.register_tool(DocumentTool(), "content")
            
            self._initialized = True
            logger.info("Default tools initialized successfully")
            
        except ImportError as e:
            logger.warning(f"Some default tools could not be imported: {e}")
            # Register mock tools for development
            from .base_tool import MockTool
            
            self.register_tool(MockTool("calendar_tool"), "productivity")
            self.register_tool(MockTool("slack_tool"), "communication")
            self.register_tool(MockTool("github_tool"), "development")
            self.register_tool(MockTool("document_tool"), "content")
            
            self._initialized = True
            logger.info("Mock tools registered for development")
            
        except Exception as e:
            logger.error(f"Error initializing default tools: {e}")
            raise

# Global tool registry instance
tool_registry = ToolRegistry()