import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class DispatchCreate(BaseModel):
    session_id: uuid.UUID | None = None
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class DispatchOut(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID | None
    customer_id: uuid.UUID
    technician_id: uuid.UUID
    dispatch_status: str
    parts_replaced: list
    total_service_fee: float
    platform_commission_fee: float
    technician_earnings: float
    invoice_pdf_url: str | None
    created_at: datetime
    completed_at: datetime | None
    settled_at: datetime | None

    model_config = {"from_attributes": True}


class DispatchCreatedResponse(BaseModel):
    dispatch: DispatchOut
    start_otp: str
    end_otp: str


class OtpVerifyRequest(BaseModel):
    otp: str = Field(min_length=4, max_length=10)
