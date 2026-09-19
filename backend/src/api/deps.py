import uuid
from typing import Annotated
from fastapi import Cookie, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.config import settings
from src.core.database import get_db_session
from src.models.entities import User

bearer = HTTPBearer(auto_error=False)

async def get_current_user(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    auth_cookie: Annotated[str | None, Cookie(alias=settings.AUTH_COOKIE_NAME)] = None,
    access_token_cookie: Annotated[str | None, Cookie(alias="access_token")] = None,
) -> User:
    # Ref: [Section 9.1] Bearer 헤더, 표준 'access_token' 쿠키, 레거시 쿠키 순으로 토큰 검사
    token = (credentials.credentials if credentials else None) or access_token_cookie or auth_cookie

    if token is None:
        if settings.ENV == "development" and settings.DEV_AUTH_BYPASS:
            user_id = uuid.UUID("a0000000-0000-0000-0000-000000000002")
        else:
            raise HTTPException(401, "로그인이 필요합니다.", headers={"WWW-Authenticate": "Bearer"})
    else:
        try:
            payload = jwt.decode(token, settings.JWT_SECRET_KEY,
                                 algorithms=[settings.JWT_ALGORITHM], options={"require_exp": True, "require_sub": True})
            if payload.get("type") == "refresh":
                raise JWTError("refresh token cannot authorize API requests")
            user_id = uuid.UUID(payload["sub"])
        except (JWTError, ValueError, KeyError, TypeError):
            raise HTTPException(401, "로그인이 만료되었거나 유효하지 않습니다.", headers={"WWW-Authenticate": "Bearer"})
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(401, "사용자 계정을 찾을 수 없습니다.")
    return user
