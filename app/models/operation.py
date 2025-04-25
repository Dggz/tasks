import enum

from sqlalchemy import Column, Integer, String, DateTime, Enum, JSON
from sqlalchemy.sql import func

from app.core.database import Base


class OperationType(str, enum.Enum):
    REGULAR = "regular"
    EXPEDITED = "expedited"


class OperationStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class Operation(Base):
    __tablename__ = "operations"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String, nullable=True)
    type = Column(Enum(OperationType))
    status = Column(Enum(OperationStatus), default=OperationStatus.PENDING)

    # Operation specific fields
    terms = Column(JSON, nullable=True)  # {"a": number, "b": number}
    result = Column(Integer, nullable=True)

    # For expedited operations
    deadline = Column(DateTime(timezone=True), nullable=True)
    expedited_reason = Column(String, nullable=True)

    # Renamed from metadata to extra_data
    extra_data = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
