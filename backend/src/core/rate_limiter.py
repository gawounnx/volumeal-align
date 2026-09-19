"""Redis 기반 슬라이딩 윈도우 Rate Limiter 구현 [Section 10.2, 14.2]."""
import logging
import time
from typing import Annotated, Any, Optional
from fastapi import Depends, HTTPException, status

from src.api.deps import get_current_user
from src.core.config import settings
from src.core.exceptions import AppException, RateLimitException
from src.models.entities import User

logger = logging.getLogger(__name__)

try:
    import redis.asyncio as aioredis
except ImportError:
    aioredis = None

_redis_pool: Optional[Any] = None


def get_redis_pool():
    global _redis_pool
    if _redis_pool is None and aioredis is not None:
        redis_url = getattr(settings, "REDIS_URL", None) or "redis://localhost:6379/0"
        _redis_pool = aioredis.ConnectionPool.from_url(
            redis_url,
            decode_responses=True,
            max_connections=20,
        )
    return _redis_pool


async def get_redis_client():
    """FastAPI Depends용 비동기 Redis 클라이언트 의존성 제공."""
    pool = get_redis_pool()
    if pool is not None and aioredis is not None:
        return aioredis.Redis(connection_pool=pool)
    return None


async def check_rate_limit(
    redis_client: Any,
    user_id: str,
    limit: int = 5,
    window_sec: int = 60,
) -> None:
    """[Section 14.2] Redis Sliding Window 알고리즘 기반 요청 속도 제한 검증."""
    if redis_client is None:
        return

    now = time.time()
    key = f"rate_limit:{user_id}"

    try:
        async with redis_client.pipeline(transaction=True) as pipe:
            pipe.zremrangebyscore(key, 0, now - window_sec)
            pipe.zadd(key, {str(now): now})
            pipe.zcard(key)
            pipe.expire(key, window_sec)
            results = await pipe.execute()

        current_count = results[2]
        if current_count > limit:
            raise RateLimitException(f"분당 API 호출 한도({limit}회)를 초과했습니다. 잠시 후 다시 시도해 주세요.")
    except RateLimitException:
        raise
    except AppException:
        raise
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("Redis rate limit check encountered an error (%s), bypassing throttle.", exc)


async def rate_limit_estimate(
    current_user: Annotated[User, Depends(get_current_user)],
    redis_client: Annotated[Any, Depends(get_redis_client)],
) -> None:
    """[Section 14.2] vision estimate 전용 분당 5회 슬라이딩 윈도우 Rate Limiter 의존성."""
    await check_rate_limit(
        redis_client=redis_client,
        user_id=str(current_user.id),
        limit=5,
        window_sec=60,
    )
