"""Agent configuration model for storing agent identifiers and enabled status."""
from sqlalchemy import Column, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from masumi_kodosuni_connector.models.agent_run import Base


class AgentConfig(Base):
    """Model for storing agent configuration including identifiers and enabled status."""
    
    __tablename__ = "agent_configs"
    
    flow_key = Column(String, primary_key=True, index=True)
    agent_identifier = Column(String, nullable=True)
    enabled = Column(Boolean, default=False, nullable=False)
    flow_name = Column(String, nullable=True)  # Cache flow name for easier lookup
    description = Column(Text, nullable=True)  # Cache description
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<AgentConfig(flow_key='{self.flow_key}', enabled={self.enabled}, agent_identifier='{self.agent_identifier}')>"