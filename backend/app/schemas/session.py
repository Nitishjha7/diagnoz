import uuid
from datetime import datetime

from pydantic import BaseModel


class DiagnosticSessionCreate(BaseModel):
    pass


class DiagnosticSessionOut(BaseModel):
    id: uuid.UUID
    customer_id: uuid.UUID
    technician_id: uuid.UUID | None
    session_status: str
    voice_transcript: str | None
    ai_structured_summary: dict
    created_at: datetime
    ended_at: datetime | None

    model_config = {"from_attributes": True}
