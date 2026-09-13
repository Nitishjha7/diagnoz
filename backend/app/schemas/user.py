import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserRegister(BaseModel):
    full_name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    phone_number: str = Field(min_length=6, max_length=20)
    password: str = Field(min_length=8, max_length=128)
    role: str = Field(pattern="^(CUSTOMER|TECHNICIAN|ADMIN)$")


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: uuid.UUID
    full_name: str
    email: EmailStr
    phone_number: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
