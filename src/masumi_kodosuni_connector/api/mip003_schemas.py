from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from pydantic import BaseModel, Field
from enum import Enum


# MIP-003 Job Status Enum
class JobStatus(str, Enum):
    PENDING = "pending"
    AWAITING_PAYMENT = "awaiting_payment"
    AWAITING_INPUT = "awaiting_input"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# Input Schema Types
class InputType(str, Enum):
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    OPTION = "option"
    NONE = "none"


class ValidationRule(BaseModel):
    validation: str = Field(..., description="Validation type: min, max, format, optional")
    value: Union[str, int, bool] = Field(..., description="Validation value")


class InputData(BaseModel):
    description: Optional[str] = None
    placeholder: Optional[str] = None
    values: Optional[List[str]] = None  # For option type


class InputField(BaseModel):
    id: str = Field(..., description="Unique identifier for the input field")
    type: InputType = Field(..., description="Type of the input field")
    name: Optional[str] = Field(None, description="Display name for the input field")
    data: Optional[InputData] = Field(None, description="Additional data for the input field")
    validations: Optional[List[ValidationRule]] = Field(None, description="Validation rules")


# MIP-003 Request/Response Models

class StartJobRequest(BaseModel):
    identifier_from_purchaser: str = Field(..., description="Purchaser-defined identifier")
    input_data: Dict[str, Any] = Field(..., description="Input data for the job")


class AmountInfo(BaseModel):
    amount: int = Field(..., description="Price amount")
    unit: str = Field(..., description="Unit identifier, e.g. 'lovelace' for ADA")


class StartJobResponse(BaseModel):
    status: str = Field(..., description="Status of job request: success or error")
    job_id: str = Field(..., description="Unique identifier for the started job")
    blockchainIdentifier: str = Field(..., description="Unique identifier for payment")
    submitResultTime: int = Field(..., description="Unix timestamp when result must be submitted")
    unlockTime: int = Field(..., description="Unix timestamp when payment can be unlocked")
    externalDisputeUnlockTime: int = Field(..., description="Unix timestamp until disputes can happen")
    agentIdentifier: str = Field(..., description="Agent identifier from registration")
    sellerVKey: str = Field(..., description="Wallet public key")
    identifierFromPurchaser: str = Field(..., description="Echoes back purchaser identifier")
    amounts: List[AmountInfo] = Field(..., description="Payment amounts")
    input_hash: str = Field(..., description="Hash of input data for integrity verification")


class JobStatusResponse(BaseModel):
    job_id: str = Field(..., description="Job identifier")
    status: JobStatus = Field(..., description="Current job status")
    message: Optional[str] = Field(None, description="Optional status message")
    input_data: Optional[List[InputField]] = Field(None, description="Required when status is awaiting_input")
    result: Optional[str] = Field(None, description="Job result if available")


class ProvideInputRequest(BaseModel):
    job_id: str = Field(..., description="Job ID awaiting input")
    input_data: Dict[str, Any] = Field(..., description="Additional input data")


class ProvideInputResponse(BaseModel):
    status: str = Field(..., description="Success status")


class AvailabilityResponse(BaseModel):
    status: str = Field(..., description="Server status: available or unavailable")
    type: str = Field(default="masumi-agent", description="Service type identifier")
    message: Optional[str] = Field(None, description="Additional message or details")


class InputSchemaResponse(BaseModel):
    input_data: List[InputField] = Field(..., description="Expected input schema")