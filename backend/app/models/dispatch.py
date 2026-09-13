import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from geoalchemy2 import Geometry

from app.core.database import Base


class ServiceDispatch(Base):
    __tablename__ = "service_dispatches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("diagnostic_sessions.id"), nullable=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    technician_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    customer_location = mapped_column(Geometry(geometry_type="POINT", srid=4326), nullable=False)
    dispatch_status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING")
    start_otp_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    end_otp_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    parts_replaced: Mapped[list] = mapped_column(JSONB, default=list)
    total_service_fee: Mapped[float] = mapped_column(Numeric(10, 2), default=0.00)
    platform_commission_fee: Mapped[float] = mapped_column(Numeric(10, 2), default=0.00)
    technician_earnings: Mapped[float] = mapped_column(Numeric(10, 2), default=0.00)
    invoice_pdf_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
