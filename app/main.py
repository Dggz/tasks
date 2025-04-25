# app/main.py
import logging
from typing import List, Optional

from fastapi import FastAPI, Depends, BackgroundTasks, APIRouter, HTTPException
from sqlalchemy.orm import Session

from app.core import service
from app.core.config import settings
from app.core.database import get_db
from app.models import operation as models
from app.schemas import operation as schemas
from app.tasks.worker import process_operation

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/operations/", response_model=schemas.Operation)
async def create_operation(
        operation: schemas.OperationCreate,
        background_tasks: BackgroundTasks,
        db: Session = Depends(get_db)
):
    try:
        db_operation = service.create_operation(db, operation)
        background_tasks.add_task(
            process_operation.apply_async,
            args=[db_operation.id],
            priority=0 if db_operation.type == models.OperationType.EXPEDITED else 9
        )
        return db_operation
    except service.ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except service.ServiceException as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/operations/batch/", response_model=schemas.BatchOperationResponse)
async def create_batch_operations(
        batch: schemas.BatchOperationCreate,
        db: Session = Depends(get_db)
):
    return service.create_batch_operations(db, batch)


@router.get("/operations/", response_model=List[schemas.OperationOutput])
async def list_operations(
        skip: int = 0,
        limit: int = 100,
        operation_type: Optional[models.OperationType] = None,
        batch_id: Optional[str] = None,
        db: Session = Depends(get_db)
):
    try:
        result = service.list_operations(db, skip, limit, operation_type, batch_id)
    except Exception as e:
        logger.info(f"Error listing operations: {str(e)}")
        raise e
    return result


@router.get("/operations/{operation_id}", response_model=schemas.OperationOutput)
async def get_operation(operation_id: int, db: Session = Depends(get_db)):
    try:
        return service.get_operation(db, operation_id)
    except service.OperationNotFoundError:
        raise HTTPException(status_code=404, detail="Operation not found")
    except service.ServiceException as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/operations/batch/{batch_id}/status")
async def get_batch_status(batch_id: str, db: Session = Depends(get_db)):
    return service.get_batch_status(db, batch_id)


@router.delete("/operations/{operation_id}", status_code=200)
def delete_operation(operation_id: int, db: Session = Depends(get_db)):
    service.delete_operation(db, operation_id)
    return {"message": "Operation deleted successfully"}


app.include_router(router)
