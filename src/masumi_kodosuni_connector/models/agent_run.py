from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class AgentRunStatus(str, Enum):
    PENDING_PAYMENT = "pending_payment"
    PAYMENT_CONFIRMED = "payment_confirmed" 
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentRun(Base):
    __tablename__ = "agent_runs"
    
    id = Column(Integer, primary_key=True, index=True)
    agent_key = Column(String(50), nullable=False, index=True)
    kodosumi_job_id = Column(String(100), unique=True, index=True)
    masumi_payment_id = Column(String(100), index=True)
    
    status = Column(String(20), nullable=False, default=AgentRunStatus.PENDING_PAYMENT)
    
    request_data = Column(JSON)
    result_data = Column(JSON)
    error_message = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)