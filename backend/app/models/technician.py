import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column
from geoalchemy2 import Geometry

from app.core.database import Base


class TechnicianProfile(Base):
    __tablename__ = "technician_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    skills: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    current_location = mapped_column(Geometry(geometry_type="POINT", srid=4326), nullable=False)
    base_rating: Mapped[float] = mapped_column(Numeric(3, 2), default=5.00)
    wallet_balance: Mapped[float] = mapped_column(Numeric(12, 2), default=0.00)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
