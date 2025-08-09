from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import os

class Settings(BaseSettings):
    # Environment Configuration
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Database Configuration
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    
    # LLM API Keys
    gemini_api_key: Optional[str] = Field(default=None, env="GEMINI_API_KEY")
    anthropic_api_key: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    
    # External Service API Keys
    vapi_api_key: Optional[str] = Field(default=None, env="VAPI_API_KEY")
    vapi_phone_number_id: Optional[str] = Field(default=None, env="VAPI_PHONE_NUMBER_ID")
    vapi_assistant_id: Optional[str] = Field(default=None, env="VAPI_ASSISTANT_ID")
    github_token: Optional[str] = Field(default=None, env="GITHUB_TOKEN")
    google_calendar_credentials_path: Optional[str] = Field(default=None, env="GOOGLE_CALENDAR_CREDENTIALS_PATH")
    slack_bot_token: Optional[str] = Field(default=None, env="SLACK_BOT_TOKEN")
    slack_app_token: Optional[str] = Field(default=None, env="SLACK_APP_TOKEN")
    
    # Security
    jwt_secret_key: str = Field(default="your-secret-key-change-this", env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expire_minutes: int = Field(default=30, env="JWT_EXPIRE_MINUTES")
    
    # CORS
    cors_origins: str = Field(default='["http://localhost:3000"]', env="CORS_ORIGINS")
    
    # Rate Limiting
    rate_limit_requests_per_minute: int = Field(default=100, env="RATE_LIMIT_REQUESTS_PER_MINUTE")
    rate_limit_window: int = Field(default=60, env="RATE_LIMIT_WINDOW")
    
    # Application Settings
    app_name: str = Field(default="Aura Onboarding Agent", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    
    model_config = {"env_file": ".env", "case_sensitive": False, "extra": "ignore"}

# Global settings instance
settings = Settings()