import logging
import uuid
from datetime import datetime
from typing import List, Dict, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models import operation as models
from app.schemas import operation as schemas
from app.tasks.worker import create_batch_processing_task

logger = logging.getLogger(__name__)


class ServiceException(Exception):
    """Base exception for service layer"""
    pass


class OperationNotFoundError(ServiceException):
    """Raised when an operation is not found"""
    pass


class ValidationError(ServiceException):
    """Raised when business validation fails"""
    pass


class BatchOperationError(ServiceException):
    """Raised when batch operation processing fails"""

    def __init__(self, message: str, failed_operations: list = None):
        super().__init__(message)
        self.failed_operations = failed_operations or []


def create_operation(db: Session, operation: schemas.OperationCreate) -> models.Operation:
    """Create a single operation"""
    try:
        # Only validate deadline for expedited operations
        logger.info(f"Creating operation {operation.model_dump()=}")
        if operation.type == models.OperationType.EXPEDITED and not operation.deadline:
            raise ValidationError("Deadline is required for expedited operations")

        db_operation = models.Operation(**operation.model_dump())
        db.add(db_operation)
        db.commit()
        db.refresh(db_operation)

        logger.info(f"Created operation {db_operation=}")
        return db_operation

    except Exception as e:
        db.rollback()
        if isinstance(e, ServiceException):
            raise
        raise ServiceException(f"An unexpected error occurred: {str(e)}")


def create_batch_operations(
        db: Session,
        batch: schemas.BatchOperationCreate
) -> schemas.BatchOperationResponse:
    """Create multiple operations in a batch"""
    operations = []
    failed_operations = []
    # Use with caution, as this might produce duplicate batch ids
    # possible improvement: use a more deterministic way to generate batch ids or
    # a fast way to check if the batch id is already in use
    batch_id = str(uuid.uuid4()) if not batch.batch_id else batch.batch_id

    try:
        # First pass: validate all operations if atomic=True
        if batch.atomic:
            for idx, operation_data in enumerate(batch.operations):
                if operation_data.type == models.OperationType.EXPEDITED and not operation_data.deadline:
                    raise ValidationError(f"Operation {idx + 1}: Deadline is required for expedited operations")

        # Second pass: create operations
        for idx, operation_data in enumerate(batch.operations):
            try:
                # Only validate deadline for expedited operations
                if operation_data.type == models.OperationType.EXPEDITED and not operation_data.deadline:
                    raise ValidationError("Deadline is required for expedited operations")

                # Add batch metadata
                operation_extra_data = {
                    **(operation_data.extra_data or {}),
                    "batch_id": batch_id,
                    "batch_extra_data": batch.extra_data,
                    "batch_created_at": datetime.utcnow().isoformat()
                }
                operation_data.extra_data = operation_extra_data

                # Create operation
                db_operation = models.Operation(**operation_data.model_dump())
                db.add(db_operation)
                operations.append(db_operation)

            except Exception as e:
                if batch.atomic:
                    db.rollback()
                    raise BatchOperationError(f"Error in operation {idx + 1}: {str(e)}")
                else:
                    failed_operations.append(
                        schemas.BatchOperationValidationError(
                            index=idx,
                            error=str(e),
                            operation=operation_data.model_dump()
                        )
                    )

        # If we have any successful operations, commit them
        if operations:
            db.commit()
            operation_ids = []
            for op in operations:
                db.refresh(op)
                operation_ids.append(op.id)

            # Create and launch batch processing for successful operations
            batch_result = None
            if operation_ids:
                batch_result = create_batch_processing_task(operation_ids)

            return schemas.BatchOperationResponse(
                batch_id=batch_id,
                operation_count=len(batch.operations),
                successful_operations=operation_ids,
                failed_operations=failed_operations,
                task_id=batch_result.id if batch_result else None,
                status="processing" if operation_ids else "completed"
            )
        else:
            return schemas.BatchOperationResponse(
                batch_id=batch_id,
                operation_count=len(batch.operations),
                successful_operations=[],
                failed_operations=failed_operations,
                status="failed"
            )

    except Exception as e:
        db.rollback()
        raise BatchOperationError(f"Error creating batch: {str(e)}")


def get_operation(db: Session, operation_id: int) -> models.Operation:
    """Get a single operation by ID"""
    operation = db.query(models.Operation).get(operation_id)
    if not operation:
        raise OperationNotFoundError(f"Operation {operation_id} not found")
    return operation


def list_operations(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        operation_type: Optional[models.OperationType] = None,
        batch_id: Optional[str] = None
) -> List[models.Operation]:
    """List operations with optional filtering"""
    query = db.query(models.Operation)

    if operation_type:
        query = query.filter(models.Operation.type == operation_type)

    if batch_id:
        query = query.filter(
            models.Operation.extra_data.contains({"batch_extra_data": {"batch_id": batch_id}})
        )

    return query.offset(skip).limit(limit).all()


def get_batch_status(db: Session, batch_id: str) -> Dict:
    """Get status information for a batch of operations"""
    operations = db.query(models.Operation).filter(
        text("extra_data->>'batch_id' = :batch_id")
    ).params(batch_id=batch_id).all()

    if not operations:
        raise OperationNotFoundError(f"Batch {batch_id} not found")

    status_count = {
        models.OperationStatus.PENDING: 0,
        models.OperationStatus.IN_PROGRESS: 0,
        models.OperationStatus.COMPLETED: 0,
        models.OperationStatus.FAILED: 0
    }

    for operation in operations:
        status_count[operation.status] += 1

    return {
        "total_operations": len(operations),
        "status_count": status_count,
        "operations": [
            {
                "id": op.id,
                "status": op.status,
                "error": op.extra_data.get("error") if op.extra_data else None
            }
            for op in operations
        ]
    }


def delete_operation(db: Session, operation_id: int) -> None:
    """Delete a single operation by ID"""
    operation = db.query(models.Operation).get(operation_id)
    if not operation:
        raise OperationNotFoundError(f"Operation {operation_id} not found")
    
    db.delete(operation)
    db.commit()
