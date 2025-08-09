from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import logging
from enum import Enum

import google.generativeai as genai
from anthropic import Anthropic

from ..core.config import settings
from ..core.logging import get_logger

logger = get_logger(__name__)

class LLMProvider(str, Enum):
    GEMINI = "gemini"
    CLAUDE = "claude"

class BaseLLMService(ABC):
    """Abstract base class for LLM services."""
    
    @abstractmethod
    async def generate_text(self, prompt: str, **kwargs) -> str:
        """Generate text response from the LLM."""
        pass
    
    @abstractmethod
    async def analyze_document(self, document_content: bytes, document_type: str) -> Dict[str, Any]:
        """Analyze document content (multimodal capability)."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the LLM service is available."""
        pass

class GeminiService(BaseLLMService):
    """Google Gemini LLM service implementation."""
    
    def __init__(self):
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the Gemini client."""
        if not settings.google_api_key:
            logger.warning("Google API key not configured")
            return
        
        try:
            genai.configure(api_key=settings.google_api_key)
            self.client = genai.GenerativeModel("gemini-2.5-pro")
            logger.info("Gemini client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {e}")
            self.client = None
    
    async def generate_text(self, prompt: str, **kwargs) -> str:
        """Generate text response using Gemini."""
        if not self.client:
            raise Exception("Gemini client not available")
        
        try:
            response = self.client.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Gemini text generation failed: {e}")
            raise
    
    async def analyze_document(self, document_content: bytes, document_type: str) -> Dict[str, Any]:
        """Analyze document using Gemini's multimodal capabilities."""
        if not self.client:
            raise Exception("Gemini client not available")
        
        try:
            # For PDF/image analysis, we'd use the vision model
            vision_model = genai.GenerativeModel('gemini-pro-vision')
            
            # This is a placeholder - actual implementation would handle different document types
            prompt = f"Analyze this {document_type} document and extract key information including skills, experience, education, and any relevant details for onboarding planning."
            
            # Note: In real implementation, you'd pass the document content properly
            response = await self.generate_text(prompt)
            
            return {
                "analysis": response,
                "document_type": document_type,
                "extracted_skills": [],  # Would be populated from actual analysis
                "extracted_experience": [],
                "extracted_education": []
            }
        except Exception as e:
            logger.error(f"Gemini document analysis failed: {e}")
            raise
    
    def is_available(self) -> bool:
        """Check if Gemini service is available."""
        return self.client is not None

class ClaudeService(BaseLLMService):
    """Anthropic Claude LLM service implementation."""
    
    def __init__(self):
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the Claude client."""
        if not settings.anthropic_api_key:
            logger.warning("Anthropic API key not configured")
            return
        
        try:
            self.client = Anthropic(api_key=settings.anthropic_api_key)
            logger.info("Claude client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Claude client: {e}")
            self.client = None
    
    async def generate_text(self, prompt: str, **kwargs) -> str:
        """Generate text response using Claude."""
        if not self.client:
            raise Exception("Claude client not available")
        
        try:
            response = self.client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=kwargs.get("max_tokens", 1000),
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Claude text generation failed: {e}")
            raise
    
    async def analyze_document(self, document_content: bytes, document_type: str) -> Dict[str, Any]:
        """Analyze document using Claude (text-based analysis)."""
        if not self.client:
            raise Exception("Claude client not available")
        
        try:
            # Claude would receive extracted text from the document
            prompt = f"Analyze this {document_type} content and provide structured information about skills, experience, and education for onboarding purposes."
            
            response = await self.generate_text(prompt)
            
            return {
                "analysis": response,
                "document_type": document_type,
                "safety_assessment": "safe",  # Claude's strong safety features
                "recommendations": []
            }
        except Exception as e:
            logger.error(f"Claude document analysis failed: {e}")
            raise
    
    def is_available(self) -> bool:
        """Check if Claude service is available."""
        return self.client is not None

class LLMRouter:
    """Router for selecting appropriate LLM based on task requirements."""
    
    def __init__(self):
        self.gemini_service = GeminiService()
        self.claude_service = ClaudeService()
    
    def select_llm(self, task_type: str, requirements: Dict[str, Any] = None) -> BaseLLMService:
        """Select the most appropriate LLM for the given task."""
        requirements = requirements or {}
        
        # Route based on task type
        if task_type in ["document_analysis", "multimodal", "resume_processing"]:
            if self.gemini_service.is_available():
                logger.info("Selected Gemini for multimodal task")
                return self.gemini_service
            elif self.claude_service.is_available():
                logger.info("Fallback to Claude for text analysis")
                return self.claude_service
        
        elif task_type in ["conversation", "safety_check", "text_processing"]:
            if self.claude_service.is_available():
                logger.info("Selected Claude for conversational task")
                return self.claude_service
            elif self.gemini_service.is_available():
                logger.info("Fallback to Gemini for text task")
                return self.gemini_service
        
        # Default fallback
        if self.gemini_service.is_available():
            return self.gemini_service
        elif self.claude_service.is_available():
            return self.claude_service
        else:
            raise Exception("No LLM services available")
    
    async def generate_response(self, task_type: str, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate response using the most appropriate LLM."""
        try:
            llm_service = self.select_llm(task_type, kwargs.get("requirements", {}))
            response = await llm_service.generate_text(prompt, **kwargs)
            
            return {
                "response": response,
                "llm_used": type(llm_service).__name__,
                "task_type": task_type,
                "success": True
            }
        except Exception as e:
            logger.error(f"LLM routing failed: {e}")
            return {
                "response": "I apologize, but I'm having trouble processing your request right now. Please try again.",
                "llm_used": "fallback",
                "task_type": task_type,
                "success": False,
                "error": str(e)
            }