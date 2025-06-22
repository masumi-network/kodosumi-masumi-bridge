import json
from typing import Dict, Any
from pydantic import BaseSettings, Field, validator


class AgentConfig:
    def __init__(self, name: str, kodosumi_agent_id: str):
        self.name = name
        self.kodosumi_agent_id = kodosumi_agent_id


class Settings(BaseSettings):
    database_url: str = Field(..., env="DATABASE_URL")
    
    kodosumi_base_url: str = Field(..., env="KODOSUMI_BASE_URL")
    kodosumi_api_key: str = Field(..., env="KODOSUMI_API_KEY")
    
    masumi_node_url: str = Field(..., env="MASUMI_NODE_URL")
    masumi_api_key: str = Field(..., env="MASUMI_API_KEY")
    
    agents_config_raw: str = Field(..., env="AGENTS_CONFIG")
    
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    debug: bool = Field(default=False, env="DEBUG")
    
    polling_interval_seconds: int = Field(default=30, env="POLLING_INTERVAL_SECONDS")
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    @validator("agents_config_raw")
    def validate_agents_config(cls, v: str) -> str:
        try:
            config = json.loads(v)
            if not isinstance(config, dict):
                raise ValueError("Agents config must be a JSON object")
            for agent_key, agent_data in config.items():
                if not isinstance(agent_data, dict):
                    raise ValueError(f"Agent {agent_key} config must be an object")
                if "name" not in agent_data or "kodosumi_agent_id" not in agent_data:
                    raise ValueError(f"Agent {agent_key} must have 'name' and 'kodosumi_agent_id'")
            return v
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON in AGENTS_CONFIG")
    
    @property
    def agents_config(self) -> Dict[str, AgentConfig]:
        config_dict = json.loads(self.agents_config_raw)
        return {
            agent_key: AgentConfig(
                name=agent_data["name"],
                kodosumi_agent_id=agent_data["kodosumi_agent_id"]
            )
            for agent_key, agent_data in config_dict.items()
        }


settings = Settings()