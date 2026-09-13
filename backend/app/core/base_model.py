from sqlalchemy import Column, Boolean, DateTime
from sqlalchemy.orm import declarative_mixin
from datetime import datetime, timezone


@declarative_mixin
class BaseAuditable:
    __abstract__ = True

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
    is_deleted = Column(Boolean, default=False, nullable=False)
    restored_at = Column(DateTime(timezone=True), nullable=True)
