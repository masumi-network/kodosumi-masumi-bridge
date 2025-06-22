from typing import Dict, Any
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = Field(..., env="DATABASE_URL")
    
    kodosumi_base_url: str = Field(..., env="KODOSUMI_BASE_URL")
    kodosumi_username: str = Field(..., env="KODOSUMI_USERNAME")
    kodosumi_password: str = Field(..., env="KODOSUMI_PASSWORD")
    
    masumi_node_url: str = Field(..., env="MASUMI_NODE_URL")
    masumi_api_key: str = Field(..., env="MASUMI_API_KEY")
    
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    debug: bool = Field(default=False, env="DEBUG")
    
    polling_interval_seconds: int = Field(default=30, env="POLLING_INTERVAL_SECONDS")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()