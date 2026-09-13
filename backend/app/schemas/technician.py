import uuid

from pydantic import BaseModel, Field


class TechnicianLocationUpdate(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class TechnicianProfileOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    skills: list[str]
    is_available: bool
    base_rating: float
    wallet_balance: float

    model_config = {"from_attributes": True}
