# VoluMeal-Align

식사 사진의 음식 영역과 깊이를 분석해 부피·중량·영양소를 추정하고, 등록한 복약 정보에 따른 경고와 식단 이력을 제공하는 웹 프로젝트입니다.

## 기능과 요구사항

아래는 코드가 담당하는 범위입니다. 실제 모델 정확도나 모든 요구사항의 수용 검증이 완료됐다는 뜻은 아닙니다.

| 요구사항 | 기능 |
| --- | --- |
| FR-001~FR-003 | ONNX 깊이 추정·영역 분할, 기준 평면 추정과 음식 부피 적분 |
| FR-004 | 음식 이미지 임베딩 검색, `foodId` 기준 밀도·영양 데이터 결합 |
| FR-005 | 사용자 등록 복약과 DB 규칙을 이용한 음식 상호작용 경고 |
| FR-006 | Three.js 기반 점군·경계 상자 시각화 |
| FR-007 | 인증, 식단 저장·조회, 복약 정보 관리 |
| FR-008 | 불확실한 음식 후보 확인, 중량 보정 및 확정 저장 |

요구사항 전체는 [요구사항 명세서](volumeal-align요구사항명세서/Volumeal%20Requirement.md)를 참고하세요. 임상 규칙의 타당성과 실사진 측정 오차는 별도의 검증 대상입니다.

## 기술 구성

| 영역 | 구성 |
| --- | --- |
| 프론트엔드 | Next.js 15, React 18, TypeScript, Tailwind CSS, Three.js |
| 백엔드 | Python 3.10, FastAPI, SQLAlchemy, Alembic |
| 데이터베이스 | PostgreSQL / asyncpg |
| 영상·기하 처리 | ONNX Runtime, OpenCV, NumPy, Open3D |
| 배포 | Docker, Render Blueprint |

```text
브라우저 → Next.js /api/v1 프록시 → FastAPI → PostgreSQL
                                      └→ ONNX 모델 + 식품 데이터
```

프론트엔드의 `API_BACKEND_URL`은 서버가 사용하는 백엔드 주소이며 빌드 시 반영됩니다. API 키는 프론트엔드나 `NEXT_PUBLIC_*` 변수에 넣지 않습니다.

## 저장소 구조

```text
backend/
  src/                  API, 인증, DB 모델, 분석·영양·복약 로직
  alembic/              DB 마이그레이션
  data/                 식품 카탈로그, 밀도·영양 데이터, 임베딩 인덱스
  scripts/              준비 상태 검사와 데이터·모델 설정 도구
  tests/                단위·DB 통합 테스트
  Dockerfile
  requirements.txt
frontend/
  src/                  화면, 3D 뷰어, API 클라이언트
  tests/                계약 및 브라우저 E2E 테스트
  Dockerfile
Audit(오류 보고서)/      검토·검증 기록
volumeal-align요구사항명세서/
render.yaml             백엔드·프론트엔드·PostgreSQL 배포 구성
GITHUB-UPLOAD.md         소스 업로드와 모델 파일 안내
```

## 로컬 실행

아래 명령은 Bash 기준입니다. Python 3.10, Node.js 20, 접근 가능한 PostgreSQL 데이터베이스가 필요합니다. 모델이 없어도 서버와 화면을 실행할 수 있지만 이미지 분석은 사용할 수 없습니다.

### 1. 백엔드 설정

```bash
git clone https://github.com/gawounnx/volumeal-align.git
cd volumeal-align/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

`backend/.env`에 아래 값을 설정합니다. 기존 `.env`가 있다면 복사로 덮어쓰지 말고 필요한 항목만 추가하세요.

| 변수 | 설정 |
| --- | --- |
| `DATABASE_URL` | 본인 PostgreSQL의 `postgresql+asyncpg://USER:PASSWORD@HOST:5432/DATABASE` 연결 문자열 |
| `JWT_SECRET_KEY` | 충분히 긴 무작위 비밀키 |
| `CORS_ORIGINS` | 로컬 기본값 `["http://localhost:3000"]` |
| `DEPTH_MODEL_IS_METRIC` | 검증된 미터 단위 깊이 모델을 설정하기 전에는 `false` |

키는 각각 아래 명령으로 생성해 `.env`에 저장할 수 있습니다. 복약 암호화 키는 재시작 후에도 같은 값을 유지해야 기존 암호문을 읽을 수 있습니다.

```bash
python -c 'import secrets; print(secrets.token_urlsafe(48))'
python -c 'import base64, os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())'
```

**신규 빈 DB에서만** 마이그레이션을 적용한 뒤 서버를 실행합니다.

```bash
python -m alembic upgrade head
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

기존 DB는 먼저 스키마와 마이그레이션 이력을 비교하세요. Docker 시작 명령도 `alembic upgrade head`를 실행하므로 기존 DB를 연결할 때 동일한 점검이 필요합니다.

- API 문서: <http://localhost:8000/docs>
- 준비 상태: <http://localhost:8000/api/v1/health>
- 사용자 계정: API 문서의 `POST /api/v1/auth/register`로 생성하고 로그인합니다.

### 2. 프론트엔드 실행

별도 터미널에서 실행합니다.

```bash
cd volumeal-align/frontend
npm ci
cp .env.example .env.local
npm run dev
```

<http://localhost:3000>에 접속합니다. 로컬 백엔드 주소 기본값은 `http://127.0.0.1:8000`입니다. 운영 빌드는 `npm run build` 후 `npm start`로 실행합니다.

## 실제 이미지 분석 준비

GitHub 소스 업로드에는 대용량 ONNX 가중치가 포함되지 않습니다. 다음 자원이 필요합니다.

- 클래스 메타데이터를 포함한 세그멘테이션 ONNX 모델: `ONNX_SEG_MODEL_PATH`
- 출력이 실제 미터 단위인 깊이 ONNX 모델: `ONNX_DEPTH_MODEL_PATH`
- 음식 이미지 임베딩 ONNX 모델: `FOOD_EMBEDDING_MODEL_PATH`
- 라벨된 기준 이미지 임베딩 인덱스: `FOOD_EMBEDDING_INDEX_PATH`
- 동일한 `foodId`로 연결되는 카탈로그·밀도·영양 파일: `FOOD_CATALOG_PATH`, `FOOD_DENSITY_PATH`, `FOOD_NUTRIENTS_PATH`

`*.example.json`은 형식 참고용입니다. 포함된 데이터의 범위·출처·정확도와 모델 입출력 계약을 검증한 뒤 운영에 사용하세요. 상대 깊이 모델에 `DEPTH_MODEL_IS_METRIC=true`를 설정해도 미터 단위 모델로 변환되지 않습니다.

백엔드 디렉터리에서 준비 상태를 확인합니다.

```bash
python scripts/check_readiness.py
```

누락된 자원이 있으면 검사 종료 코드가 1일 수 있습니다. HTTP health 응답만으로 모델 준비나 정확도가 보장되지는 않습니다. 상세 계약은 [백엔드 README](backend/README.md)를 참고하세요.

## Render 배포와 OpenAI API 키

현재 [render.yaml](render.yaml)은 공모전 시연용으로 `volumeal-backend`, `volumeal-frontend`, `volumeal-db` 모두 `plan: free`를 명시합니다.

무료 웹 서비스는 15분간 요청이 없으면 절전되며 다음 접속 시 기동 시간이 걸립니다. 워크스페이스의 무료 웹 서비스 실행 시간은 월 750시간을 공유합니다. 무료 PostgreSQL은 생성 30일 후 만료되므로 공모전 일정에 맞춰 데이터를 별도로 백업하세요. 무료 서버의 512MB 메모리에서 실제 모델 추론 동작은 아직 검증되지 않았습니다. 카드 등록 후 사용량 한도를 초과하면 별도 요금이 발생할 수 있으므로 생성 화면에서 세 리소스가 모두 Free인지 확인하세요. [Render 무료 플랜 안내](https://render.com/docs/free)

1. Render에서 **New → Blueprint**를 열고 이 저장소의 `main` 브랜치를 연결합니다.
2. 생성할 서비스와 DB 설정, 표시되는 요금을 확인합니다.
3. Blueprint가 요청하는 `OPENAI_API_KEY` 값은 Render에 직접 입력합니다. 생성된 백엔드 서비스에서는 **Environment**에서 관리합니다.
4. 배포된 백엔드의 실제 주소가 프론트엔드 `API_BACKEND_URL`과 일치하는지 확인하고, 주소를 변경했다면 프론트엔드를 다시 빌드합니다.
5. 실제 프론트엔드 주소에 맞춰 `CORS_ORIGINS`를 확인합니다.
6. 모델과 식품 데이터를 배포 환경에 제공하고 준비 상태 및 실제 요청을 검증합니다.

`DATABASE_URL`은 Blueprint의 DB 연결에서 가져오며 JWT·복약 암호화 키는 생성하도록 설정돼 있습니다. 복약 암호화 키는 위의 Base64 형식과 맞는지 확인하고 기존 데이터가 있는 상태에서 임의로 교체하지 마세요.

**현재 키 입력은 보관 설정 단계입니다. OpenAI 요청을 수행하는 연동 코드가 아직 없으며, Render 배포 성공과 전체 분석 기능 완성은 별도로 확인해야 합니다.**

## 검증

```bash
# backend 디렉터리
python -m pytest tests -q

# frontend 디렉터리
npm test
npm run typecheck
npm run build
```

2026-09-16 소스 업로드 전 확인 결과: 백엔드 **82 passed, 11 skipped**(기본 실행에서 DB 통합 테스트 제외), 프론트엔드 계약 테스트·타입 검사 통과. 이 결과는 실제 ONNX 모델 정확도, 운영 배포, 브라우저 E2E 검증을 의미하지 않습니다.

DB 통합 테스트는 별도 테스트 DB를 설정한 뒤 `RUN_DB_TESTS=1 python -m pytest tests -q`로 실행합니다. 브라우저 E2E 실행 조건은 [프론트엔드 README](frontend/README.md)를 참고하세요.

## 관련 문서

- [백엔드 실행·모델·DB 안내](backend/README.md)
- [프론트엔드 실행·E2E 안내](frontend/README.md)
- [GitHub 업로드·대용량 모델 안내](GITHUB-UPLOAD.md)
- [수정 내역과 당시 검증 결과](FIXES-2026-09-15.md)
- [프로젝트 요구사항](volumeal-align요구사항명세서/Volumeal%20Requirement.md)

실제 `.env`, API 키, DB 비밀번호는 커밋하지 않습니다. 검토 보고서는 작성 시점의 기록이므로 현재 동작은 소스와 최신 검증 결과를 함께 확인하세요.

