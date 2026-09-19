import datetime
import uuid
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    # Ref: [FR-008] 신규 사용자 계정 등록 DTO
    email: EmailStr = Field(..., max_length=255, description="사용자 이메일 주소")
    password: str = Field(..., min_length=8, max_length=72, description="비밀번호 (최소 8자)")
    name: str | None = Field(default=None, min_length=1, max_length=100, description="사용자 실명 또는 닉네임")


SignupRequest = RegisterRequest


class LoginRequest(BaseModel):
    # Ref: [FR-007] 사용자 로그인 DTO
    email: str = Field(..., min_length=1, max_length=255, description="사용자 이메일 주소")
    password: str = Field(..., min_length=1, max_length=72, description="비밀번호")


class UserResponse(BaseModel):
    # Ref: [FR-007] 사용자 프로필 응답 DTO
    id: uuid.UUID
    email: str
    name: str
    role: str
    createdAt: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    # Ref: [FR-007] 인증 토큰 응답 DTO
    accessToken: str
    tokenType: str = "bearer"

    model_config = ConfigDict(from_attributes=True)
