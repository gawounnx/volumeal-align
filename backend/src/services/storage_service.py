"""2-Phase 파일 원자성 커밋 및 롤백 서비스 [FR-001, NFR 3.2, BR-VAL-003].

1. Phase 1 (임시 저장): 동일 파티션 내 /static/uploads/.tmp/{uuid}.jpg 선저장 (HEIC 415 차단)
2. Phase 2 (확정 이동): Celery 추론 성공 시 os.rename() 원자적 이동 -> /static/uploads/meals/{uuid}.jpg
3. 실패 롤백: Timeout(504), OOM(503), 추론 실패 시 finally 블록에서 os.unlink()로 고아 파일 즉시 삭제
"""
import os
import uuid
from pathlib import Path
from typing import Optional, Tuple
from src.core.exceptions import AppException


def is_heic_image(contents: bytes, filename: Optional[str] = None) -> bool:
    """[BR-VAL-003] 파일 확장자 및 매직 바이트 기반 HEIC 포맷 검사."""
    if filename:
        ext = os.path.splitext(filename)[1].lower()
        if ext in {".heic", ".heif"}:
            return True

    if len(contents) >= 12:
        # ISO Base Media File Format (ISOBMFF) ftyp box signature
        if contents[4:8] == b"ftyp":
            brand = contents[8:12].lower()
            heic_brands = {
                b"heic", b"heix", b"hevc", b"hevx",
                b"heim", b"heis", b"mif1", b"msf1",
            }
            if brand in heic_brands:
                return True
            # Compatible brands check (bytes 16..32)
            compatible_chunk = contents[12:32].lower()
            if any(hb in compatible_chunk for hb in heic_brands):
                return True
    return False


class StorageService:
    """동일 파티션 내 2-Phase 파일 커밋 및 롤백 관리자."""

    def __init__(self, base_dir: Optional[str] = None):
        if base_dir is None:
            # 1순위: Docker 컨테이너 표준 경로
            container_path = Path("/workspace/backend/static/uploads")
            # 2순위: 로컬 상대 경로
            local_backend_path = Path(__file__).resolve().parent.parent.parent / "static" / "uploads"
            if container_path.exists():
                self.base_dir = container_path
            elif local_backend_path.exists():
                self.base_dir = local_backend_path
            else:
                self.base_dir = container_path
        else:
            self.base_dir = Path(base_dir)

        self.tmp_dir = self.base_dir / ".tmp"
        self.meals_dir = self.base_dir / "meals"

        self.tmp_dir.mkdir(parents=True, exist_ok=True)
        self.meals_dir.mkdir(parents=True, exist_ok=True)

    def validate_image_payload(self, contents: bytes, filename: Optional[str] = None) -> None:
        """[BR-VAL-003] HEIC 포맷 즉시 415 차단."""
        if is_heic_image(contents, filename):
            raise AppException(
                status_code=415,
                code="ERR_HEIC_UNSUPPORTED",
                message="HEIC 포맷은 서버에서 지원하지 않습니다. 클라이언트에서 JPEG로 변환 후 업로드하세요.",
            )

    async def save_temp_image(
        self,
        contents: bytes,
        filename: Optional[str] = None,
        file_uuid: Optional[uuid.UUID] = None,
    ) -> Tuple[str, str]:
        """[Phase 1] 클라이언트 업로드 이미지를 동일 파티션 내 .tmp 폴더에 선저장."""
        self.validate_image_payload(contents, filename)

        file_id = str(file_uuid or uuid.uuid4())
        tmp_filename = f"{file_id}.jpg"
        tmp_path = str(self.tmp_dir / tmp_filename)

        try:
            import aiofiles
            async with aiofiles.open(tmp_path, "wb") as f:
                await f.write(contents)
        except ImportError:
            # aiofiles 미설치 환경 대비 표준 파일 저장
            with open(tmp_path, "wb") as f:
                f.write(contents)

        return file_id, tmp_path

    def commit_temp_image(self, file_id: str, tmp_path: str) -> Tuple[str, str]:
        """[Phase 2] 연산 성공 시 os.rename()을 사용해 meals/ 로 원자적 이동 (O(1))."""
        final_filename = f"{file_id}.jpg"
        final_path = str(self.meals_dir / final_filename)

        if os.path.exists(tmp_path):
            os.rename(tmp_path, final_path)

        web_url = f"/static/uploads/meals/{final_filename}"
        return final_path, web_url

    def rollback_temp_image(self, tmp_path: str) -> bool:
        """[실패 롤백] Timeout(504), OOM(503), 에러 발생 시 .tmp 고아 파일 즉시 삭제."""
        try:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)
                return True
        except OSError:
            pass
        return False
