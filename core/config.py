"""Configuration models and loading logic."""

import json
import os
from typing import Literal, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

class ProspectorConfig(BaseModel):
    """Main configuration model for the LinkedIn Prospector."""
    companies: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    location: str = "France"
    max_results_per_company: int = 50
    email_level: Literal['light', 'medium', 'heavy'] = 'medium'
    enable_smtp_check: bool = False
    proxy_url: Optional[str] = None
    linkedin_cookie: Optional[str] = None
    rate_limit_rpm: int = 20
    min_delay: float = 2.0
    max_delay: float = 7.0
    circuit_breaker_threshold: int = 3
    db_path: str = 'data/prospector.db'
    output_dir: str = 'output'
    warm_up_days: int = 14
    daily_profile_limit: int = 200
    daily_search_limit: int = 50

    @classmethod
    def from_json(cls, path: str) -> "ProspectorConfig":
        """Load configuration from a JSON file and environment variables."""
        load_dotenv()
        
        config_data = {}
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                
        # Override with env vars where applicable
        if os.getenv("LI_AT_COOKIE"):
            config_data["linkedin_cookie"] = os.getenv("LI_AT_COOKIE")
        if os.getenv("PROXY_URL"):
            config_data["proxy_url"] = os.getenv("PROXY_URL")
            
        return cls(**config_data)
        
    def to_json(self, path: str) -> None:
        """Save configuration to a JSON file."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(self.model_dump_json(indent=2))
