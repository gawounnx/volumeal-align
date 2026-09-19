# 요구사항 대조 수정 및 검증 결과 (2026-09-15)

## 적용한 수정

| 요구사항 | 원인 | 수정 |
| --- | --- | --- |
| NFR 3.3 추론 동시성 | 요청마다 제한 없이 이미지 디코딩과 추론 실행 | 워커 프로세스당 asyncio.Semaphore(5) 적용 |
| NFR 3.2 이미지 생명주기 | 분석 함수가 압축 원본과 디코딩 배열을 DB 저장까지 유지 | 분석 함수 분리, 압축 버퍼 참조 제거, 성공/실패 시 업로드 닫기 |
| FR-003 기준 평면 | 알약 검출을 제거한 뒤 배경을 구해 알약 깊이가 평면 표본에 포함 | 모든 검출 객체의 합집합을 평면 표본에서 제외 |
| FR-002 세그멘테이션 | 극단적인 이미지 비율에서 리사이즈 치수가 0이 됨 | 전처리와 마스크 복원 모두 최소 치수 1 보장 |

API 응답 형식, DB 스키마, 영양 수치 및 기존 데이터는 변경하지 않았다.
동시성 변경은 High Risk로 분류한다. 다중 워커의 전체 한도는 워커 수 곱하기 5이다.
HTTP multipart 파싱은 라우터보다 먼저 일어나므로 업로드 수신 자체의 동시성 제한은 아니다.

## 검증

- backend: python -m pytest tests -q: 63 passed, 3 skipped.
- backend: RUN_DB_TESTS=1 python -m pytest tests/integration -q: 3 passed.
- frontend: npm test: 통과.
- frontend: npm run typecheck: 통과.
- 추가 회귀 테스트: 동시 요청 6건의 최대 실행 5건, 오류 후 슬롯 반환 및 파일 닫기, 알약 평면 제외, 1x2000 및 2000x1 이미지 처리.
- 기존 Starlette/AnyIO deprecation 경고 1건.
- 운영 빌드, 실제 모델 부피 정확도, GPU 및 브라우저 FPS는 이번 작업에서 검증하지 않았다.
- git 실행 파일이 없어 git diff/status는 사용할 수 없었다.

## 실제 준비 상태 (Fact)

check_readiness.py 결과:
- DB 연결 및 ORM 스키마 조회 성공.
- 세그멘테이션 모델 로딩 성공, CPUExecutionProvider.
- 메트릭 깊이 모델 준비 실패.
- 영양 데이터 준비 실패.
- ready=false. 검사 종료 코드 1은 준비되지 않은 자원이 있다는 뜻이다.

기존 감사 보고서의 세그멘테이션 링크 오류는 현재 환경에서 재현되지 않았다.
깊이 모델과 영양 데이터 부재를 임의의 가중치나 수치로 대체하지 않았다.

## 남은 명세서 차이 및 검증 항목

- FR-001: 검증된 미터 단위 깊이 모델과 카메라 EXIF/보정 경로.
- FR-004: DINOv2 검색 및 출처가 검증된 밀도/영양 자료 연결.
- FR-005: 시각적 약제 식별과 EDI 코드 매칭, /drugs/interactions.
- FR-007: 목록 응답 envelope 및 날짜 범위 통계.
- NFR 3.2: 현재 Bearer 인증은 명세서의 HttpOnly/SameSite=Strict 쿠키 방식과 다르다. 복약 컬럼 암호화도 별도 구현 검토가 필요하다.
- BR-VAL-002: 기준 평면 실패 시 2D 표준 인분 폴백 연동.
- 실제 사진 부피 오차, CPU 응답 시간 450ms, 3D 60 FPS, 실약제/식품 데이터 적합성은 미검증.

이번 수정은 위 전체 기능의 구현 완료를 뜻하지 않는다.

## 설계와 롤백

기존 파이프라인 및 API 계약을 유지하면서 분석 구간에만 동시성 제한을 추가했다.
추론만 제한하면 대기 요청의 이미지 디코딩 메모리가 누적되므로 읽기와 디코딩도 동일 구간으로 묶었다.
모든 객체를 평면에서 제외하되 식품 영양/점군 계산에는 기존 음식 마스크만 사용한다.
스키마 마이그레이션은 없다. 롤백 시 세 소스 파일의 이번 변경만 되돌릴 수 있으며 기존 사용자 변경은 보존해야 한다.

## 핵심 추가 함수 전체

파일: backend/src/api/v1/endpoints/vision.py

```python
async def analyze_upload(file, focal_length_mm, conf_threshold):
    # Ref: NFR 3.3, bound image decoding and inference together per worker.
    async with inference_semaphore:
        try:
            contents = await file.read(settings.MAX_UPLOAD_BYTES + 1)
            if len(contents) > settings.MAX_UPLOAD_BYTES:
                raise AppException(413, "ERR_FILE_TOO_LARGE", "이미지 파일은 10MB 이하로 업로드해 주세요.")
            image = await run_in_threadpool(decode_image, contents)
            del contents
            pipeline = await run_in_threadpool(get_pipeline)
            return await run_in_threadpool(pipeline.process_image, image, focal_length_mm, conf_threshold)
        finally:
            await file.close()
```

모듈에 import asyncio와 inference_semaphore = asyncio.Semaphore(5)를 추가했고,
estimate_meal_vision에서 result=await analyze_upload(file,focal_length_mm,conf_threshold)로 호출한다.

