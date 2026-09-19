"""[Section 3.1, 10.3, 11.2] 비전 추론 파이프라인 P95 SLA 벤치마크 스크립트.

- 명세서 규격: 추론 SLA P95 <= 1,500ms (1.5초)
- 호출 대상: POST /api/v1/vision/estimate (10회 연속 비동기 호출)
- 측정 도구: httpx.AsyncClient (ASGITransport 기반 네트워크 I/O 격리 측정)
"""
import asyncio
import io
import os
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx
import numpy as np
from PIL import Image
from jose import jwt

from src.main import app
from src.core.config import settings
from src.api.deps import get_current_user
from src.core.rate_limiter import rate_limit_estimate
from src.models.entities import User
from src.services.storage_service import StorageService


from unittest.mock import AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database import get_db_session


def make_test_jwt(user_id: uuid.UUID) -> str:
    """테스트용 JWT Access Token 생성."""
    expires = datetime.now(timezone.utc) + timedelta(minutes=60)
    return jwt.encode(
        {"sub": str(user_id), "type": "access", "exp": expires},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def load_benchmark_image() -> Tuple[str, bytes]:
    """실제 음식 이미지 바이너리 우선 로드, 부재 시 더미 이미지 생성."""
    candidate_paths = [
        Path(__file__).resolve().parents[1] / "data" / "real_food" / "images" / "test" / "RF_apple_0801.jpg",
        Path(__file__).resolve().parents[2] / "frontend" / "tests" / "fixtures" / "real_apple.jpg",
        Path(__file__).resolve().parents[2] / "frontend" / "tests" / "fixtures" / "meal.jpg",
    ]
    for cp in candidate_paths:
        if cp.is_file():
            return cp.name, cp.read_bytes()
    buffer = io.BytesIO()
    image = Image.new("RGB", (64, 64), color="red")
    image.save(buffer, format="JPEG")
    return "dummy_red.jpg", buffer.getvalue()


async def run_benchmark(
    num_requests: int = 10,
    sla_target_ms: float = 1500.0,
    use_mock: bool = False,
    live_url: Optional[str] = None,
) -> Tuple[List[float], List[bool], List[dict]]:
    """POST /api/v1/vision/estimate 엔드포인트를 num_requests회 연속 호출하고 메트릭을 수집."""
    user_id = uuid.UUID("a0000000-0000-0000-0000-000000000002")
    mock_user = User(
        id=user_id,
        email="benchmark@volumeal.io",
        name="벤치마크사용자",
        role="USER",
        hashed_password="hashed_pw",
    )

    # 1. 벤치마크 환경 세팅: 인증, Rate Limiter, DB 세션 오버라이드
    if not live_url:
        fake_db = AsyncMock(spec=AsyncSession)
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[rate_limit_estimate] = lambda: None
        app.dependency_overrides[get_db_session] = lambda: fake_db

    # Redis 키 초기화 (안전망)
    r = None
    try:
        import redis
        r = redis.Redis(host="localhost", port=6379)
        r.delete(f"rate_limit:{user_id}")
    except Exception:
        pass

    token = make_test_jwt(user_id)
    cookies = {
        settings.AUTH_COOKIE_NAME: token,
        "access_token": token,
    }
    headers = {
        "Authorization": f"Bearer {token}",
    }
    if use_mock:
        headers["X-Test-Force-Fail"] = "BENCHMARK"

    img_name, image_bytes = load_benchmark_image()
    latencies: List[float] = []
    success_flags: List[bool] = []
    detailed_results: List[dict] = []
    created_files: List[str] = []

    storage = StorageService()

    print("=" * 72, flush=True)
    print(f" [VoluMeal-Align] 비전 파이프라인 벤치마크 시작 (총 {num_requests}회 호출)", flush=True)
    print(f" - 엔드포인트 : POST /api/v1/vision/estimate", flush=True)
    print(f" - 대상 SLA   : P95 <= {sla_target_ms:,.1f} ms [명세서 Section 3.1]", flush=True)
    client_type = f"Live Server ({live_url})" if live_url else "httpx.AsyncClient with ASGITransport"
    print(f" - 클라이언트 : {client_type}", flush=True)
    print("=" * 72, flush=True)
    print(f"{'회차':>4} | {'상태 코드':>9} | {'성공':>4} | {'클라이언트 지연(ms)':>18} | {'서버 내부 추론(ms)':>18}", flush=True)
    print("-" * 72, flush=True)

    client_ctx = httpx.AsyncClient(base_url=live_url, cookies=cookies) if live_url else httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://benchmark.local", cookies=cookies)
    async with client_ctx as client:
        for seq in range(1, num_requests + 1):
            if r is not None:
                try:
                    r.delete(f"rate_limit:{user_id}")
                except Exception:
                    pass
            start_time = time.perf_counter()
            try:
                response = await client.post(
                    "/api/v1/vision/estimate",
                    files={"file": (f"benchmark_{seq}.jpg", image_bytes, "image/jpeg")},
                    data={
                        "focal_length_mm": 26.0,
                        "is_calibrated": "false",
                        "conf_threshold": 0.05,
                    },
                    headers=headers,
                )
                elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                status_code = response.status_code
                is_success = (status_code == 200)

                server_internal_ms = "-"
                if is_success:
                    data = response.json().get("data", {})
                    server_internal_ms = f"{data.get('inferenceLatencyMs', 0):.1f}"
                    img_url = data.get("imageUrl", "")
                    if img_url:
                        fname = os.path.basename(img_url)
                        fpath = os.path.join(str(storage.meals_dir), fname)
                        created_files.append(fpath)

                latencies.append(elapsed_ms)
                success_flags.append(is_success)
                detailed_results.append({
                    "seq": seq,
                    "status_code": status_code,
                    "success": is_success,
                    "latency_ms": elapsed_ms,
                    "server_ms": server_internal_ms,
                })

                success_mark = "OK" if is_success else "FAIL"
                print(f"{seq:>4} | {status_code:>9} | {success_mark:>4} | {elapsed_ms:>18.2f} | {server_internal_ms:>18}", flush=True)
                if not is_success and seq == 1:
                    print(f" [1회차 오류 상세] {response.text}", flush=True)

            except Exception as exc:
                elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                latencies.append(elapsed_ms)
                success_flags.append(False)
                detailed_results.append({
                    "seq": seq,
                    "status_code": 500,
                    "success": False,
                    "latency_ms": elapsed_ms,
                    "server_ms": f"ERR: {exc}",
                })
                print(f"{seq:>4} | {'ERR':>9} | {'FAIL':>4} | {elapsed_ms:>18.2f} | {str(exc)[:18]:>18}", flush=True)

    # 2. 리소스 정리
    app.dependency_overrides.clear()
    for fp in created_files:
        if os.path.exists(fp):
            try:
                os.unlink(fp)
            except OSError:
                pass

    return latencies, success_flags, detailed_results


def print_summary_and_evaluate(latencies: List[float], success_flags: List[bool], sla_target_ms: float = 1500.0) -> bool:
    """P50, P90, P95 지표 산출 및 SLA 충족 여부 판정 콘솔 출력."""
    total = len(latencies)
    success_count = sum(1 for s in success_flags if s)
    failure_count = total - success_count

    p50 = float(np.percentile(latencies, 50))
    p90 = float(np.percentile(latencies, 90))
    p95 = float(np.percentile(latencies, 95))
    min_lat = float(np.min(latencies))
    max_lat = float(np.max(latencies))
    mean_lat = float(np.mean(latencies))

    is_sla_passed = (p95 <= sla_target_ms) and (failure_count == 0)

    print("=" * 72, flush=True)
    print(" [벤치마크 통계 요약 (Latency Metrics)]", flush=True)
    print(f" - 총 요청 건수     : {total} 회", flush=True)
    print(f" - 성공 / 실패      : {success_count} 회 성공 / {failure_count} 회 실패", flush=True)
    print(f" - 최소 응답 시간   : {min_lat:8.2f} ms", flush=True)
    print(f" - 최대 응답 시간   : {max_lat:8.2f} ms", flush=True)
    print(f" - 평균 응답 시간   : {mean_lat:8.2f} ms", flush=True)
    print(f" - P50 (중앙값)     : {p50:8.2f} ms", flush=True)
    print(f" - P90              : {p90:8.2f} ms", flush=True)
    print(f" - P95              : {p95:8.2f} ms (SLA 기준: <= {sla_target_ms:,.1f} ms)", flush=True)
    print("-" * 72, flush=True)

    if is_sla_passed:
        print(f" >>> [SLA 판정 결과: PASS] <<<", flush=True)
        print(f" P95 ({p95:.2f} ms)가 목표치({sla_target_ms:.1f} ms)를 충족합니다. (명세서 Section 3.1 부합)", flush=True)
    else:
        print(f" >>> [SLA 판정 결과: FAIL] <<<", flush=True)
        if p95 > sla_target_ms:
            print(f" P95 ({p95:.2f} ms)가 목표치({sla_target_ms:.1f} ms)를 초과하였습니다.", flush=True)
        if failure_count > 0:
            print(f" {failure_count}건의 요청 실패가 발생하였습니다.", flush=True)
    print("=" * 72, flush=True)

    return is_sla_passed


def main():
    import argparse
    parser = argparse.ArgumentParser(description="비전 파이프라인 P95 SLA 벤치마크")
    parser.add_argument("--runs", type=int, default=10, help="호출 횟수 (기본 10)")
    parser.add_argument("--sla", type=float, default=1500.0, help="SLA P95 상한치 ms (기본 1500.0)")
    parser.add_argument("--mock", action="store_true", help="모의(Mock) 워커 결과 사용")
    parser.add_argument("--live", type=str, default=None, help="실제 서버 베이스 URL (예: http://127.0.0.1:8001)")
    args = parser.parse_args()

    latencies, success_flags, _ = asyncio.run(
        run_benchmark(
            num_requests=args.runs,
            sla_target_ms=args.sla,
            use_mock=args.mock,
            live_url=args.live,
        )
    )
    passed = print_summary_and_evaluate(latencies, success_flags, sla_target_ms=args.sla)
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
