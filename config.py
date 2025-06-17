"""
Configuration management for the email automation agent.
"""
import os
from dataclasses import dataclass
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

@dataclass
class BrowserConfig:
    """Browser automation configuration"""
    headless: bool = False
    timeout: int = 30000
    viewport_width: int = 1280
    viewport_height: int = 800
    user_agent: str = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    )
   

@dataclass
class ThrottlingConfig:
    """Human-like behavior configuration"""
    min_typing_delay: float = 0.1
    max_typing_delay: float = 0.3
    min_action_delay: float = 1.0
    max_action_delay: float = 3.0
    min_page_load_delay: float = 2.0
    max_page_load_delay: float = 5.0

@dataclass
class AIConfig:
    """AI service configuration"""
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    model: str = "gpt-4o"
    max_tokens: int = 500
    temperature: float = 0.7

@dataclass
class EmailConfig:
    """Email platform configuration"""
    platform_url: str = os.getenv("EMAIL_PLATFORM_URL", "https://login.live.com/")
    username: str = os.getenv("EMAIL_USERNAME", "")
    password: str = os.getenv("EMAIL_PASSWORD", "")
    inbox_check_interval: int = 1800  # seconds

class Config:
    """Main configuration class"""
    
    def __init__(self):
        self.browser = BrowserConfig()
        self.throttling = ThrottlingConfig()
        self.ai = AIConfig()
        self.email = EmailConfig()
        self.validate()
    
    def validate(self):
        """Validate required configuration"""
        if not self.ai.openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        if not self.email.username or not self.email.password:
            raise ValueError("EMAIL_USERNAME and EMAIL_PASSWORD environment variables are required")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary"""
        return {
            'browser': self.browser.__dict__,
            'throttling': self.throttling.__dict__,
            'ai': self.ai.__dict__,
            'email': {k: v for k, v in self.email.__dict__.items() if k != 'password'}
        }