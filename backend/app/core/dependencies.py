from fastapi import Depends, HTTPException, status
from redis import Redis
import google.generativeai as genai
from anthropic import Anthropic
from typing import Optional
import logging

from .config import settings

logger = logging.getLogger(__name__)

# Redis connection
def get_redis_client() -> Redis:
    try:
        redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
        redis_client.ping()
        return redis_client
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed"
        )

# Google Generative AI client
def get_gemini_client() -> Optional[genai.GenerativeModel]:
    if not settings.google_api_key:
        logger.warning("Google API key not configured")
        return None
    
    try:
        genai.configure(api_key=settings.google_api_key)
        return genai.GenerativeModel('gemini-pro')
    except Exception as e:
        logger.error(f"Failed to initialize Gemini client: {e}")
        return None

# Anthropic Claude client
def get_claude_client() -> Optional[Anthropic]:
    if not settings.anthropic_api_key:
        logger.warning("Anthropic API key not configured")
        return None
    
    try:
        return Anthropic(api_key=settings.anthropic_api_key)
    except Exception as e:
        logger.error(f"Failed to initialize Claude client: {e}")
        return None

# Dependency injection functions
def redis_dependency() -> Redis:
    return get_redis_client()

def gemini_dependency() -> Optional[genai.GenerativeModel]:
    return get_gemini_client()

def claude_dependency() -> Optional[Anthropic]:
    return get_claude_client()