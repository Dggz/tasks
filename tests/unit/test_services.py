from unittest.mock import patch

from app.core import service
from app.models.operation import OperationStatus, OperationType
from app.schemas.operation import OperationCreate, BatchOperationCreate


def test_create_operation(db_session, sample_operation_data):
    operation_create = OperationCreate(**sample_operation_data)

    operation = service.create_operation(db_session, operation_create)
    assert operation.title == sample_operation_data["title"]
    assert operation.terms == sample_operation_data["terms"]
    assert operation.status == OperationStatus.PENDING


def test_get_operation(db_session, sample_operation_data):
    operation_create = OperationCreate(**sample_operation_data)
    created_op = service.create_operation(db_session, operation_create)

    fetched_op = service.get_operation(db_session, created_op.id)
    assert fetched_op is not None
    assert fetched_op.id == created_op.id
    assert fetched_op.title == created_op.title


def test_list_operations(db_session, sample_operation_data):
    # Create multiple operations
    for i in range(3):
        data = dict(sample_operation_data)
        data["title"] = f"Operation {i}"
        operation_create = OperationCreate(**data)
        service.create_operation(db_session, operation_create)

    operations = service.list_operations(db_session)
    assert len(operations) == 3


@patch('app.core.service.create_batch_processing_task')
def test_batch_operation_creation(mock_create_batch_task, db_session, sample_operation_data):
    # Mock the Celery task result
    mock_create_batch_task.return_value.id = "mocked-task-id"

    operations = []
    for i in range(3):
        data = dict(sample_operation_data)
        data["title"] = f"Batch Operation {i}"
        data["type"] = OperationType.REGULAR
        data["terms"] = {"a": i + 1, "b": i + 2}
        operations.append(data)

    batch_create = BatchOperationCreate(
        operations=[OperationCreate(**op) for op in operations],
        atomic=True,
        extra_data={"test": "data"}
    )

    batch_result = service.create_batch_operations(db_session, batch_create)

    # Verify the results
    assert batch_result.operation_count == 3
    assert len(batch_result.successful_operations) == 3
    assert len(batch_result.failed_operations) == 0
    assert batch_result.task_id == "mocked-task-id"  # Verify the mocked task ID

    # Verify the task was called with correct operation IDs
    mock_create_batch_task.assert_called_once()
    called_operation_ids = mock_create_batch_task.call_args[0][0]  # Get first positional arg
    assert len(called_operation_ids) == 3


@patch('app.core.service.create_batch_processing_task')
def test_get_batch_status(mock_create_batch_task, db_session, sample_operation_data):
    # Mock the Celery task result
    mock_create_batch_task.return_value.id = "mocked-batch-id"
    # Create a batch first
    operations = []
    for i in range(3):
        data = dict(sample_operation_data)
        data["title"] = f"Batch Operation {i}"
        data["type"] = OperationType.REGULAR
        data["terms"] = {"a": i + 1, "b": i + 2}
        operations.append(data)

    batch_create = BatchOperationCreate(
        operations=[OperationCreate(**op) for op in operations],
        atomic=False,
        extra_data={"test": "data"},
        batch_id="mocked-batch-id"
    )

    batch_result = service.create_batch_operations(db_session, batch_create)

    # Get batch status
    status = service.get_batch_status(db_session, batch_result.batch_id)
    assert status["total_operations"] == 3
    assert all(op["status"] == OperationStatus.PENDING for op in status["operations"])

    # Verify the task was called with correct operation IDs
    mock_create_batch_task.assert_called_once()
    called_operation_ids = mock_create_batch_task.call_args[0][0]  # Get first positional arg
    assert len(called_operation_ids) == 3
