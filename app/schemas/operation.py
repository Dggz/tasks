from datetime import datetime
from typing import Optional, List, Dict

from pydantic import BaseModel, field_validator

from app.models.operation import OperationType, OperationStatus


class Terms(BaseModel):
    a: int
    b: int


class OperationCreate(BaseModel):
    title: str
    description: Optional[str] = None
    type: OperationType
    deadline: Optional[datetime] = None
    expedited_reason: Optional[str] = None
    extra_data: Optional[Dict] = None
    terms: Terms


class Operation(OperationCreate):
    id: int
    status: OperationStatus
    result: Optional[Dict] = None
    extra_data: Optional[Dict] = None

    @field_validator('terms', check_fields=False)
    def validate_terms(cls, v):
        if not isinstance(v, (dict, Terms)):
            raise ValueError('Terms must be a dictionary or Terms object')
        if isinstance(v, dict):
            return Terms(**v)
        return v

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "title": "Simple Addition",
                "description": "Adding two numbers",
                "type": "regular",
                "terms": {
                    "a": 5,
                    "b": 3
                }
            }
        }


class OperationOutput(BaseModel):
    title: str
    description: Optional[str] = None
    type: OperationType = OperationType.REGULAR

    # Operation fields
    terms: Optional[Terms] = None
    result: Optional[int] = None

    # Optional fields
    deadline: Optional[datetime] = None
    expedited_reason: Optional[str] = None
    extra_data: Optional[Dict] = None

    # Auto-generated fields
    id: Optional[int] = None
    status: OperationStatus = OperationStatus.PENDING
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "title": "Simple Addition",
                "description": "Adding two numbers",
                "type": "regular",
                "terms": {
                    "a": 5,
                    "b": 3
                }
            }
        }


class BatchOperationCreate(BaseModel):
    batch_id: Optional[str] = None
    operations: List[OperationCreate]
    extra_data: Optional[Dict] = None
    atomic: bool = False  # Default to non-atomic for backward compatibility 


class BatchOperationValidationError(BaseModel):
    index: int
    error: str
    operation: Dict


class BatchOperationResponse(BaseModel):
    batch_id: str
    operation_count: int
    successful_operations: List[int]  # List of successful operation IDs
    failed_operations: List[BatchOperationValidationError]
    task_id: Optional[str] = None
    status: str
