import os
from typing import Dict, Any, Optional
from pydantic import Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables from .env file
# Try multiple paths to find .env file
import pathlib
project_root = pathlib.Path(__file__).parent.parent.parent.parent
env_paths = [
    project_root / ".env",
    pathlib.Path.cwd() / ".env",
    pathlib.Path(".env")
]

for env_path in env_paths:
    if env_path.exists():
        load_dotenv(env_path)
        break

class Settings(BaseSettings):
    database_url: str = Field(..., env="DATABASE_URL")
    
    kodosumi_base_url: str = Field(..., env="KODOSUMI_BASE_URL")
    kodosumi_username: str = Field(..., env="KODOSUMI_USERNAME")
    kodosumi_password: str = Field(..., env="KODOSUMI_PASSWORD")
    
    # Masumi Payment Service Configuration
    payment_service_url: str = Field(..., env="PAYMENT_SERVICE_URL")
    payment_api_key: str = Field(..., env="PAYMENT_API_KEY")
    network: str = Field(default="preprod", env="NETWORK")
    # Note: payment amounts and seller keys are configured within the masumi package, not here
    masumi_test_mode: bool = Field(default=False, env="MASUMI_TEST_MODE")
    
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    debug: bool = Field(default=False, env="DEBUG")
    
    polling_interval_seconds: int = Field(default=30, env="POLLING_INTERVAL_SECONDS")
    
    # API Security
    api_key: Optional[str] = Field(default=None, env="API_KEY")
    
    class Config:
        env_file = [str(p) for p in env_paths if p.exists()]
        case_sensitive = False
        extra = "ignore"  # Allow extra environment variables
    
    def get_agent_identifier(self, flow_key: str) -> Optional[str]:
        """Get the agent identifier for a specific flow."""
        # Import here to avoid circular imports
        from masumi_kodosuni_connector.services.agent_config_manager import agent_config_manager
        return agent_config_manager.get_agent_identifier(flow_key)
    
    def get_configured_agents(self) -> Dict[str, str]:
        """Get all configured agent identifiers."""
        # Import here to avoid circular imports
        from masumi_kodosuni_connector.services.agent_config_manager import agent_config_manager
        return agent_config_manager.get_configured_agents()
    
    def is_agent_enabled(self, flow_key: str) -> bool:
        """Check if an agent is enabled (has an identifier configured)."""
        # Import here to avoid circular imports
        from masumi_kodosuni_connector.services.agent_config_manager import agent_config_manager
        return agent_config_manager.is_agent_enabled(flow_key)


settings = Settings()