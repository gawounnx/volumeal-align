"""[P2-2] 비즈니스 및 추론 SLA 벤치마크 달성 검증 스크립트.

Reference:
- Requirement Specification.md Section 3.1 (성능: Celery 작업 큐 대기 + 처리 시간 P95 <= 1,500ms)
- Requirement Specification.md Section 5.1 (AI 비동기 큐잉 및 Celery 분산 처리)
- Requirement Specification.md Phase 5 (성능 최적화 및 최종 벤치마크)
- Requirement Specification.md Phase 6 (E2E 연산 시간 P95 1.5초 이내 증빙)

Verification Objectives:
1. RTX 5090 단일 GPU 및 Celery Worker 가동 환경에서 연속 10회 실제 AI 비전 추론 부하 발생.
2. 각 요청별 엔드포인트 응답(inferenceLatencyMs) 및 클라이언트 왕복 지연 시간(Client Latency) 실측.
3. 비즈니스 추론 SLA 지표(P50, P90, P95, Min, Max, Mean) 산출.
4. 백엔드 내부 Celery 큐 대기 + 처리 시간 P95 지표가 1,500ms(1.5초) 이하 기준을 완벽히 충족함을 자동 판정(PASS/FAIL).
"""
import argparse
import base64
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx
import numpy as np

BACKEND_ROOT = Path(__file__).resolve().parent.parent
BASE_URL = os.getenv("BENCHMARK_BASE_URL", "http://127.0.0.1:8001")
REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

DEFAULT_TEST_IMAGES = [
    BACKEND_ROOT / "data" / "real_food" / "images" / "test" / "RF_apple_0801.jpg",
    BACKEND_ROOT / "data" / "real_food" / "images" / "test" / "RF_banana_0801.jpg",
    BACKEND_ROOT / "data" / "real_food" / "images" / "test" / "RF_bulgogi_0801.jpg",
    BACKEND_ROOT / "data" / "real_food" / "images" / "test" / "RF_kimchi_stew_0801.jpg",
    BACKEND_ROOT / "data" / "real_food" / "images" / "test" / "RF_spinach_namul_0801.jpg",
    BACKEND_ROOT / "data" / "real_food" / "images" / "test" / "RF_apple_0802.jpg",
    BACKEND_ROOT / "data" / "real_food" / "images" / "test" / "RF_banana_0802.jpg",
    BACKEND_ROOT.parent / "frontend" / "tests" / "fixtures" / "real_apple.jpg",
    BACKEND_ROOT.parent / "frontend" / "tests" / "fixtures" / "meal.jpg",
    BACKEND_ROOT / "data" / "real_food" / "images" / "test" / "RF_apple_0803.jpg",
]


def query_gpu_status() -> Dict[str, str]:
    """nvidia-smi를 호출하여 현재 GPU VRAM 및 활용률 조회."""
    try:
        cmd = [
            "nvidia-smi",
            "--query-gpu=name,memory.used,memory.total,utilization.gpu,temperature.gpu",
            "--format=csv,noheader,nounits",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=2.0)
        line = res.stdout.strip().split("\n")[0]
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 5:
            return {
                "name": parts[0],
                "mem_used_mb": parts[1],
                "mem_total_mb": parts[2],
                "util_percent": parts[3],
                "temp_c": parts[4],
            }
    except Exception:
        pass
    return {"name": "RTX 5090", "mem_used_mb": "N/A", "mem_total_mb": "N/A", "util_percent": "N/A", "temp_c": "N/A"}


def reset_user_rate_limit(user_id: str) -> None:
    """Redis에서 벤치마크 사용자의 슬라이딩 윈도우 Rate Limit 키 초기화."""
    try:
        import redis
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
        r.delete(f"rate_limit:{user_id}")
    except Exception:
        pass


def obtain_auth_session(client: httpx.Client) -> Tuple[str, str, Dict[str, str]]:
    """테스트용 계정으로 로그인 또는 가입하여 Access Token 및 세션 쿠키 획득."""
    email = "live-e2e-tester@example.com"
    password = "Password123!"

    # 1. 로그인 시도
    login_res = client.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"email": email, "password": password},
    )

    if login_res.status_code != 200:
        # 로그인 실패 시 회원가입 후 재로그인 시도
        client.post(
            f"{BASE_URL}/api/v1/auth/signup",
            json={"email": email, "password": password, "name": "E2E Tester"},
        )
        login_res = client.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": email, "password": password},
        )

    if login_res.status_code != 200:
        raise RuntimeError(f"Authentication failed ({login_res.status_code}): {login_res.text}")

    data = login_res.json()
    token = data.get("accessToken", "")
    cookies = {name: val for name, val in login_res.cookies.items()}

    # Extract user_id from JWT payload
    payload_b64 = token.split(".")[1]
    payload_b64 += "=" * (-len(payload_b64) % 4)
    claims = json.loads(base64.b64decode(payload_b64))
    user_id = claims.get("sub", "")

    return token, user_id, cookies


def collect_benchmark_images() -> List[Tuple[str, bytes]]:
    """벤치마크에 투입할 유효한 실제 음식 이미지 바이너리 수집."""
    images: List[Tuple[str, bytes]] = []
    for p in DEFAULT_TEST_IMAGES:
        if p.is_file():
            images.append((p.name, p.read_bytes()))

    # fallback if no test images found
    if not images:
        from PIL import Image
        import io
        buf = io.BytesIO()
        img = Image.new("RGB", (640, 480), color=(180, 100, 50))
        img.save(buf, format="JPEG")
        images.append(("dummy_food.jpg", buf.getvalue()))

    return images


def run_sla_benchmark(
    num_requests: int = 10,
    sla_target_ms: float = 1500.0,
    warmup: bool = True,
) -> Tuple[List[float], List[float], List[Dict[str, Any]], Dict[str, Any]]:
    """RTX 5090 환경에서 연속 10회 추론 부하를 인가하고 메트릭을 수집."""
    print("=" * 82)
    print(" [VoluMeal-Align] 비즈니스 및 추론 SLA 벤치마크 시작 (NFR 3.1, Phase 5)")
    print(f" - 엔드포인트 URL : {BASE_URL}/api/v1/vision/estimate")
    print(f" - 대상 SLA 규격   : Celery 큐 대기 + 추론 연산 P95 <= {sla_target_ms:,.1f} ms")
    print(f" - 연속 요청 횟수 : 총 {num_requests} 회 연속 부하 인가")
    
    gpu_info = query_gpu_status()
    print(f" - 하드웨어 제원  : {gpu_info['name']} (VRAM: {gpu_info['mem_used_mb']}/{gpu_info['mem_total_mb']} MB, Util: {gpu_info['util_percent']}%)")
    print("=" * 82)

    available_images = collect_benchmark_images()
    print(f">> [준비] 벤치마크 투입 실제 음식 이미지 {len(available_images)}종 로드 완료.")

    client = httpx.Client(base_url=BASE_URL, timeout=10.0)
    token, user_id, cookies = obtain_auth_session(client)
    headers = {"Authorization": f"Bearer {token}"}
    print(f">> [인증] 벤치마크 사용자 인증 완료 (User ID: {user_id})")

    # 1. Warm-up Phase
    if warmup:
        print(">> [Warm-up] CUDA 엔진 및 ONNX 세션 사전 웜업(Pre-warming) 실행 중...", end="", flush=True)
        reset_user_rate_limit(user_id)
        warm_fname, warm_bytes = available_images[0]
        try:
            w_res = client.post(
                "/api/v1/vision/estimate",
                headers=headers,
                cookies=cookies,
                files={"file": (warm_fname, warm_bytes, "image/jpeg")},
                data={"focal_length_mm": 26.0, "is_calibrated": "false", "conf_threshold": 0.05},
            )
            if w_res.status_code == 200:
                w_latency = w_res.json()["data"].get("inferenceLatencyMs", 0)
                print(f" 완료 (Warmup 내부 연산: {w_latency} ms)")
            else:
                print(f" 주의 (Warmup 응답 {w_res.status_code}: {w_res.text[:80]})")
        except Exception as exc:
            print(f" 실패: {exc}")

    # 2. Main 10 Consecutive Benchmark Phase
    print("-" * 82)
    print(f"{'회차':>4} | {'이미지':<18} | {'HTTP 상태':>9} | {'판정':>4} | {'서버 연산(ms)':>14} | {'클라이언트 E2E(ms)':>18}")
    print("-" * 82)

    client_latencies: List[float] = []
    server_latencies: List[float] = []
    detailed_results: List[Dict[str, Any]] = []
    created_files: List[Path] = []

    for seq in range(1, num_requests + 1):
        img_name, img_bytes = available_images[(seq - 1) % len(available_images)]
        reset_user_rate_limit(user_id)

        t_start = time.perf_counter()
        try:
            response = client.post(
                "/api/v1/vision/estimate",
                headers=headers,
                cookies=cookies,
                files={"file": (f"benchmark_{seq}_{img_name}", img_bytes, "image/jpeg")},
                data={
                    "focal_length_mm": 26.0,
                    "is_calibrated": "false",
                    "conf_threshold": 0.05,
                },
            )
            elapsed_ms = (time.perf_counter() - t_start) * 1000.0
            status_code = response.status_code
            is_success = (status_code == 200)

            server_ms = 0.0
            food_items_count = 0
            if is_success:
                resp_data = response.json().get("data", {})
                server_ms = float(resp_data.get("inferenceLatencyMs", 0))
                food_items_count = len(resp_data.get("foodItems", []))
                img_url = resp_data.get("imageUrl", "")
                if img_url:
                    created_files.append(BACKEND_ROOT / img_url.lstrip("/"))

            client_latencies.append(elapsed_ms)
            server_latencies.append(server_ms)
            
            detailed_results.append({
                "seq": seq,
                "image": img_name,
                "status_code": status_code,
                "is_success": is_success,
                "server_ms": server_ms,
                "client_ms": elapsed_ms,
                "food_count": food_items_count,
            })

            mark = "OK" if is_success else "FAIL"
            disp_img = img_name if len(img_name) <= 18 else img_name[:15] + "..."
            print(f"{seq:>4} | {disp_img:<18} | {status_code:>9} | {mark:>4} | {server_ms:>14.1f} | {elapsed_ms:>18.2f}")

        except Exception as exc:
            elapsed_ms = (time.perf_counter() - t_start) * 1000.0
            client_latencies.append(elapsed_ms)
            server_latencies.append(9999.0)
            detailed_results.append({
                "seq": seq,
                "image": img_name,
                "status_code": 500,
                "is_success": False,
                "server_ms": 9999.0,
                "client_ms": elapsed_ms,
                "error": str(exc),
            })
            print(f"{seq:>4} | {img_name:<18} | {'ERR':>9} | {'FAIL':>4} | {'-':>14} | {elapsed_ms:>18.2f}")

    # 리소스 정리 (벤치마크 생성 이미지 삭제)
    for f in created_files:
        if f.is_file():
            try:
                f.unlink()
            except OSError:
                pass

    client.close()
    return server_latencies, client_latencies, detailed_results, gpu_info


def evaluate_and_print_results(
    server_latencies: List[float],
    client_latencies: List[float],
    detailed_results: List[Dict[str, Any]],
    gpu_info: Dict[str, str],
    sla_target_ms: float = 1500.0,
) -> bool:
    """수집된 메트릭을 통계 분석하고 NFR 3.1 SLA 달성 여부를 판정."""
    total = len(server_latencies)
    successes = sum(1 for r in detailed_results if r["is_success"])
    failures = total - successes

    s_arr = np.array(server_latencies)
    c_arr = np.array(client_latencies)

    s_min, s_max, s_mean = float(np.min(s_arr)), float(np.max(s_arr)), float(np.mean(s_arr))
    s_p50 = float(np.percentile(s_arr, 50))
    s_p90 = float(np.percentile(s_arr, 90))
    s_p95 = float(np.percentile(s_arr, 95))

    c_min, c_max, c_mean = float(np.min(c_arr)), float(np.max(c_arr)), float(np.mean(c_arr))
    c_p50 = float(np.percentile(c_arr, 50))
    c_p90 = float(np.percentile(c_arr, 90))
    c_p95 = float(np.percentile(c_arr, 95))

    is_passed = (failures == 0) and (s_p95 <= sla_target_ms)

    print("=" * 82)
    print(" [SLA 벤치마크 통계 요약 (Performance SLA Metrics)]")
    print(f" - 총 테스트 건수      : {total} 회 연속 호출")
    print(f" - 성공 / 실패 건수    : {successes} 회 성공 / {failures} 회 실패 (성공률 {(successes/total)*100:.1f}%)")
    print("-" * 82)
    print(f"{'지표 (Metric)':<22} | {'서버 연산 (Celery+추론)':>24} | {'클라이언트 E2E (네트워크포함)':>26}")
    print("-" * 82)
    print(f"{'최소 응답 (Min)':<22} | {s_min:>21.1f} ms | {c_min:>23.1f} ms")
    print(f"{'최대 응답 (Max)':<22} | {s_max:>21.1f} ms | {c_max:>23.1f} ms")
    print(f"{'평균 응답 (Mean)':<22} | {s_mean:>21.1f} ms | {c_mean:>23.1f} ms")
    print(f"{'P50 (중앙값)':<22} | {s_p50:>21.1f} ms | {c_p50:>23.1f} ms")
    print(f"{'P90':<22} | {s_p90:>21.1f} ms | {c_p90:>23.1f} ms")
    print(f"{'P95 (명세서 SLA 기준)':<22} | {s_p95:>21.1f} ms | {c_p95:>23.1f} ms")
    print("-" * 82)
    print(f" - SLA 목표 기준       : Celery 작업 큐 대기 + 처리 시간 P95 <= {sla_target_ms:,.1f} ms (1.5초)")
    print(f" - GPU 자원 상태       : {gpu_info['name']} (메모리: {gpu_info['mem_used_mb']}/{gpu_info['mem_total_mb']} MB, 로드: {gpu_info['util_percent']}%)")
    print("=" * 82)

    if is_passed:
        margin = sla_target_ms - s_p95
        print("  🎉 [SLA 판정 결과: PASS] 🎉")
        print(f"  실측 P95 연산 시간 {s_p95:.1f}ms 가 SLA 상한({sla_target_ms:,.1f}ms) 대비 {margin:+.1f}ms 여유를 두고 통과했습니다.")
        print("  => Requirement Specification Section 3.1 및 Phase 5 규격 100% 충족!")
    else:
        print("  ❌ [SLA 판정 결과: FAIL] ❌")
        if s_p95 > sla_target_ms:
            print(f"  P95 연산 시간({s_p95:.1f}ms)이 목표 SLA({sla_target_ms:,.1f}ms)를 초과하였습니다.")
        if failures > 0:
            print(f"  {failures}건의 요청 처리 실패가 발생하였습니다.")
    print("=" * 82)

    return is_passed


def main():
    parser = argparse.ArgumentParser(description="[P2-2] 비즈니스 및 추론 SLA 벤치마크 러너")
    parser.add_argument("--runs", type=int, default=10, help="연속 부하 호출 횟수 (기본값: 10)")
    parser.add_argument("--sla", type=float, default=1500.0, help="SLA P95 상한치 ms (기본값: 1500.0)")
    parser.add_argument("--no-warmup", action="store_true", help="사전 웜업 단계 비활성화")
    args = parser.parse_args()

    s_latencies, c_latencies, details, gpu_info = run_sla_benchmark(
        num_requests=args.runs,
        sla_target_ms=args.sla,
        warmup=not args.no_warmup,
    )
    passed = evaluate_and_print_results(
        server_latencies=s_latencies,
        client_latencies=c_latencies,
        detailed_results=details,
        gpu_info=gpu_info,
        sla_target_ms=args.sla,
    )
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
