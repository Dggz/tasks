import logging
from datetime import datetime

from celery import Celery, group, chord
from celery.result import GroupResult

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.operation import Operation, OperationStatus

celery = Celery(
    "worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

# Configure Celery for handling large results
celery.conf.update(
    result_extended=True,
    result_expires=60,  # Results expire in 1 minute
    task_track_started=True,
    task_serializer='json',
    result_serializer='json',
    accept_content=['json']
)

logger = logging.getLogger(__name__)


@celery.task(bind=True, name='tasks.process_operation')
def process_operation(self, operation_id: int) -> dict:
    """Process a single operation"""
    with SessionLocal() as db:
        operation = db.query(Operation).get(operation_id)
        if not operation:
            return {"status": "not_found"}

        try:
            operation.status = OperationStatus.IN_PROGRESS
            logger.info(f"Processing operation {operation_id=}")
            db.commit()

            # Perform the addition
            terms = operation.terms
            operation.result = terms['a'] + terms['b']
            operation.status = OperationStatus.COMPLETED
            logger.info(f"Operation {operation_id}, {terms=} completed with result {operation.result}")
            db.commit()

            return {
                "status": "completed",
                "result": operation.result,
                "operation_id": operation.id
            }

        except Exception as e:
            operation.status = OperationStatus.FAILED
            operation.extra_data = {
                **(operation.extra_data or {}),
                "error": str(e),
                "operation_id": operation.id
            }
            db.commit()
            return {"status": "failed", "error": str(e)}


@celery.task(name='tasks.process_batch_callback')
def process_batch_callback(results):
    """Callback task that runs after all operations in a batch are completed"""
    with SessionLocal() as db:
        # Group results by status
        status_count = {
            "completed": 0,
            "failed": 0,
            "not_found": 0
        }
        for result in results:
            status_count[result['status']] += 1

            # Update operation with batch completion info
            operation = db.query(Operation).get(result['operation_id'])
            if operation:
                operation.extra_data = {
                    **(operation.extra_data or {}),
                    "batch_completion_time": datetime.utcnow().isoformat(),
                    "batch_result": result
                }

        db.commit()

        return {
            "batch_completed_at": datetime.utcnow().isoformat(),
            "results": status_count
        }


def create_batch_processing_task(operation_ids: list[int]) -> GroupResult:
    """
    Create a distributed batch processing task using Celery chord
    Returns a GroupResult that can be used to track the batch progress
    """
    # Create a group of tasks for parallel processing
    operation_tasks = group(
        process_operation.s(op_id) for op_id in operation_ids
    )

    # Create a chord that will execute the callback after all operations are done
    batch_chord = chord(
        operation_tasks,
        process_batch_callback.s()
    )

    # Execute the chord
    result = batch_chord.apply_async()
    return result
