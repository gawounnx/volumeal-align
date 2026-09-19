import asyncio
import io
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import UploadFile

from src.api.v1.endpoints import vision
from src.core.exceptions import AppException


@pytest.mark.asyncio
async def test_six_uploads_run_at_most_five_inferences(monkeypatch):
    monkeypatch.setattr(vision, 'inference_semaphore', asyncio.Semaphore(5))
    started = asyncio.Event()
    release = asyncio.Event()
    active = 0
    peak = 0

    def process(*args):
        return {'ok': True}

    monkeypatch.setattr(vision, 'decode_image', lambda contents: contents)
    monkeypatch.setattr(vision, 'get_pipeline', lambda: SimpleNamespace(process_image=process))

    async def threadpool(function, *args):
        nonlocal active, peak
        if function is process:
            active += 1
            peak = max(peak, active)
            if active == 5:
                started.set()
            try:
                await release.wait()
                return function(*args)
            finally:
                active -= 1
        return function(*args)

    monkeypatch.setattr(vision, 'run_in_threadpool', threadpool)
    uploads = [UploadFile(file=io.BytesIO(b'image')) for _ in range(6)]
    tasks = [asyncio.create_task(vision.analyze_upload(upload, 26, .25)) for upload in uploads]
    try:
        await asyncio.wait_for(started.wait(), 2)
        await asyncio.sleep(0)
        assert active == 5
        assert sum(upload.file.tell() > 0 for upload in uploads) == 5
    finally:
        release.set()
        results = await asyncio.wait_for(asyncio.gather(*tasks), 2)
    assert peak == 5
    assert results == [{'ok': True}] * 6
    assert all(upload.file.closed for upload in uploads)


@pytest.mark.asyncio
async def test_failed_decode_closes_upload_and_releases_slot(monkeypatch):
    semaphore = asyncio.Semaphore(1)
    monkeypatch.setattr(vision, 'inference_semaphore', semaphore)
    monkeypatch.setattr(vision, 'run_in_threadpool', AsyncMock(
        side_effect=AppException(422, 'ERR_INVALID_IMAGE', 'invalid'),
    ))
    upload = UploadFile(file=io.BytesIO(b'invalid'))
    with pytest.raises(AppException):
        await vision.analyze_upload(upload, 26, .25)
    assert upload.file.closed
    await asyncio.wait_for(semaphore.acquire(), 1)
    semaphore.release()


def test_exif_focal_length_uses_35mm_equivalent():
    from PIL import Image

    image = Image.new("RGB", (4, 4), "white")
    exif = image.getexif()
    exif[41989] = 52
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", exif=exif.tobytes())

    assert vision.extract_exif_focal_length_mm(buffer.getvalue()) == 52.0


def test_exif_focal_length_is_optional():
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (4, 4), "white").save(buffer, format="JPEG")

    assert vision.extract_exif_focal_length_mm(buffer.getvalue()) is None


@pytest.mark.asyncio
async def test_analyze_upload_passes_exif_calibration_to_pipeline(monkeypatch):
    from PIL import Image

    image = Image.new("RGB", (4, 4), "white")
    exif = image.getexif()
    exif[41989] = 52
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", exif=exif.tobytes())
    received = {}

    def process(image, focal_length_mm, conf_threshold):
        received.update({"focal_length_mm": focal_length_mm, "conf_threshold": conf_threshold})
        return {"ok": True}

    monkeypatch.setattr(vision, "get_pipeline", lambda: SimpleNamespace(process_image=process))
    calibration = {}
    result = await vision.analyze_upload(
        UploadFile(file=io.BytesIO(buffer.getvalue())), None, .25, calibration
    )

    assert result == {"ok": True}
    assert received == {"focal_length_mm": 52.0, "conf_threshold": .25}
    assert calibration == {"focal_length_mm": 52.0, "is_calibrated": True}


@pytest.mark.asyncio
async def test_analyze_upload_uses_explicit_is_calibrated_flag(monkeypatch):
    from PIL import Image

    image = Image.new("RGB", (4, 4), "white")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")

    monkeypatch.setattr(vision, "get_pipeline", lambda: SimpleNamespace(process_image=lambda *args: {"ok": True}))
    calibration = {}
    result = await vision.analyze_upload(
        UploadFile(file=io.BytesIO(buffer.getvalue())),
        focal_length_mm=35.0,
        conf_threshold=0.25,
        calibration=calibration,
        is_calibrated=True,
    )

    assert result == {"ok": True}
    assert calibration == {"focal_length_mm": 35.0, "is_calibrated": True}


@pytest.mark.asyncio
async def test_analyze_upload_defaults_to_uncalibrated_without_exif(monkeypatch):
    from PIL import Image

    image = Image.new("RGB", (4, 4), "white")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")

    monkeypatch.setattr(vision, "get_pipeline", lambda: SimpleNamespace(process_image=lambda *args: {"ok": True}))
    calibration = {}
    result = await vision.analyze_upload(
        UploadFile(file=io.BytesIO(buffer.getvalue())),
        focal_length_mm=26.0,
        conf_threshold=0.25,
        calibration=calibration,
        is_calibrated=False,
    )

    assert result == {"ok": True}
    assert calibration == {"focal_length_mm": 26.0, "is_calibrated": False}

