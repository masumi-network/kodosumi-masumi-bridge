from datetime import datetime
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from masumi_kodosuni_connector.models.agent_run import FlowRunStatus


class FlowRunRequest(BaseModel):
    inputs: Dict[str, Any]
    identifier_from_purchaser: str
    payment_amount: Optional[float] = None


class FlowRunResponse(BaseModel):
    id: str
    status: FlowRunStatus
    payment_id: Optional[str] = None
    created_at: datetime


class FlowRunStatusResponse(BaseModel):
    id: str
    status: FlowRunStatus
    result: Optional[Dict[str, Any]] = None
    events: Optional[List[Dict[str, Any]]] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class FlowInfo(BaseModel):
    key: str
    name: str
    description: str
    version: str
    author: Optional[str] = None
    tags: List[str]


class FlowListResponse(BaseModel):
    flows: List[FlowInfo]


class FlowSchemaResponse(BaseModel):
    flow_schema: Dict[str, Any]


class PaymentRequest(BaseModel):
    run_id: int
    amount: float
    currency: str = "USD"


class PaymentResponse(BaseModel):
    payment_id: str
    payment_url: Optional[str] = None
    status: str