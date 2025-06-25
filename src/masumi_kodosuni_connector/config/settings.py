import os
from typing import Dict, Any, Optional
from pydantic import Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv("/Users/patricktobler/masumi_kodosuni_connector/.env")
load_dotenv(".env")  # Also try from current directory

class Settings(BaseSettings):
    database_url: str = Field(..., env="DATABASE_URL")
    
    kodosumi_base_url: str = Field(..., env="KODOSUMI_BASE_URL")
    kodosumi_username: str = Field(..., env="KODOSUMI_USERNAME")
    kodosumi_password: str = Field(..., env="KODOSUMI_PASSWORD")
    
    # Masumi Payment Service Configuration
    payment_service_url: str = Field(..., env="PAYMENT_SERVICE_URL")
    payment_api_key: str = Field(..., env="PAYMENT_API_KEY")
    network: str = Field(default="preprod", env="NETWORK")
    seller_vkey: str = Field(..., env="SELLER_VKEY")
    payment_amount: str = Field(default="10000000", env="PAYMENT_AMOUNT")
    payment_unit: str = Field(default="lovelace", env="PAYMENT_UNIT")
    masumi_test_mode: bool = Field(default=False, env="MASUMI_TEST_MODE")
    
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    debug: bool = Field(default=False, env="DEBUG")
    
    polling_interval_seconds: int = Field(default=30, env="POLLING_INTERVAL_SECONDS")
    
    class Config:
        env_file = [".env", "/Users/patricktobler/masumi_kodosuni_connector/.env"]
        case_sensitive = False
        extra = "ignore"  # Allow extra environment variables
    
    def get_agent_identifier(self, flow_key: str) -> Optional[str]:
        """Get the agent identifier for a specific flow."""
        env_key = f"AGENT_IDENTIFIER_{flow_key}"
        return os.getenv(env_key)
    
    def get_agent_vkey(self, flow_key: str) -> str:
        """Get the seller vKey for a specific agent. Falls back to global vKey if not specified."""
        env_key = f"AGENT_VKEY_{flow_key}"
        agent_vkey = os.getenv(env_key)
        
        if agent_vkey:
            return agent_vkey
        
        # Fall back to global vKey
        return self.seller_vkey
    
    def get_configured_agents(self) -> Dict[str, str]:
        """Get all configured agent identifiers."""
        configured_agents = {}
        prefix = "AGENT_IDENTIFIER_"
        
        for key, value in os.environ.items():
            if key.startswith(prefix):
                flow_key = key[len(prefix):]
                configured_agents[flow_key] = value
        
        return configured_agents
    
    def get_configured_agent_vkeys(self) -> Dict[str, str]:
        """Get all configured agent-specific vKeys."""
        configured_vkeys = {}
        prefix = "AGENT_VKEY_"
        
        for key, value in os.environ.items():
            if key.startswith(prefix):
                flow_key = key[len(prefix):]
                configured_vkeys[flow_key] = value
        
        return configured_vkeys
    
    def is_agent_enabled(self, flow_key: str) -> bool:
        """Check if an agent is enabled (has an identifier configured)."""
        return self.get_agent_identifier(flow_key) is not None


settings = Settings()