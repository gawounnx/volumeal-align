# VoluMeal-Align backend

## 실행

`backend`에서 환경변수를 설정한 뒤 `uvicorn src.main:app --host 0.0.0.0 --port 8000`으로 실행합니다. `backend/.env`를 자동으로 읽으며, 실행 환경변수가 파일보다 우선합니다. `.env.example`은 설정 형식 참고용입니다. 실제 `.env`는 Git에서 제외됩니다.

- `DATABASE_URL`: PostgreSQL asyncpg 연결 문자열.
- `JWT_SECRET_KEY`: 충분히 긴 무작위 비밀키. development 이외 환경에서는 필수입니다. development에서 생략하면 프로세스 재시작 시 세션이 만료됩니다.
- `CORS_ORIGINS`: 허용 프론트 주소의 JSON 배열. 기본값은 `["http://localhost:3000"]`입니다.
- `ONNX_SEG_MODEL_PATH`: 클래스 names 메타데이터를 포함하는 YOLO segmentation ONNX.
- `ONNX_DEPTH_MODEL_PATH`: 입력 518×518 RGB/ImageNet 정규화, 출력이 미터 단위 깊이인 모델 경로.
- `DEPTH_MODEL_IS_METRIC=true`: 위 모델의 미터 단위 출력 계약을 확인한 후 설정합니다. 상대 깊이 모델에는 설정하면 안 됩니다.
- `FOOD_EMBEDDING_MODEL_PATH`: 음식 크롭을 임베딩으로 변환하는 ONNX 모델.
- `FOOD_EMBEDDING_INDEX_PATH`: 라벨된 기준 이미지의 `embeddings`와 `food_ids` 배열을 담은 NPZ.
- `FOOD_CATALOG_PATH`: 표준명, 별칭, 상호작용 태그를 담은 식품 카탈로그.
- `FOOD_DENSITY_PATH`: foodId별 실측 밀도와 표준편차.
- `FOOD_NUTRIENTS_PATH`: foodId별 기준 중량과 영양성분.
- `ONNX_USE_CUDA=true`: CUDA provider 사용을 요청합니다. 기본은 CPU이며 실제 provider는 `/api/v1/health`에서 확인합니다. 현재 환경의 CUDA 로딩에는 `libcudnn.so.9`가 부족합니다. 시스템 CUDA 라이브러리는 이번 수정에서 설치하지 않았습니다.

깊이 모델/영양 데이터가 준비되지 않았으면 분석은 503과 구체적인 오류 코드를 반환합니다. 합성 깊이, 임의 영양 계수, 가짜 점군으로 성공 응답을 만들지 않습니다. 실모델 정확도와 카메라 보정은 별도의 수용 검증이 필요합니다.

## 인증과 API

`POST /api/v1/auth/login`에 `email`, `password`를 보내 받은 `accessToken`을 `Authorization: Bearer ...`로 전달합니다. 프론트엔드 로그인 폼도 이 경로를 사용합니다. 토큰은 브라우저 메모리에만 보관하므로 새로고침하면 다시 로그인합니다.

개발용 고정 테스터 접근은 `ENV=development`와 `DEV_AUTH_BYPASS=true`를 둘 다 설정했을 때만 가능합니다. 기본은 꺼져 있습니다. 기존 시드의 임의 해시로는 로그인할 수 없을 수 있으며, 기존 계정 비밀번호를 이번 수정에서 변경하지 않았습니다.

- `/api/v1/meals`: 본인 기록 목록/상세 조회.
- `/api/v1/medications`: 본인 복약 등록/목록/비활성화.
- `/api/v1/vision/estimate`: 로그인 사용자의 분석 저장 및 등록 복약 기반 경고.
- `focal_length_mm`는 **35mm 환산 초점거리**입니다. 기본 26mm는 가정이며 실제 카메라 보정값이 아니므로 `isCalibrated=false`입니다.
- 원본 이미지는 보관하지 않습니다. `imageUrl=""`은 보관된 이미지가 없다는 뜻입니다. 프론트는 업로드 원본의 로컬 미리보기를 사용합니다.
- 파일 최대 10MiB, 최대 12,000,000픽셀, JPEG/PNG/WebP를 지원합니다.

## 식품 식별 및 영양 데이터 계약

음식 크롭은 라벨된 기준 이미지 임베딩과 비교하여 `foodId`를 얻습니다. DINOv2 임베딩을 음식명
텍스트나 영양 DB 행과 직접 비교하지 않습니다. 모든 데이터 조인은 이름이 아닌 `foodId`를 사용합니다.

- `food_catalog.json`: `foodId`, 표준명, 별칭, 상호작용 태그.
- `food_density_profiles.json`: `foodId`, g/cm³ 밀도, 표준편차, 조리 상태, 출처.
- `food_nutrients.json`: `foodId`, 기준 중량, 영양성분, 원천 코드와 버전.
- `food_reference_embeddings.npz`: `embeddings`(N×D float), `food_ids`(N개 문자열).

계산은 `weight_g = volume_cm3 * density_g_cm3`, 각 영양소는
`nutrient_per_basis * weight_g / basis_weight_g`를 사용합니다. 세 JSON의 foodId 집합이 다르거나
출처 필드가 비어 있으면 서버는 준비되지 않은 것으로 판정합니다. 형식만 보여주는 `*.example.json`은
운영 데이터가 아니며 그대로 설정하면 안 됩니다.

Top-1 점수가 0.80 미만이거나 Top-1과 Top-2 차이가 0.10 미만이면
`requiresConfirmation=true`를 반환하고 해당 분석은 DB에 저장하지 않습니다.

경고는 해당 사용자의 활성 복약과 DB 규칙을 교차 조회합니다. 기존 DB 규칙/시드의 임상 문구는 이번 코드 수정에서 의학적으로 검증하지 않았습니다.

## DB와 초기 설치

현재 DB의 UUID 기반 7개 업무 테이블에 ORM을 맞췄습니다. 기존 `medications`/`drug_food_interactions` 보조 테이블과 데이터는 삭제하지 않았으며 신규 코드에서는 사용하지 않습니다.

빈 DB는 `alembic upgrade head`로 초기 스키마를 생성할 수 있습니다. **기존 DB에는 이 초기 마이그레이션을 그대로 실행하지 마세요.** 기존 테이블이 있으므로 먼저 스키마를 비교하고 일치 확인 후 관리자가 기준 revision을 stamp해야 합니다. 이번 작업에서는 기존 DB의 마이그레이션 적용·stamp를 실행하지 않았습니다. 자동 downgrade는 데이터 삭제 방지를 위해 제공하지 않습니다.

`psql "$DATABASE_URL" -f app/data/seed.sql`는 예시 초기 데이터를 넣습니다. `ON CONFLICT DO NOTHING`으로 기존 계정/데이터는 덮어쓰지 않습니다. 운영용 임상 데이터 적재 도구가 아닙니다.

## 검증

- `python -m pytest tests -q`: DB 통합 테스트는 기본 skip.
- `RUN_DB_TESTS=1 python -m pytest tests -q`: 연결 DB에서 임시 데이터를 트랜잭션 안에 생성하고 롤백하는 통합 검사까지 수행. 분석 계산은 통합 테스트에서 고정하고, 별도의 단위 테스트에서 주입된 깊이·영양 데이터로 기하 계산을 검증합니다.
- `python -m alembic upgrade head --sql`: DB 쓰기 없이 신규 스키마 SQL 생성.
- `python scripts/generate_frontend_types.py`: 프론트 응답 타입 재생성.


## 준비 상태 확인

`python scripts/check_readiness.py`는 DB 연결, 7개 ORM, ONNX 세그멘테이션 로딩, 깊이 모델과 영양 데이터 준비 상태를 확인합니다. 자원이 누락되면 종료 코드 1과 항목별 결과를 출력합니다. 데이터·스키마·계정은 변경하지 않습니다. 모델 로딩 성공은 실사진 정확도 검증을 의미하지 않습니다.

이번 로컬 설정에는 새 무작위 JWT 비밀키를 `backend/.env`에 저장했습니다. 계정 비밀번호와 인증 우회 설정은 변경하지 않았습니다.
