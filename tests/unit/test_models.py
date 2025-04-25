from app.models.operation import Operation


def test_operation_creation(db_session, sample_operation_data):
    # Test basic model instantiation and persistence
    operation = Operation(**sample_operation_data)
    db_session.add(operation)
    db_session.commit()
    db_session.refresh(operation)

    assert operation.id is not None
    assert operation.title == sample_operation_data["title"]
    assert operation.type == sample_operation_data["type"]
    assert operation.terms == sample_operation_data["terms"]


def test_operation_update(db_session, sample_operation_data):
    # Test model field updates
    operation = Operation(**sample_operation_data)
    db_session.add(operation)
    db_session.commit()

    operation.title = "Updated Title"
    db_session.commit()
    db_session.refresh(operation)

    assert operation.title == "Updated Title"
