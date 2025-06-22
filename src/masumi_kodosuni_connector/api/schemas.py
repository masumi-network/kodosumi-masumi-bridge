from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel
from masumi_kodosuni_connector.models.agent_run import AgentRunStatus


class JobRequest(BaseModel):
    data: Dict[str, Any]
    payment_amount: Optional[float] = None


class JobResponse(BaseModel):
    id: int
    status: AgentRunStatus
    payment_id: Optional[str] = None
    created_at: datetime


class JobStatusResponse(BaseModel):
    id: int
    status: AgentRunStatus
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class PaymentRequest(BaseModel):
    run_id: int
    amount: float
    currency: str = "USD"


class PaymentResponse(BaseModel):
    payment_id: str
    payment_url: Optional[str] = None
    status: str