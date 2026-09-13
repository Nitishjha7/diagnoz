import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DiagnosticSession(Base):
    __tablename__ = "diagnostic_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    technician_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    session_status: Mapped[str] = mapped_column(String(30), nullable=False, default="INITIATED")
    raw_audio_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    voice_transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_structured_summary: Mapped[dict] = mapped_column(JSONB, default=dict)
    raw_recording_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    hls_master_playlist_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
