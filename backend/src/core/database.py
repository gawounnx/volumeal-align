from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from src.core.config import settings

# 비동기 커넥션 풀 엔진 생성
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# 비동기 세션 팩토리
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """SQLAlchemy 2.0 공통 베이스 클래스"""
    pass


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 라우터 의존성 주입용 비동기 세션 제너레이터"""
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# FastAPI Depends 의존성 주입 호환성을 위한 심볼릭 별칭 (SSOT 유지)
get_db = get_db_session