import pytest

from app.schemas.operation import (
    OperationCreate,
    Terms,
    BatchOperationCreate
)


def test_terms_validation():
    terms = Terms(a=5, b=3)
    assert terms.a == 5
    assert terms.b == 3


def test_operation_create_validation(sample_operation_data):
    operation = OperationCreate(**sample_operation_data)
    assert operation.title == sample_operation_data["title"]
    assert operation.terms.a == sample_operation_data["terms"]["a"]
    assert operation.terms.b == sample_operation_data["terms"]["b"]


def test_operation_priority_validation():
    with pytest.raises(ValueError):
        OperationCreate(
            title="Test",
            terms={"a": 1, "b": 2}
        )


def test_batch_operation_validation(sample_operation_data):
    operations = [sample_operation_data for _ in range(3)]
    batch = BatchOperationCreate(operations=operations)
    assert len(batch.operations) == 3
    assert batch.atomic is False  # Default value
