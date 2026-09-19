from datetime import datetime, timedelta, timezone
from typing import Annotated
import uuid
import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user
from src.core.config import settings
from src.core.database import get_db_session
from src.models.entities import User
from src.schemas.auth import LoginRequest, RegisterRequest, SignupRequest, TokenResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["Auth"])


def _create_token(user_id: uuid.UUID, token_type: str, expires: timedelta) -> str:
    return jwt.encode(
        {"sub": str(user_id), "type": token_type, "exp": datetime.now(timezone.utc) + expires},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str | None = None) -> None:
    """[Section 9.1] 명세서 규격 쿠키 보안 정책 강제 적용:
    - access_token: Max-Age 900초(15분), HttpOnly=True, SameSite=Strict, Path=/
    - refresh_token: Max-Age 604800초(7일), HttpOnly=True, SameSite=Strict, Path=/api/v1/auth
    - 하위 호환성을 위해 설정된 AUTH_COOKIE_NAME / AUTH_REFRESH_COOKIE_NAME 및 표준 쿠키명을 모두 주입합니다.
    """
    cookie_keys = {settings.AUTH_COOKIE_NAME, "access_token"}
    for key in cookie_keys:
        response.set_cookie(
            key=key,
            value=access_token,
            max_age=900,
            httponly=True,
            secure=settings.AUTH_COOKIE_SECURE,
            samesite="strict",
            path="/",
        )
    if refresh_token is not None:
        refresh_cookie_keys = {settings.AUTH_REFRESH_COOKIE_NAME, "refresh_token"}
        for key in refresh_cookie_keys:
            response.set_cookie(
                key=key,
                value=refresh_token,
                max_age=604800,
                httponly=True,
                secure=settings.AUTH_COOKIE_SECURE,
                samesite="strict",
                path="/api/v1/auth",
            )


def _check_already_authenticated(request: Request | None) -> None:
    """[Section 9.3] 기로그인 사용자(인증 쿠키 또는 유효 토큰 보유) 접근 시 403 Forbidden (ALREADY_AUTHENTICATED) 반환."""
    if request is None:
        return

    # 1. 인증 쿠키 확인
    auth_cookie = request.cookies.get(settings.AUTH_COOKIE_NAME) or request.cookies.get("access_token")
    if auth_cookie and auth_cookie.strip():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="ALREADY_AUTHENTICATED",
        )

    # 2. 유효 토큰(Authorization 헤더) 확인
    auth_header = request.headers.get("authorization")
    if auth_header:
        token = auth_header[7:].strip() if auth_header.lower().startswith("bearer ") else auth_header.strip()
        if token:
            try:
                payload = jwt.decode(
                    token,
                    settings.JWT_SECRET_KEY,
                    algorithms=[settings.JWT_ALGORITHM],
                    options={"require_exp": True, "require_sub": True},
                )
                if payload.get("type") != "refresh":
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="ALREADY_AUTHENTICATED",
                    )
            except HTTPException:
                raise
            except (JWTError, ValueError, KeyError, TypeError):
                pass


@router.post(
    "/signup",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="신규 사용자 회원가입 (FR-008 & Section 8.1)",
)
async def signup(
    payload: SignupRequest,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    request: Request,
) -> UserResponse:
    # Ref: [Section 9.3] 기로그인 사용자 접근 가드 (403 Forbidden)
    _check_already_authenticated(request)

    # Ref: [FR-008] 이메일 중복 확인 (409 Conflict)
    stmt = select(User).where(User.email == payload.email)
    existing_user = (await db.execute(stmt)).scalar_one_or_none()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 등록된 이메일 주소입니다.",
        )

    # Ref: [FR-008] bcrypt(Cost: 12) 비밀번호 단방향 해싱 및 계정 생성
    salt = bcrypt.gensalt(rounds=12)
    hashed_password = bcrypt.hashpw(payload.password.encode("utf-8"), salt).decode("utf-8")

    new_user = User(
        id=uuid.uuid4(),
        email=payload.email,
        hashed_password=hashed_password,
        name=payload.name or payload.email.split("@", 1)[0][:100],
        role="USER",
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # Ref: [FR-008 & Section 9.1] 가입 성공 시 즉시 인증 토큰 발급 및 보안 쿠키 설정
    access_token = _create_token(
        new_user.id, "access", timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    refresh_token = _create_token(
        new_user.id, "refresh", timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    _set_auth_cookies(response, access_token, refresh_token)

    return UserResponse(
        id=new_user.id,
        email=new_user.email,
        name=new_user.name,
        role=new_user.role,
        createdAt=new_user.created_at or datetime.now(timezone.utc),
    )


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="신규 사용자 회원가입 (하위 호환용 엔드포인트)",
)
async def register(
    payload: RegisterRequest,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    request: Request,
) -> UserResponse:
    # Ref: [FR-008] 기존 /register 호출을 표준 /signup 로직으로 위임
    return await signup(payload=payload, response=response, db=db, request=request)


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="사용자 로그인 (FR-008 & Section 8.1, 9.1)",
)
async def login(
    payload: LoginRequest,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    request: Request,
) -> TokenResponse:
    # Ref: [Section 9.3] 기로그인 사용자 접근 가드 (403 Forbidden)
    _check_already_authenticated(request)

    user = (await db.execute(select(User).where(User.email == payload.email))).scalar_one_or_none()
    valid = False
    if user:
        try:
            valid = bcrypt.checkpw(payload.password.encode(), user.hashed_password.encode())
        except ValueError:
            pass
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다.",
        )
    access_token = _create_token(
        user.id, "access", timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    refresh_token = _create_token(
        user.id, "refresh", timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    _set_auth_cookies(response, access_token, refresh_token)
    return {"accessToken": access_token, "tokenType": "bearer"}


@router.post("/refresh", response_model=TokenResponse, summary="인증 토큰 갱신 (Section 9.1, 9.2)")
async def refresh(request: Request, response: Response) -> TokenResponse:
    # Ref: [Section 9.1] 'refresh_token' 및 'volumeal_refresh' 모두 조회
    token = request.cookies.get("refresh_token") or request.cookies.get(settings.AUTH_REFRESH_COOKIE_NAME)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "세션을 갱신할 수 없습니다.")
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM],
            options={"require_exp": True, "require_sub": True},
        )
        if payload.get("type") != "refresh":
            raise JWTError("invalid token type")
        user_id = uuid.UUID(payload["sub"])
    except (JWTError, ValueError, KeyError, TypeError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "세션을 갱신할 수 없습니다.")
    access_token = _create_token(
        user_id, "access", timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    _set_auth_cookies(response, access_token)
    return {"accessToken": access_token, "tokenType": "bearer"}


@router.post("/logout", status_code=204, summary="사용자 로그아웃 (Section 8.1, 9.1)")
async def logout(
    response: Response,
    _: Annotated[User, Depends(get_current_user)],
):
    # Ref: [Section 9.1] 발급된 모든 인증 쿠키 안전 삭제
    for key in {settings.AUTH_COOKIE_NAME, "access_token"}:
        response.delete_cookie(key=key, path="/")
    for key in {settings.AUTH_REFRESH_COOKIE_NAME, "refresh_token"}:
        response.delete_cookie(key=key, path="/api/v1/auth")


@router.get(
    "/me",
    response_model=UserResponse,
    summary="현재 로그인한 사용자 정보 조회 (Section 8.1, 9.1)",
)
async def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserResponse:
    # Ref: [Section 8.1, 9.1] 인증된 사용자의 프로필 DTO 반환
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        role=current_user.role,
        createdAt=current_user.created_at or datetime.now(timezone.utc),
    )
