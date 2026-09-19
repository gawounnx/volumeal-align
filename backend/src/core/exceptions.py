"""VoluMeal-Align 전역 도메인 비즈니스 예외 정의 [NFR 10.1, Section 10.2]."""
from datetime import datetime, timezone
from typing import Any, List, Optional
from fastapi import HTTPException, status


def generate_error_timestamp() -> str:
    """[NFR 10.1] ISO-8601 UTC 표준 포맷 타임스탬프 생성 (예: 2026-09-16T15:35:10.000Z)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


class AppException(HTTPException):
    """[NFR 10.1] 전역 표준 비즈니스 도메인 예외 기본 클래스."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: Optional[List[Any]] = None,
        path: Optional[str] = None,
    ):
        self.code = code
        self.message = message
        self.details = details if details is not None else []
        self.path = path or ""
        self.timestamp = generate_error_timestamp()

        detail_payload = {
            "success": False,
            "error": {
                "code": self.code,
                "message": self.message,
                "timestamp": self.timestamp,
                "path": self.path,
                "details": self.details,
            },
        }
        super().__init__(status_code=status_code, detail=detail_payload)


class PlaneNotFoundException(AppException):
    """[FR-003, Section 10.2] RANSAC 평면 추정 실패 시 발생하는 예외."""

    def __init__(
        self,
        message: str = "테이블 기준 평면 추정에 실패했습니다. 밝은 곳에서 접시와 주변 테이블이 함께 보이도록 다시 촬영해 주세요.",
        code: str = "ERR_PLANE_NOT_FOUND",
    ):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code=code,
            message=message,
        )


class VolumeOutOfBoundsException(AppException):
    """[FR-003, Section 10.2] 연산된 부피가 유효 임계치를 벗어난 경우 발생하는 예외."""

    def __init__(self, volume_cm3: float):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="ERR_VOLUME_OUT_OF_BOUNDS",
            message=f"연산된 음식 부피({volume_cm3:.2f} cm³)가 유효 범위(5 ~ 5000 cm³)를 벗어났습니다.",
            details=[{"field": "volume_cm3", "issue": f"Out of bounds: {volume_cm3}"}],
        )


class ZeroObjectDetectedException(AppException):
    """[FR-002, Section 10.2] 검출된 음식 객체가 없는 경우 발생하는 예외."""

    def __init__(self):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="ERR_ZERO_OBJECT_DETECTED",
            message="이미지 내 유효한 음식 또는 약제가 검출되지 않았습니다.",
        )


class HeicUnsupportedException(AppException):
    """[BR-VAL-003, Section 10.2] HEIC 포맷 이미지 업로드 차단 예외."""

    def __init__(
        self,
        message: str = "HEIC 포맷은 서버에서 지원하지 않습니다. 클라이언트에서 JPEG로 변환 후 업로드하세요.",
    ):
        super().__init__(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            code="ERR_HEIC_UNSUPPORTED",
            message=message,
        )


class CeleryOOMException(AppException):
    """[Section 10.2, 10.3] Celery Worker VRAM OOM 시 메인 API가 반환하는 예외."""

    def __init__(
        self,
        message: str = "ML 추론 엔진 메모리가 일시적으로 부족합니다. 잠시 후 다시 시도해 주세요.",
    ):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="ERR_CELERY_OOM",
            message=message,
        )


class CeleryTimeoutException(AppException):
    """[Section 10.2, 10.3] Celery Worker 작업 제한 시간(5.0초) 초과 시 발생하는 예외."""

    def __init__(
        self,
        message: str = "ML 추론 연산 처리 시간이 초과되었습니다. 임시 파일이 안전하게 정리되었습니다.",
    ):
        super().__init__(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            code="ERR_CELERY_TIMEOUT",
            message=message,
        )


class AccessDeniedException(AppException):
    """[Section 9.3, 10.2, 14.1] 리소스 접근 권한 위반(IDOR 방어) 시 발생하는 예외."""

    def __init__(self, message: str = "본인 소유의 식단에만 접근할 수 있습니다."):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            code="ERR_ACCESS_DENIED",
            message=message,
        )


class RateLimitException(AppException):
    """[Section 10.2, 14.2] 분당 API 호출 한도 초과 시 발생하는 예외."""

    def __init__(
        self,
        message: str = "분당 API 호출 한도를 초과했습니다. 잠시 후 다시 시도해 주세요.",
    ):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            code="ERR_RATE_LIMIT",
            message=message,
        )


class InvalidPayloadException(AppException):
    """[Section 10.2] 필수 필드 누락 또는 요청 페이로드 검증 실패 시 발생하는 예외."""

    def __init__(
        self,
        message: str = "요청 페이로드가 올바르지 않습니다.",
        details: Optional[List[Any]] = None,
    ):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="ERR_INVALID_PAYLOAD",
            message=message,
            details=details,
        )


class TokenExpiredException(AppException):
    """[Section 9.1, 10.2] JWT Access Token 만료 시 발생하는 예외."""

    def __init__(self, message: str = "인증 토큰이 만료되었습니다. 토큰을 갱신해 주세요."):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="ERR_TOKEN_EXPIRED",
            message=message,
        )
