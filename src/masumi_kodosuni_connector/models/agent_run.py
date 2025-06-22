from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class FlowRunStatus(str, Enum):
    PENDING_PAYMENT = "pending_payment"
    PAYMENT_CONFIRMED = "payment_confirmed" 
    STARTING = "starting"
    RUNNING = "running"
    FINISHED = "finished"
    ERROR = "error"
    CANCELLED = "cancelled"


class FlowRun(Base):
    __tablename__ = "flow_runs"
    
    id = Column(Integer, primary_key=True, index=True)
    flow_path = Column(String(200), nullable=False, index=True)
    flow_name = Column(String(100), nullable=False)
    kodosumi_run_id = Column(String(100), unique=True, index=True)
    masumi_payment_id = Column(String(100), index=True)
    
    status = Column(String(20), nullable=False, default=FlowRunStatus.PENDING_PAYMENT)
    
    inputs = Column(JSON)
    result_data = Column(JSON)
    events = Column(JSON)
    error_message = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)