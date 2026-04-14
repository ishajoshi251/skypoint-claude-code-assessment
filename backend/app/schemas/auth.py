import re
from datetime import datetime

from pydantic import BaseModel, EmailStr, field_validator

from app.models.user import Role

# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------

PASSWORD_PATTERN = re.compile(
    r"^(?=.*[A-Z])(?=.*\d).{8,72}$"
)  # ≥8 chars, ≥1 uppercase, ≥1 digit; bcrypt truncates at 72


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    role: Role = Role.CANDIDATE

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not PASSWORD_PATTERN.match(v):
            raise ValueError(
                "Password must be at least 8 characters and contain "
                "at least one uppercase letter and one digit."
            )
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------


class UserOut(BaseModel):
    id: int
    email: str
    role: Role
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class RefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MessageResponse(BaseModel):
    message: str
