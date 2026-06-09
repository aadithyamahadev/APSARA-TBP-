from enum import Enum
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class PasswordStatus(str, Enum):
    SAFE = "SAFE"
    RISKY = "RISKY"
    BREACHED = "BREACHED"


class CheckPasswordRequest(BaseModel):
    sha1_prefix: str = Field(min_length=5, max_length=5, pattern=r"^[A-Fa-f0-9]{5}$")
    sha1_suffix: str = Field(min_length=35, max_length=35, pattern=r"^[A-Fa-f0-9]{35}$")
    password_length: int = Field(ge=1, le=256)
    has_uppercase: bool = False
    has_lowercase: bool = False
    has_digit: bool = False
    has_symbol: bool = False
    zxcvbn_score: int = Field(ge=0, le=4)


class CheckPasswordResponse(BaseModel):
    status: PasswordStatus
    score: int = Field(ge=0, le=4)
    failed_rules: list[str]
    suggestion: str


class AnalyzePasswordRequest(BaseModel):
    password: str


class AnalyzePasswordResponse(BaseModel):
    entropy_bits: float
    zxcvbn_score: int = Field(ge=0, le=4)
    strength_label: str
    crack_time_display: str
    patterns_detected: list[str]
    recommendations: list[str]
    policy_violations: list[str]


class BreachCheckRequest(BaseModel):
    password: str = Field(min_length=1, max_length=128)


class BreachCheckResponse(BaseModel):
    is_breached: bool | None
    breach_count: int = Field(ge=0)
    cache_hit: bool
    error: str | None = None


class ScorePasswordRequest(BaseModel):
    password: str = Field(min_length=1, max_length=128)


class ScorePasswordResponse(BaseModel):
    service_id: str
    score: int = Field(ge=0, le=100)
    risk_label: str
    strength_label: str
    entropy_bits: float
    zxcvbn_score: int = Field(ge=0, le=4)
    crack_time_display: str
    is_breached: bool | None
    breach_count: int = Field(ge=0)
    patterns_detected: list[str]
    recommendations: list[str]
    policy_violations: list[str]
    cache_hit: bool


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class AdminLoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=128)


class AdminRegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    created_at: datetime


class PolicyUpdateRequest(BaseModel):
    service_id: str = Field(default="default", min_length=1, max_length=128)
    value: dict[str, Any]


class PolicyRowResponse(BaseModel):
    service_id: str
    name: str
    value: Any
    description: str | None = None
    updated_by: UUID | None = None
    updated_at: datetime


class AuditLogRowResponse(BaseModel):
    id: UUID
    user_id: UUID | None = None
    action: str | None = None
    ip_address: str | None = None
    metadata: dict[str, Any] | None = None
    created_at: datetime


class AuditLogListResponse(BaseModel):
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total: int = Field(ge=0)
    items: list[AuditLogRowResponse]
