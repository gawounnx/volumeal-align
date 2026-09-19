# **Volumeal-Align 요구사항 명세서 Vercel 배포 반영**

# **Response: Technical Specification: VoluMeal-Align \- Turn 1**

**TL;DR** **본 명세서는 랩실 RTX 5090 단일 워크스테이션 환경에서 고용민/차가원 2인의 VS Code Remote 병렬 개발을 위한 자원 격리 및 API Mocking 기반 아키텍처를 정의합니다. 기존 명세에 외부 심사관을 위한 Vercel 프론트엔드 프로덕션 배포 아키텍처(Dual-Track)를 추가로 반영하여 구성했습니다.**

## **1\. System Overview**

### **1.1 프로젝트 목적 및 해결 과제**

> * 수기 입력 병목 및 3D 기하 오차 해소: 단안 RGB 이미지에서 Zero-shot Metric Depth 추정 및 35mm 환산 화각(72도) 기반 픽셀 단위 3D 역투영을 통해, 수기 입력 없이 음식의 정밀 체적(*V*,cm3)과 중량(*W*,g)을 계측합니다.  
> * DINOv2 패치 검색 기반 식품 매핑: 음식 영역 패치 임베딩을 Faiss(**mmap** 방식)를 활용해 대조하여 고유 **foodId**를 식별하고, 밀도(*ρ*)를 조인하여 매크로 영양소를 산출합니다.  
> * 단일 서버(RTX 5090 32GB) 2인 원격 개발 자원 격리: 1대의 Linux OS 환경에서 2인(고용민, 차가원)이 VS Code Remote로 상호 간섭 없이 프론트엔드와 백엔드 GPU 파이프라인을 병렬 개발할 수 있도록 자원과 포트를 엄격히 샌드박싱합니다.

### **1.2 핵심 기능 요약**

> * **FR-001**: 2-Phase Commit 기반 파일 원자성 보장 저장(/static/uploads/.tmp \-\> os.rename) 및 Metric 깊이 맵 생성. (HEIC 포맷 415 차단 포함)  
> * **FR-002**: 음식/식기 픽셀 바이너리 인스턴스 세그멘테이션.  
> * **FR-003**: 2D-to-3D 점군 역투영 및 RANSAC 테이블 바닥면 피팅 기반 이중 수치 적분 체적 연산.  
> * **FR-004**: DINOv2 기반 **foodId** 맵핑, 중량 도출 및 영양성분 비례 계산.  
> * **FR-005**: 클라이언트 단 Three.js WebGL 기반 3D 바운딩 볼륨 및 포인트 클라우드 실시간 렌더링.  
> * **FR-006**: 식단 분석 리포트 DB 적재 및 일자별 통계 이력 조회.  
> * **FR-007**: 불확실 객체에 대한 서버 SSOT 기반 사용자 수동 보정 및 보정 이력(History) 로깅.  
> * **FR-008**: 신규 사용자 계정 가입(Sign-up) 및 인증 토큰 발급.

### **1.3 아키텍처 패턴 및 선정 이유**

> * **선정 패턴**: Contract-First Modular Monolith with Celery Background Queuing  
> * **선정 근거**:  
  1. **CUDA OOM 방어 및 GIL 회피**: ProcessPoolExecutor의 fork 컨텍스트 파괴 문제와 복잡성을 제거하고, 독립된 Celery Worker 데몬(1 Worker, 1 GPU) 구조를 도입합니다. ML 모델은 격리된 메모리에 1회만 적재되어 순차 처리되며, OOM이나 Timeout 시 Worker만 재시작되어 메인 API 서버의 생존을 100% 보장합니다.  
  2. **파티션 경계 원자성 보장 (2-Phase Commit)**: /tmp와 정적 볼륨 간의 shutil.move 복사-삭제 원자성 상실 결함을 해결하기 위해, 최종 목적지 내부 숨김 폴더(/static/uploads/.tmp)에 선저장 후 동일 파티션 내에서 os.rename 연산(O(1))으로 확정 이동합니다.  
  3. **계약 우선(Contract-First)**: 백엔드의 Celery 연동이 끝나기 전이라도 프론트엔드가 MSW Mock을 통해 병렬로 UI를 완결할 수 있습니다.

### **1.4 시스템 컴포넌트 관계도 (Mermaid Component Diagram)**

다음은 심사관용 외부 배포(Vercel) 인프라가 포함된 시스템 컴포넌트 관계도입니다.

`graph TB`  
&nbsp;&nbsp;&nbsp;&nbsp;`subgraph Host_Workstation ["연구실 단일 워크스테이션 (Linux OS / RTX 5090 32GB)"]`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`subgraph Shared_Infra ["공통 인프라 레이어 (Docker Bridge Network)"]`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`PostgresDB[(PostgreSQL 15<br/>Port: 5432)]`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`RedisBroker[(Redis 7 (Broker/Cache)<br/>Port: 6379)]`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`SharedVolume[("Docker Static Volume<br/>/static/uploads/")]`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`end`

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`subgraph Dev1_Domain ["개발자 1: 고용민 격리 환경 (UID: 1001)"]`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`VSCode_Remote_1["VS Code Server (Remote-SSH)"]`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`Goyongmin_BE["FastAPI Async API<br/>Host: 0.0.0.0 | Port: 8001"]`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`Goyongmin_FE["Next.js Preview<br/>Host: 0.0.0.0 | Port: 3001"]`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`subgraph Goyongmin_Celery ["Celery OOM Shield Runtime"]`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`CeleryWorker["Celery Worker Daemon<br/>(1 Worker, VRAM Limit: 14GB)"]`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`Inference_Pipe["Vision Core (Depth, Seg)<br/>Faiss (mmap) + DINOv2"]`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`end`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`end`

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`subgraph Dev2_Domain ["개발자 2: 차가원 격리 환경 (UID: 1002)"]`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`VSCode_Remote_2["VS Code Server (Remote-SSH)"]`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`Chagawon_FE["Next.js Frontend (Dev)<br/>Host: 0.0.0.0 | Port: 3002"]`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`Chagawon_BE["FastAPI Backend (Proxy)<br/>Host: 0.0.0.0 | Port: 8002"]`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`MSW_Engine["MSW Mock Service Worker"]`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`end`  
&nbsp;&nbsp;&nbsp;&nbsp;`end`

&nbsp;&nbsp;&nbsp;&nbsp;`subgraph Client_Access ["외부 접속 클라이언트 (VS Code Port Forwarding)"]`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`Client_Goyongmin["고용민 브라우저<br/>http://localhost:3001"]`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`Client_Chagawon["차가원 브라우저<br/>http://localhost:3002"]`  
&nbsp;&nbsp;&nbsp;&nbsp;`end`

&nbsp;&nbsp;&nbsp;&nbsp;`subgraph Public_Deployment ["외부 공개 프로덕션 배포 레이어"]`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`Vercel_Edge["Vercel Edge Network<br/>https://volumeal-align.vercel.app"]`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`Vercel_FE["Next.js Production Build<br/>(Mock Mode: ALWAYS ON)"]`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`MSW_Production["MSW Engine (Worker)"]`  
&nbsp;&nbsp;&nbsp;&nbsp;`end`

&nbsp;&nbsp;&nbsp;&nbsp;`subgraph External_Audience ["해커톤 평가단"]`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`Judge_Client["심사위원 모바일/PC 브라우저"]`  
&nbsp;&nbsp;&nbsp;&nbsp;`end`

&nbsp;&nbsp;&nbsp;&nbsp;`Judge_Client -->|Public HTTPS Access| Vercel_Edge`  
&nbsp;&nbsp;&nbsp;&nbsp;`Vercel_Edge --> Vercel_FE`  
&nbsp;&nbsp;&nbsp;&nbsp;`Vercel_FE -->|Intercept| MSW_Production`

&nbsp;&nbsp;&nbsp;&nbsp;`VSCode_Remote_1 -.->|Port Forward: 3001, 8001| Client_Goyongmin`  
&nbsp;&nbsp;&nbsp;&nbsp;`VSCode_Remote_2 -.->|Port Forward: 3002, 8002| Client_Chagawon`

&nbsp;&nbsp;&nbsp;&nbsp;`Goyongmin_FE -->|API Call| Goyongmin_BE`  
&nbsp;&nbsp;&nbsp;&nbsp;`Goyongmin_BE -->|Phase 1: Save to .tmp| SharedVolume`  
&nbsp;&nbsp;&nbsp;&nbsp;`Goyongmin_BE -->|Task Queue| RedisBroker`  
&nbsp;&nbsp;&nbsp;&nbsp;`RedisBroker -->|Consume| CeleryWorker`  
&nbsp;&nbsp;&nbsp;&nbsp;`CeleryWorker --> Inference_Pipe`  
&nbsp;&nbsp;&nbsp;&nbsp;`CeleryWorker -->|Phase 2: os.rename| SharedVolume`  
&nbsp;&nbsp;&nbsp;&nbsp;`CeleryWorker -->|Result| RedisBroker`  
&nbsp;&nbsp;&nbsp;&nbsp;`Goyongmin_BE --> PostgresDB`

&nbsp;&nbsp;&nbsp;&nbsp;`Chagawon_FE -->|Mock Mode: ON| MSW_Engine`  
&nbsp;&nbsp;&nbsp;&nbsp;`Chagawon_FE -->|Mock Mode: OFF| Chagawon_BE`  
&nbsp;&nbsp;&nbsp;&nbsp;`Chagawon_BE --> PostgresDB`  
&nbsp;&nbsp;&nbsp;&nbsp;`Chagawon_BE -.->|Proxy Fallback| Goyongmin_BE`

## **2\. Functional Requirements & Ownership Mapping**

### **2.1 기능 요구사항 명세**

&nbsp;

| ID(FR-XX) | 기능명 | 설명 | 주요 동작 | 입력값 | 출력값 | 연관 API | 주 담당자 | 우선순위 |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| **FR-001** | **임시 저장 및 2-Phase 파일 원자성 보장** | **파티션 내 이동 원자성 확보 및 3D Metric 깊이 생성** | **1\) /static/uploads/.tmp 임시 저장 2\) Celery Task 위임 3\) 성공 시 os.rename 이동** | **이미지 바이너리, EXIF 메타데이터** | **Float32 Depth 텐서, 확정 파일 경로** | POST /estimate | \[고용민\] | **P0** |
| **FR-002** | **인스턴스 세그멘테이션** | **음식 및 식기 픽셀 마스크 분할** | **YOLOv8-Seg 모델 추론** | **RGB 텐서 (1×3×*H*×*W*)** | **BBox, 바이너리 마스크** | POST /estimate | \[고용민\] | **P0** |
| **FR-003** | **RANSAC 기반 수치 이중 적분** | **3D 점군 역투영 및 바닥 피팅 체적 계산** | **1\) *fpx*​ 근사 기반 점군 역투영 2\) 평면 피팅(*ax*\+*by*\+*cz*\+*d*\=0)** | **Depth 텐서, 마스크 텐서** | **체적(*V*), 3D BBox, 평면 파라미터** | POST /estimate | \[고용민\] | **P0** |
| **FR-004** | **식품 매핑 및 영양소 산출** | **DINOv2 패치 및 mmap Faiss 기반 중량 도출** | **1\) Faiss 인덱스(mmap) 검색 2\) *W*\=*V*×*ρ* 3\) 영양소 환산** | **크롭 패치 텐서, 체적(*V*)** | **foodId, 산출 중량(*W*), 매크로 영양소** | POST /estimate | \[고용민\] | **P0** |
| **FR-005** | **WebGL 3D 시각화 점군 렌더링** | **Three.js를 이용한 결과 시각화** | **Voxel Grid 점군 다운샘플링 브라우저 렌더링** | **Sparse Point Cloud JSON** | **인터랙티브 3D 뷰 캔버스** | POST /estimate | \[차가원\] | **P1** |
| **FR-006** | **식단 영양소 합산 리포트** | **최종 확정 식단 DB 적재/조회** | **식단 트랜잭션 적재 및 기간별 쿼리** | **조회 조건 (page, 날짜)** | **식단 내역, 총합 영양소 DTO** | GET /meals | Shared | **P1** |
| **FR-007** | **SSOT 기반 수동 보정 및 이력 관리** | **클라이언트 임시 갱신, 서버 재계산 및 로깅** | **1\) UI 임시 갱신 2\) 서버 SSOT 재계산 3\) is\_user\_adjusted 플래그 및 이력 DB 갱신** | **foodId, 수정 중량(*Wmod*​)** | **서버 계산 최종 영양소 리포트** | POST /confirm | Shared | **P0** |
| **FR-008** | **신규 계정 가입 (Sign-up)** | **미인증 사용자 DB 계정 생성** | **1\) 이메일/비밀번호 수신 2\) Bcrypt 해시 3\) 201 응답 및 토큰 발급** | **Email, Password** | **201 Created** | POST /signup | \[고용민\] | **P0** |

### **2.2 예외 처리 및 유효성 검증 규칙 (Business Rules)**

> * **\[BR-VAL-001\] EXIF 메타데이터 보정**: 초점거리/센서 사이즈 부재 시 35mm 환산 72도 화각 기준 픽셀 초점거리 *fpx*​\=2×tan(72∘/2)*W*​ 산출을 강제합니다.  
> * **\[BR-VAL-002\] 바닥 평면 추정 실패**: RANSAC 평면 피팅 시 Inlier 비율이 40% 미만이면 ERR\_GEOMETRY\_PLANE\_NOT\_FOUND (422) 예외를 던집니다.  
> * **\[BR-VAL-003\] HEIC 포맷 예외 차단**: 클라이언트 업로드 이미지가 .heic 확장자이거나 헤더 시그니처가 매칭될 경우 변환 없이 415 Unsupported Media Type 예외로 즉시 차단합니다. (모바일 클라이언트에서 JPEG 변환 후 전송하도록 유도)  
> * **\[BR-VAL-004\] SSOT 수동 보정 원칙 및 로깅**: 중량 보정 시 클라이언트는 단순 비율로 UI를 즉시 반영하되, 최종 통신 시 서버가 foodId 기반 표준 프로필로 정밀 재계산(SSOT)하여 덮어쓰며, 변경 전/후 데이터는 반드시 보정 이력 테이블(meal\_correction\_logs)에 기록되어야 합니다.

## **3\. Non-Functional Requirements**

### **3.1 성능 (Performance)**

> * **순수 비즈니스 및 추론 SLA**: 서버가 네트워크 I/O를 제외한 백엔드 내부 Celery 작업 큐 대기 및 처리 시간의 P95 지표를 1,500ms(1.5초) 이하로 보장해야 합니다.  
> * **프론트엔드 WebGL 렌더링**: 다운샘플링 점군(최대 5,000점) 렌더링 시 브라우저 내 60 FPS 유지를 목표로 합니다.

### **3.2 보안 및 2-Phase 파일 생명주기**

> * **2-Phase 파일 커밋 및 롤백 (Atomic Commit)**: 파티션 교차로 인한 shutil.move 트랜잭션 붕괴를 방지하기 위해 파일은 최종 목적지와 동일한 파티션 내의 /static/uploads/.tmp/{uuid}.jpg에 선저장됩니다. Celery 연산(타임아웃 5.0초) 중 실패 또는 OOM 발생 시 finally 블록에서 os.unlink()로 고아 파일을 완벽히 삭제합니다. 연산 성공 시 os.rename()으로 /static/uploads/meals/ 로 원자적 이동을 수행합니다.  
> * **Faiss 인덱스 RAM 공유**: DINOv2용 벡터 검색 DB는 Celery Worker 시작 시 RAM 고갈을 막기 위해 mmap 방식으로 로드하여 OS 레벨 메모리 맵핑을 강제합니다.  
> * **쿠키 정책**: JWT Access/Refresh 토큰은 1st-party 환경이므로 SameSite=Strict, HttpOnly=True 플래그를 100% 강제 적용합니다.

### **3.3 원격 자원 격리 원칙**

> * **포트 포워딩 바인딩 규칙**: VS Code 원격 터널 및 호환성을 위해 모든 개발 서버 바인딩은 127.0.0.1이 아닌 0.0.0.0으로 고정합니다.  
  * **공통 인프라**: PostgreSQL (5432), Redis (6379)  
  * **개발자 1 \[고용민\]**: Backend (8001), Frontend (3001)  
  * **개발자 2 \[차가원\]**: Backend (8002), Frontend (3002)  
> * **GPU 샌드박싱 제한**: Celery Worker 데몬 부트스트랩 시 torch.cuda.set\_per\_process\_memory\_fraction(0.43)을 적용하여 VRAM 사용량을 14GB 한도로 락(Lock)합니다.  
> * **Linux 파일 권한**: 모노레포 폴더 및 Docker 볼륨의 root 권한 점유 방지를 위해 컨테이너 기동 시 호스트 사용자의 UID/GID 주입 및 umask 002를 적용합니다.

## **4\. Tech Stack & Dependencies**

&nbsp;

| 영역 | 기술 | 권장 버전 | 용도 | 선택 근거 및 담당자 |
| :---- | :---- | :---- | :---- | :---- |
| **Backend Core** | **Python / FastAPI** | **3.10 / 0.111+** | **비동기 API 서버** | **PyTorch 생태계 네이티브 연동** \[고용민\] |
| **Async Worker** | **Celery / Redis** | **5.3+ / 7.2** | **GPU 샌드박스 오프로딩 큐** | **OOM 강제 롤백 및 Worker 1:1 격리 제어** \[고용민\] |
| **Database** | **PostgreSQL** | **15** | **데이터 영속성** | **JSONB 점군 데이터 트랜잭션 관리** \[고용민\] |
| **ML/Geometry** | **PyTorch 2.3+ / Faiss** | **CUDA 12.8+** | **비전 추론 및 벡터 검색** | mmap **인메모리 공유 및 RTX 5090 가속** \[고용민\] |
| **File I/O** | **aiofiles / os** | **Native** | **2-Phase 원자적 커밋** | .tmp **비동기 저장 및** os.rename **이동** \[고용민\] |
| **Frontend Core** | **Next.js (App Router)** | **14.2+** | **UI 클라이언트** | **RSC 기반 렌더링 속도 최적화** \[차가원\] |
| **Client State** | **Zustand / TanStack Query** | **4.5+ / 5.35+** | **전역 상태 / 서버 캐싱** | **SSOT 서버 응답 동기화 및 API 무효화** \[차가원\] |
| **3D Rendering** | **Three.js / R3F** | **0.164+** | **WebGL 캔버스 출력** | **브라우저 내 경량화된 Point Cloud 렌더링** \[차가원\] |
| **Contracts** | **Zod** | **3.23+** | **SSOT 런타임 검증** | **백\-프론트 타입 1:1 강제 일치(Drift 방지)** \[Shared\] |
| **API Mocking** | **MSW** | **2.3+** | **브라우저 가로채기** | **백엔드 의존 없는 선제적 UI 병렬 구현** \[차가원\] |
| **Cloud Hosting** | **Vercel (PaaS)** | **Edge / Serverless** | **프론트엔드 프로덕션 배포** | **랩실 네트워크 분리, 24시간 무중단 심사 링크(HTTPS) 제공** \[차가원\] |

## **5\. System Architecture & Collaboration Data Flow**

### **5.1 End-to-End 시퀀스 (Celery 2-Phase Commit 반영)**

다음은 요청 처리 라이프사이클을 나타내는 End-to-End 시퀀스 다이어그램입니다.

`sequenceDiagram`  
&nbsp;&nbsp;&nbsp;&nbsp;`autonumber`  
&nbsp;&nbsp;&nbsp;&nbsp;`actor User`  
&nbsp;&nbsp;&nbsp;&nbsp;`participant FE as Next.js [차가원]`  
&nbsp;&nbsp;&nbsp;&nbsp;`participant BE as FastAPI [고용민]`  
&nbsp;&nbsp;&nbsp;&nbsp;`participant Tmp as /static/uploads/.tmp`  
&nbsp;&nbsp;&nbsp;&nbsp;`participant Broker as Redis (Celery)`  
&nbsp;&nbsp;&nbsp;&nbsp;`participant Worker as Celery Worker (GPU)`  
&nbsp;&nbsp;&nbsp;&nbsp;`participant DB as Postgres [고용민]`  
&nbsp;&nbsp;&nbsp;&nbsp;`participant Static as /static/uploads/meals`

&nbsp;&nbsp;&nbsp;&nbsp;`User->>FE: 촬영 및 업로드 (HEIC는 FE/BE에서 415 차단)`  
&nbsp;&nbsp;&nbsp;&nbsp;`FE->>BE: POST /api/v1/vision/estimate (Multipart)`  
&nbsp;&nbsp;&nbsp;&nbsp;`activate BE`  
&nbsp;&nbsp;&nbsp;&nbsp;`BE->>Tmp: [Phase 1] aiofiles.write() 동일 파티션 내 임시 저장`  
&nbsp;&nbsp;&nbsp;&nbsp;`BE->>Broker: delay() Task 발행 및 대기 (Timeout 5s)`  
&nbsp;&nbsp;&nbsp;&nbsp;`Broker->>Worker: Task Consume`  
&nbsp;&nbsp;&nbsp;&nbsp;`activate Worker`  
&nbsp;&nbsp;&nbsp;&nbsp;  
&nbsp;&nbsp;&nbsp;&nbsp;`alt CUDA OOM or Worker Crash`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`Worker--xBroker: Task Revoked / Exception`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`Broker-->>BE: Celery Timeout/Error`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`BE->>Tmp: os.unlink() 롤백 삭제`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`BE-->>FE: HTTP 503 / 504 Error`  
&nbsp;&nbsp;&nbsp;&nbsp;`else 추론 성공`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`Worker->>Worker: DINOv2 + Faiss (mmap) + Geometry`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`Worker->>Static: [Phase 2] os.rename() 원자적 이동`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`Worker-->>Broker: V(cm3), BBox, DINOv2 Result`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`deactivate Worker`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`Broker-->>BE: Task Result 반환`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`BE->>DB: INSERT meals, meal_food_items`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`BE-->>FE: HTTP 200 OK (imageUrl, Data)`  
&nbsp;&nbsp;&nbsp;&nbsp;`end`  
&nbsp;&nbsp;&nbsp;&nbsp;`deactivate BE`  
&nbsp;&nbsp;&nbsp;&nbsp;`FE-->>User: 3D Point Cloud 렌더링`

### **5.2 단일 머신 2인 병렬 개발 흐름도**

> * **\[고용민\]**: 0.0.0.0:8001에서 FastAPI를, 백그라운드 터미널에서 Celery Worker를 기동. Redis를 통해 Task 큐잉을 테스트하며 인프라/GPU 안정성에 집중합니다.  
> * **\[차가원\]**: 0.0.0.0:3002 실행. NEXT\_PUBLIC\_API\_MOCKING=true 상태로 MSW가 HTTP 호출을 인터셉트하여 Mock JSON을 응답합니다. 프론트엔드 작업 완료 후 환경변수를 false로 스위칭하여 8001 포트로 즉시 통합 연동합니다.

## **6\. Directory Structure & Code Ownership Map**

다음은 모노레포 전체 Tree 구조와 파일별 책임자 명세입니다.

`volumeal-align/`  
`├── docker-compose.yml                      # [Shared] Postgres, Redis 자원 및 UID/GID 매핑`  
`├── .vscode/                                # [Shared]`  
`│   ├── settings.json                       # 원격 포맷터 및 공통 세팅`  
`│   └── launch.json                         # 8001(BE) / 3002(FE) 포트 디버거 구성`  
`├── packages/contracts/                     # [Shared] SSOT 스키마 (변경 시 양측 합의 필수)`  
`│   └── src/`  
`│       ├── schemas/vision.ts               # Zod API 스키마 및 Request/Response 계약`  
`│       └── types/index.ts                  # Zod에서 추론된 TypeScript 타입`  
`├── backend/                                # Owner: [고용민]`  
`│   ├── static/uploads/`&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;  
`│   │   ├── .tmp/                           # Phase 1: 임시 저장소 (동일 파티션)`  
`│   │   └── meals/                          # Phase 2: os.rename 목적지`  
`│   └── app/`  
`│       ├── main.py`  
`│       ├── worker/`  
`│       │   └── celery_app.py               # Celery Worker Daemon 및 OOM 통제`  
`│       ├── api/v1/endpoints/`  
`│       │   ├── auth.py                     # /signup, /login 라우터`  
`│       │   └── vision.py                   # /estimate, /confirm 라우터`  
`│       ├── services/`  
`│       │   ├── storage_service.py          # 2-Phase 파일 원자성 커밋 및 롤백 제어`  
`│       │   └── geometry_service.py         # 72도 FOV $f_{px}$ 산출`  
`│       └── ml/`  
`│           ├── ransac_integrator.py`  
`│           └── patch_embedder.py           # Faiss (mmap) 인덱스 로드 및 매핑`  
`└── frontend/                               # Owner: [차가원]`  
&nbsp;&nbsp;&nbsp;&nbsp;`├── public/mockServiceWorker.js`  
&nbsp;&nbsp;&nbsp;&nbsp;`└── src/`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`├── mocks/`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`│   └── fixtures/estimate_mock.json # Contract-First 목업 응답 데이터`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`├── stores/`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`│   └── useMealCorrectionStore.ts   # 수동 보정 UI 갱신 Zustand 스토어`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`└── components/viewer3d/`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`└── ThreeCanvas.tsx             # Point Cloud WebGL 렌더러`

Turn 2(섹션 7\~10)를 출력할까요?

---

*User prompt: Turn2*

# **Response: Technical Specification: VoluMeal-Align \- Turn 2**

## **7\. Database Schema & Seed Data**

### **7.1 데이터베이스 스키마 정의**

모든 테이블은 PostgreSQL 15 규격을 따르며, 데이터 무결성 및 감사(Audit)를 위해 created\_at 및 updated\_at 컬럼을 의무 적용합니다. 모든 테이블 및 컬럼 설계의 소유권(Primary Owner)은 \[고용민\]에게 있습니다.

**7.1.1 users 테이블 \[FR-008\]** 시스템 사용자 계정 및 권한 제어를 관리합니다.

&nbsp;

| Column | Data Type | Constraints | Default | Index | Description | Primary Owner |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| **id** | **UUID** | **PRIMARY KEY** | **gen\_random\_uuid()** | **BTREE** | **사용자 고유 식별자** | \[고용민\] |
| **email** | **VARCHAR(255)** | **NOT NULL, UNIQUE** | **\-** | **BTREE** | **로그인 이메일** | \[고용민\] |
| **password\_hash** | **VARCHAR(255)** | **NOT NULL** | **\-** | **\-** | **Bcrypt(Cost: 12\) 해시** | \[고용민\] |
| **role** | **VARCHAR(20)** | **NOT NULL** | **'USER'** | **\-** | **권한 ('USER', 'ADMIN')** | \[고용민\] |
| **created\_at** | **TIMESTAMPTZ** | **NOT NULL** | **CURRENT\_TIMESTAMP** | **\-** | **레코드 생성 일시** | \[고용민\] |
| **updated\_at** | **TIMESTAMPTZ** | **NOT NULL** | **CURRENT\_TIMESTAMP** | **\-** | **레코드 변경 일시** | \[고용민\] |

**7.1.2 meals 테이블 \[FR-001, FR-006\]** 단일 식단 분석 마스터 데이터와 확정된 정적 파일 경로, 합산 영양소를 저장합니다.

&nbsp;

| Column | Data Type | Constraints | Default | Index | Description | Primary Owner |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| **id** | **UUID** | **PRIMARY KEY** | **gen\_random\_uuid()** | **BTREE** | **식단 분석 고유 식별자** | \[고용민\] |
| **user\_id** | **UUID** | **NOT NULL, FK(users.id) ON DELETE CASCADE** | **\-** | **BTREE** | **분석 소유자 식별자** | \[고용민\] |
| **image\_url** | **VARCHAR(1024)** | **NOT NULL** | **\-** | **\-** | **정적 디스크 영속 저장 경로** | \[고용민\] |
| **focal\_length\_mm** | **NUMERIC(6,2)** | **NOT NULL** | **26.00** | **\-** | ***fpx*****​ 근사에 사용된 초점거리** | \[고용민\] |
| **status** | **VARCHAR(20)** | **NOT NULL** | **'ESTIMATED'** | **BTREE** | **상태 ('ESTIMATED', 'CONFIRMED')** | \[고용민\] |
| **total\_calories** | **NUMERIC(8,2)** | **NOT NULL** | **0.00** | **\-** | **전체 열량(kcal) 합산** | \[고용민\] |
| **total\_carbs** | **NUMERIC(8,2)** | **NOT NULL** | **0.00** | **\-** | **전체 탄수화물(g) 합산** | \[고용민\] |
| **total\_protein** | **NUMERIC(8,2)** | **NOT NULL** | **0.00** | **\-** | **전체 단백질(g) 합산** | \[고용민\] |
| **total\_fat** | **NUMERIC(8,2)** | **NOT NULL** | **0.00** | **\-** | **전체 지방(g) 합산** | \[고용민\] |
| **created\_at** | **TIMESTAMPTZ** | **NOT NULL** | **CURRENT\_TIMESTAMP** | **BTREE** | **식단 분석 요청 일시** | \[고용민\] |
| **updated\_at** | **TIMESTAMPTZ** | **NOT NULL** | **CURRENT\_TIMESTAMP** | **\-** | **확정/보정 변경 일시** | \[고용민\] |

**7.1.3 meal\_food\_items 테이블 \[FR-003, FR-004, FR-007\]** 분석된 개별 음식의 기하학 정보 및 산출 영양소를 저장합니다.

&nbsp;

| Column | Data Type | Constraints | Default | Index | Description | Primary Owner |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| **id** | **UUID** | **PRIMARY KEY** | **gen\_random\_uuid()** | **BTREE** | **개별 음식 객 식별자** | \[고용민\] |
| **meal\_id** | **UUID** | **NOT NULL, FK(meals.id) ON DELETE CASCADE** | **\-** | **BTREE** | **상위 식단 마스터 식별자** | \[고용민\] |
| **food\_id** | **VARCHAR(64)** | **NOT NULL** | **\-** | **BTREE** | **표준 식품 카탈로그 ID** | \[고용민\] |
| **food\_name** | **VARCHAR(100)** | **NOT NULL** | **\-** | **\-** | **매핑된 표준 식품명** | \[고용민\] |
| **volume\_cm3** | **NUMERIC(8,2)** | **NOT NULL** | **\-** | **\-** | **RANSAC 이중 적분 부피** | \[고용민\] |
| **weight\_g** | **NUMERIC(8,2)** | **NOT NULL** | **\-** | **\-** | **산출 중량** | \[고용민\] |
| **calories** | **NUMERIC(8,2)** | **NOT NULL** | **\-** | **\-** | **비례 산출 열량** | \[고용민\] |
| **carbs** | **NUMERIC(8,2)** | **NOT NULL** | **\-** | **\-** | **비례 산출 탄수화물** | \[고용민\] |
| **protein** | **NUMERIC(8,2)** | **NOT NULL** | **\-** | **\-** | **비례 산출 단백질** | \[고용민\] |
| **fat** | **NUMERIC(8,2)** | **NOT NULL** | **\-** | **\-** | **비례 산출 지방** | \[고용민\] |
| **is\_user\_adjusted** | **BOOLEAN** | **NOT NULL** | **FALSE** | **\-** | **수동 보정 여부 (SSOT 마커)** | \[고용민\] |
| **created\_at** | **TIMESTAMPTZ** | **NOT NULL** | **CURRENT\_TIMESTAMP** | **\-** | **레코드 생성 일시** | \[고용민\] |
| **updated\_at** | **TIMESTAMPTZ** | **NOT NULL** | **CURRENT\_TIMESTAMP** | **\-** | **레코드 변경 일시** | \[고용민\] |

**7.1.4 meal\_correction\_logs 테이블 \[FR-007\]** SSOT 원칙에 따라 사용자 수동 보정 시 변경 이력을 영구 보존합니다.

&nbsp;

| Column | Data Type | Constraints | Default | Index | Description | Primary Owner |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| **id** | **UUID** | **PRIMARY KEY** | **gen\_random\_uuid()** | **BTREE** | **보정 이력 고유 식별자** | \[고용민\] |
| **meal\_food\_item\_id** | **UUID** | **NOT NULL, FK(meal\_food\_items.id)** | **\-** | **BTREE** | **대상 음식 식별자** | \[고용민\] |
| **original\_weight\_g** | **NUMERIC(8,2)** | **NOT NULL** | **\-** | **\-** | **보정 전 기존 중량** | \[고용민\] |
| **new\_weight\_g** | **NUMERIC(8,2)** | **NOT NULL** | **\-** | **\-** | **보정 후 신규 중량** | \[고용민\] |
| **created\_at** | **TIMESTAMPTZ** | **NOT NULL** | **CURRENT\_TIMESTAMP** | **BTREE** | **로그 생성 일시** | \[고용민\] |

### **7.2 Entity-Relationship Diagram (Mermaid)**

`erDiagram`  
&nbsp;&nbsp;&nbsp;&nbsp;`users ||--o{ meals : "owns"`  
&nbsp;&nbsp;&nbsp;&nbsp;`meals ||--|{ meal_food_items : "contains"`  
&nbsp;&nbsp;&nbsp;&nbsp;`meal_food_items ||--o{ meal_correction_logs : "tracks_history"`

&nbsp;&nbsp;&nbsp;&nbsp;`users {`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`UUID id PK`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`VARCHAR email UK`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`VARCHAR password_hash`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`VARCHAR role`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`TIMESTAMPTZ created_at`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`TIMESTAMPTZ updated_at`  
&nbsp;&nbsp;&nbsp;&nbsp;`}`

&nbsp;&nbsp;&nbsp;&nbsp;`meals {`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`UUID id PK`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`UUID user_id FK`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`VARCHAR image_url`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`NUMERIC focal_length_mm`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`VARCHAR status`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`NUMERIC total_calories`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`NUMERIC total_carbs`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`NUMERIC total_protein`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`NUMERIC total_fat`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`TIMESTAMPTZ created_at`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`TIMESTAMPTZ updated_at`  
&nbsp;&nbsp;&nbsp;&nbsp;`}`

&nbsp;&nbsp;&nbsp;&nbsp;`meal_food_items {`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`UUID id PK`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`UUID meal_id FK`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`VARCHAR food_id`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`VARCHAR food_name`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`NUMERIC volume_cm3`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`NUMERIC weight_g`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`NUMERIC calories`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`NUMERIC carbs`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`NUMERIC protein`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`NUMERIC fat`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`BOOLEAN is_user_adjusted`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`TIMESTAMPTZ created_at`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`TIMESTAMPTZ updated_at`  
&nbsp;&nbsp;&nbsp;&nbsp;`}`

&nbsp;&nbsp;&nbsp;&nbsp;`meal_correction_logs {`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`UUID id PK`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`UUID meal_food_item_id FK`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`NUMERIC original_weight_g`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`NUMERIC new_weight_g`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`TIMESTAMPTZ created_at`  
&nbsp;&nbsp;&nbsp;&nbsp;`}`

### **7.3 Local Verification Seed Data (backend/app/data/seed.sql)**

프론트엔드 개발자(차가원)가 로컬 DB 포트(5432)에 직접 접근하여 독립적인 UI 렌더링 및 이력 조회 테스트를 수행할 수 있도록 기본 데이터를 적재합니다. Owner: **\[고용민\]**

`-- 1. 사용자 계정 시드 (Password: 'Test1234!')`  
`INSERT INTO users (id, email, password_hash, role, created_at, updated_at)`  
`VALUES`  
&nbsp;&nbsp;`('a0000000-0000-0000-0000-000000000001', 'admin@volumeal.io', '$2b$12$KIXH/C./T21GjEa8f6Tf5.RMBF4Q.R1sWlX6p8oFh1c8F3Yd6pQxK', 'ADMIN', NOW(), NOW()),`  
&nbsp;&nbsp;`('a0000000-0000-0000-0000-000000000002', 'test@volumeal.io', '$2b$12$KIXH/C./T21GjEa8f6Tf5.RMBF4Q.R1sWlX6p8oFh1c8F3Yd6pQxK', 'USER', NOW(), NOW())`  
`ON CONFLICT (id) DO NOTHING;`

`-- 2. 식단 마스터 시드`  
`INSERT INTO meals (id, user_id, image_url, focal_length_mm, status, total_calories, total_carbs, total_protein, total_fat, created_at, updated_at)`  
`VALUES (`  
&nbsp;&nbsp;`'f47ac10b-58cc-4372-a567-0e02b2c3d479', 'a0000000-0000-0000-0000-000000000002',`  
&nbsp;&nbsp;`'/static/uploads/meals/seed_sample.jpg', 26.00, 'ESTIMATED',`  
&nbsp;&nbsp;`250.00, 30.50, 15.20, 7.40, NOW(), NOW()`  
`) ON CONFLICT (id) DO NOTHING;`

`-- 3. 개별 음식 시드`  
`INSERT INTO meal_food_items (id, meal_id, food_id, food_name, volume_cm3, weight_g, calories, carbs, protein, fat, is_user_adjusted, created_at, updated_at)`  
`VALUES (`  
&nbsp;&nbsp;`'e1a2b3c4-0001-4000-8000-000000000001', 'f47ac10b-58cc-4372-a567-0e02b2c3d479',`  
&nbsp;&nbsp;`'FOOD_001', '제육볶음', 120.00, 150.00, 250.00, 30.50, 15.20, 7.40, FALSE, NOW(), NOW()`  
`) ON CONFLICT (id) DO NOTHING;`

## **8\. API Specifications & Contract-First Interfaces**

### **8.1 REST 엔드포인트 테이블**

&nbsp;

| Method | Endpoint | Auth | Producer | Consumer | FR-ID |
| :---- | :---- | :---- | :---- | :---- | :---- |
| **POST** | /api/v1/auth/signup | **No** | \[고용민\] | \[차가원\] | **FR-008** |
| **POST** | /api/v1/auth/login | **No** | \[고용민\] | \[차가원\] | **FR-008** |
| **POST** | /api/v1/auth/logout | **Yes** | \[고용민\] | \[차가원\] | **FR-008** |
| **POST** | /api/v1/vision/estimate | **Yes** | \[고용민\] | \[차가원\] | **FR-001\~005** |
| **POST** | /api/v1/vision/confirm | **Yes** | \[고용민\] | \[차가원\] | **FR-007** |
| **GET** | /api/v1/meals | **Yes** | \[고용민\] | \[차가원\] | **FR-006** |

### **8.2 Zod Validation Schema & TypeScript Types**

프론트엔드와 백엔드 간 타입 불일치를 완벽히 차단하기 위한 SSOT 계약 레이어입니다. 수정 시 반드시 양측 합의가 필요합니다. Owner: **\[공통/Shared\]**

packages/contracts/src/schemas/vision.ts

`import { z } from 'zod';`

`export const MacroNutrientsSchema = z.object({`  
&nbsp;&nbsp;`calories: z.number().nonnegative(),`  
&nbsp;&nbsp;`carbs: z.number().nonnegative(),`  
&nbsp;&nbsp;`protein: z.number().nonnegative(),`  
&nbsp;&nbsp;`fat: z.number().nonnegative(),`  
`});`

`export const SparsePointCloudSchema = z.object({`  
&nbsp;&nbsp;`count: z.number().int().nonnegative(),`  
&nbsp;&nbsp;`positions: z.array(z.number()),`  
&nbsp;&nbsp;`colors: z.array(z.number()),`  
`});`

`export const FoodItemEstimationSchema = z.object({`  
&nbsp;&nbsp;`id: z.string().uuid(),`  
&nbsp;&nbsp;`foodId: z.string().min(1),`  
&nbsp;&nbsp;`foodName: z.string().min(1),`  
&nbsp;&nbsp;`volumeCm3: z.number().positive(),`  
&nbsp;&nbsp;`weightG: z.number().positive(),`  
&nbsp;&nbsp;`nutrients: MacroNutrientsSchema,`  
&nbsp;&nbsp;`isUserAdjusted: z.boolean().default(false),`  
`});`

`export const MealEstimateResponseSchema = z.object({`  
&nbsp;&nbsp;`mealId: z.string().uuid(),`  
&nbsp;&nbsp;`imageUrl: z.string().min(1),`  
&nbsp;&nbsp;`focalLengthMm: z.number().positive(),`  
&nbsp;&nbsp;`totalNutrition: MacroNutrientsSchema,`  
&nbsp;&nbsp;`foodItems: z.array(FoodItemEstimationSchema),`  
&nbsp;&nbsp;`visualization3d: z.object({`  
&nbsp;&nbsp;&nbsp;&nbsp;`pointCloud: SparsePointCloudSchema,`  
&nbsp;&nbsp;`}),`  
&nbsp;&nbsp;`processedAt: z.string().datetime(),`  
`});`

`export const MealConfirmRequestSchema = z.object({`  
&nbsp;&nbsp;`mealId: z.string().uuid(),`  
&nbsp;&nbsp;`corrections: z.array(`  
&nbsp;&nbsp;&nbsp;&nbsp;`z.object({`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`foodItemId: z.string().uuid(),`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`correctedWeightG: z.number().positive(),`  
&nbsp;&nbsp;&nbsp;&nbsp;`})`  
&nbsp;&nbsp;`),`  
`});`

`// 타입 추론 익스포트`  
`export type MacroNutrients = z.infer<typeof MacroNutrientsSchema>;`  
`export type FoodItemEstimation = z.infer<typeof FoodItemEstimationSchema>;`  
`export type MealEstimateResponse = z.infer<typeof MealEstimateResponseSchema>;`  
`export type MealConfirmRequest = z.infer<typeof MealConfirmRequestSchema>;`

### **8.3 Frontend 독립 개발용 Mock JSON Data**

MSW 가로채기(Mocking) 응답 명세입니다. 이를 통해 백엔드(Celery/GPU) 구동과 무관하게 UI 및 상태 스토어를 즉시 구축합니다. Owner: **\[차가원\]**

frontend/src/mocks/fixtures/estimate\_mock.json

`{`  
&nbsp;&nbsp;`"success": true,`  
&nbsp;&nbsp;`"data": {`  
&nbsp;&nbsp;&nbsp;&nbsp;`"mealId": "f47ac10b-58cc-4372-a567-0e02b2c3d479",`  
&nbsp;&nbsp;&nbsp;&nbsp;`"imageUrl": "/static/uploads/meals/mock_output_123.jpg",`  
&nbsp;&nbsp;&nbsp;&nbsp;`"focalLengthMm": 26.0,`  
&nbsp;&nbsp;&nbsp;&nbsp;`"totalNutrition": {`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`"calories": 250.00,`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`"carbs": 30.50,`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`"protein": 15.20,`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`"fat": 7.40`  
&nbsp;&nbsp;&nbsp;&nbsp;`},`  
&nbsp;&nbsp;&nbsp;&nbsp;`"foodItems": [`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`{`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`"id": "e1a2b3c4-0001-4000-8000-000000000001",`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`"foodId": "FOOD_001",`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`"foodName": "제육볶음",`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`"volumeCm3": 120.00,`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`"weightG": 150.00,`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`"nutrients": {`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`"calories": 250.00,`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`"carbs": 30.50,`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`"protein": 15.20,`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`"fat": 7.40`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`},`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`"isUserAdjusted": false`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`}`  
&nbsp;&nbsp;&nbsp;&nbsp;`],`  
&nbsp;&nbsp;&nbsp;&nbsp;`"visualization3d": {`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`"pointCloud": {`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`"count": 2,`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`"positions": [0.12, -0.04, 0.48, 0.13, -0.03, 0.47],`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`"colors": [0.18, 0.45, 0.22, 0.20, 0.48, 0.24]`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`}`  
&nbsp;&nbsp;&nbsp;&nbsp;`},`  
&nbsp;&nbsp;&nbsp;&nbsp;`"processedAt": "2026-09-16T15:30:00.000Z"`  
&nbsp;&nbsp;`}`  
`}`

## **9\. Authentication & Authorization**

### **9.1 인증 라이프사이클 및 보안 정책**

> * **저장 위치**: 브라우저 localStorage를 통한 토큰 보관을 절대 금지합니다.  
> * **쿠키 규격**:  
  * access\_token: Max-Age 900초(15분), HttpOnly=True, SameSite=Strict.  
  * refresh\_token: Max-Age 604800초(7일), HttpOnly=True, SameSite=Strict, Path=/api/v1/auth.  
> * **CORS 및 포트 매핑**: 0.0.0.0:3001 (고용민 FE) 및 0.0.0.0:3002 (차가원 FE)의 요청에 대해 Access-Control-Allow-Credentials: true를 허용하도록 FastAPI 미들웨어를 구성합니다. Owner: **\[고용민\]**

### **9.2 클라이언트 토큰 갱신 인터셉터 (Refresh Queue)**

401 Unauthorized 응답 발생 시, 동시다발적인 /refresh API 중복 호출 방지를 위해 Axios Interceptor 내부 Queue(큐)를 활용하여 첫 번째 요청이 갱신될 때까지 나머지 요청을 대기시킨 후 일괄 재시도합니다. Owner: **\[차가원\]**

### **9.3 RBAC 권한 매트릭스 테이블**

&nbsp;

| 경로 | GUEST | USER | ADMIN | 인터셉터/가드 검증 로직 |
| :---- | :---- | :---- | :---- | :---- |
| /api/v1/auth/signup | **허용** | **차단** | **차단** | **미인증 상태 확인** |
| /api/v1/auth/login | **허용** | **차단** | **차단** | **미인증 상태 확인** |
| /api/v1/vision/estimate | **차단** | **허용** | **허용** | **유효한 access\_token 파싱** |
| /api/v1/vision/confirm | **차단** | **허용** | **허용** | meal.user\_id \== current\_user.id **(IDOR 방어)** |

## **10\. Error Handling & Hardware Safeguards**

### **10.1 전역 표준 에러 응답 규격**

시스템에서 발생하는 모든 예외는 표준화된 JSON 포맷으로 반환됩니다.

`{`  
&nbsp;&nbsp;`"success": false,`  
&nbsp;&nbsp;`"error": {`  
&nbsp;&nbsp;&nbsp;&nbsp;`"code": "ERR_HEIC_UNSUPPORTED",`  
&nbsp;&nbsp;&nbsp;&nbsp;`"message": "HEIC 포맷은 서버에서 지원하지 않습니다. 클라이언트에서 JPEG로 변환 후 업로드하세요.",`  
&nbsp;&nbsp;&nbsp;&nbsp;`"timestamp": "2026-09-16T15:35:10.000Z",`  
&nbsp;&nbsp;&nbsp;&nbsp;`"path": "/api/v1/vision/estimate",`  
&nbsp;&nbsp;&nbsp;&nbsp;`"details": []`  
&nbsp;&nbsp;`}`  
`}`

### **10.2 시스템 에러 매핑 테이블**

&nbsp;

| HTTP Status | Internal Error Code | 발생 조건 | 대응 메커니즘 |
| :---- | :---- | :---- | :---- |
| **400 Bad Request** | ERR\_INVALID\_PAYLOAD | **필수 필드 누락 또는 Zod 검증 실패** | **프론트엔드 Form 검증 유도** |
| **401 Unauthorized** | ERR\_TOKEN\_EXPIRED | **JWT Access Token 만료** | **FE Axios Interceptor 갱신 트리거** |
| **403 Forbidden** | ERR\_ACCESS\_DENIED | **본인 소유가 아닌 식단 리소스 접근** | **즉시 거부 (IDOR 방어)** |
| **415 Unsupported** | ERR\_HEIC\_UNSUPPORTED | image/heic **또는 매직 바이트 HEIC 감지** | **\[BR-VAL-003\]에 따른 즉시 차단** |
| **422 Unprocessable** | ERR\_PLANE\_NOT\_FOUND | **RANSAC 테이블 바닥 평면 Inlier 40% 미만** | **사용자 재촬영 유도 가이드라인 제공** |
| **429 Too Many Req** | ERR\_RATE\_LIMIT | **분당 API 호출 한도 초과** | **Redis Sliding Window 기반 쓰로틀링** |
| **503 Service Unavail** | ERR\_CELERY\_OOM | **Worker VRAM 할당 한도 도달 및 Crash** | **Worker OS 레벨 재시작 및 롤백** |
| **504 Gateway Timeout** | ERR\_CELERY\_TIMEOUT | **Celery Task 5.0초 초과** | **Task Revoke 및 임시 파일 삭제** |

### **10.3 하드웨어 예외 처리 가이드라인**

단일 서버 2인 병렬 개발 환경 내 자원 격리와 생존성을 보장하기 위한 안전장치입니다. Owner: **\[고용민\]**

> 1. **포트 점유 방어 (check\_ports.py)**: 서버 부트스트랩 시 0.0.0.0 호스트에 바인딩하려는 포트(8001, 8002)가 이미 사용 중(EADDRINUSE)일 경우, FastAPI 구동을 즉시 중단하고 명확한 터미널 에러를 출력합니다.  
> 2. **Celery Worker OOM 쉴드**: 비동기 작업 큐에서 PyTorch의 torch.cuda.OutOfMemoryError가 포착되거나 데몬 자체가 OS에 의해 Kill 당할 경우, Redis Broker는 해당 Task를 실패 처리합니다. FastAPI 메인 프로세스는 이를 503 예외로 감지하여 즉각 클라이언트에 전파합니다.  
> 3. **2-Phase 파일 원자성 롤백**: Celery Timeout(504) 또는 OOM(503) 발생 시, 백엔드의 Exception Handler는 /static/uploads/.tmp/에 기록된 1단계 임시 파일을 os.unlink()로 완벽히 삭제하여 디스크 누수와 고아(Orphan) 파일을 차단합니다.

Turn 3(섹션 11\~16)을 출력할까요?

---

*User prompt: Turn3*

# **Response: Technical Specification: VoluMeal-Align \- Turn 3**

## **11\. Testing Strategy**

### **11.1 Unit Test (단위 테스트)**

외부 인프라(DB, Redis, GPU 실제 연산) 의존성을 배제하고, 순수 비즈니스 로직과 기하 연산, 클라이언트 상태 관리의 정확성을 검증합니다.

&nbsp;

| Test Suite | 대상 파일 | 검증 시나리오 및 경계 조건 | 기대 결과 | 연관 FR | 주 담당자 |
| :---- | :---- | :---- | :---- | :---- | :---- |
| test\_geometry\_fpx | backend/app/services/geometry\_service.py | **EXIF 부재 시 35mm 환산 72도 기반 *fpx*​ 근사 산출** | **화각 72∘ 기준 픽셀 초점거리 오차 ≤1%** | **FR-001** | \[고용민\] |
| test\_ransac\_volume | backend/app/ml/ransac\_integrator.py | **가상 평면 위의 점군 배열 피팅 및 체적(*V*) 적분** | **법선 벡터 각도 오차 ≤1.5∘, 체적 오차 ≤2.0%** | **FR-003** | \[고용민\] |
| test\_nutrition\_calc | backend/app/ml/patch\_embedder.py | **매핑된 밀도(*ρ*\=0.85)와 *V*\=120 주입** | **중량 102g, 매크로 영양소 정밀 비례 계산 일치** | **FR-004** | \[고용민\] |
| test\_ui\_correction | frontend/src/stores/useMealCorrectionStore.ts | **150g에서 180g으로 수동 변경 시 클라이언트 임시 계산** | **영양소 산출 비례(180/150) 일치 확인 (Zustand)** | **FR-007** | \[차가원\] |
| test\_file\_validator | frontend/src/utils/fileValidator.ts | .heic **확장자 및 매직 바이트 파일 업로드 시도** | false **반환 및 브라우저 레벨 경고 트리거** | **FR-001** | \[차가원\] |

### **11.2 Integration Test (통합 테스트)**

2-Phase Commit 파일 관리 및 Celery Task 롤백 전략을 통합 검증합니다. 비전 모델 추론은 FakeCeleryWorker로 모킹(Mocking)합니다.

백엔드 파이프라인 통합 테스트 (backend/tests/integration/test\_pipeline.py) Owner: **\[고용민\]**

`import pytest`  
`import os`  
`from httpx import AsyncClient`  
`from app.main import app`

`@pytest.mark.asyncio`  
`async def test_estimate_2phase_commit_and_rollback(async_client: AsyncClient, auth_cookies: dict):`  
&nbsp;&nbsp;&nbsp;&nbsp;`# 1. 가상 이미지 바이너리 파일 업로드`  
&nbsp;&nbsp;&nbsp;&nbsp;`file_bytes = b"\xFF\xD8\xFF_fake_jpeg_data"`  
&nbsp;&nbsp;&nbsp;&nbsp;  
&nbsp;&nbsp;&nbsp;&nbsp;`# 2. 강제 예외 발생을 유도하는 헤더 주입 (Mock Worker에서 인식)`  
&nbsp;&nbsp;&nbsp;&nbsp;`response = await async_client.post(`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`"/api/v1/vision/estimate",`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`files={"file": ("test.jpg", file_bytes, "image/jpeg")},`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`cookies=auth_cookies,`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`headers={"X-Test-Force-Fail": "OOM"}`  
&nbsp;&nbsp;&nbsp;&nbsp;`)`  
&nbsp;&nbsp;&nbsp;&nbsp;  
&nbsp;&nbsp;&nbsp;&nbsp;`# 3. 503 응답 확인 및 .tmp 폴더 내 고아 파일(Orphan file) 삭제 확인`  
&nbsp;&nbsp;&nbsp;&nbsp;`assert response.status_code == 503`  
&nbsp;&nbsp;&nbsp;&nbsp;`res_data = response.json()`  
&nbsp;&nbsp;&nbsp;&nbsp;`assert res_data["error"]["code"] == "ERR_CELERY_OOM"`  
&nbsp;&nbsp;&nbsp;&nbsp;  
&nbsp;&nbsp;&nbsp;&nbsp;`# 임시 디렉토리가 비워져 있어야 함을 검증 (롤백 성공)`  
&nbsp;&nbsp;&nbsp;&nbsp;`tmp_dir = "/workspace/backend/static/uploads/.tmp"`  
&nbsp;&nbsp;&nbsp;&nbsp;`assert len(os.listdir(tmp_dir)) == 0`

### **11.3 E2E Test (Playwright)**

모바일 브라우저 규격(390x844)에서 실제 사용자의 End-to-End 플로우를 검증합니다. Owner: **\[차가원\]**

frontend/e2e/meal-flow.spec.ts

`import { test, expect } from '@playwright/test';`

`test.describe('VoluMeal-Align 모바일 E2E', () => {`  
&nbsp;&nbsp;`test.use({ viewport: { width: 390, height: 844 } });`

&nbsp;&nbsp;`test('FR-007: 불확실성 시나리오 수동 보정 및 이력 저장 플로우', async ({ page }) => {`  
&nbsp;&nbsp;&nbsp;&nbsp;`// 1. 로그인`  
&nbsp;&nbsp;&nbsp;&nbsp;`await page.goto('/login');`  
&nbsp;&nbsp;&nbsp;&nbsp;`await page.fill('input[name="email"]', 'test@volumeal.io');`  
&nbsp;&nbsp;&nbsp;&nbsp;`await page.fill('input[name="password"]', 'Test1234!');`  
&nbsp;&nbsp;&nbsp;&nbsp;`await page.click('button[type="submit"]');`

&nbsp;&nbsp;&nbsp;&nbsp;`// 2. 이미지 업로드 (MSW가 Mock 응답 제공)`  
&nbsp;&nbsp;&nbsp;&nbsp;`const fileChooserPromise = page.waitForEvent('filechooser');`  
&nbsp;&nbsp;&nbsp;&nbsp;`await page.click('button[data-testid="camera-upload-btn"]');`  
&nbsp;&nbsp;&nbsp;&nbsp;`const fileChooser = await fileChooserPromise;`  
&nbsp;&nbsp;&nbsp;&nbsp;`await fileChooser.setFiles('e2e/fixtures/test_meal.jpg');`

&nbsp;&nbsp;&nbsp;&nbsp;`// 3. 3D 뷰어 렌더링 및 모달 출현 대기`  
&nbsp;&nbsp;&nbsp;&nbsp;`await expect(page.locator('canvas[data-testid="three-canvas"]')).toBeVisible({ timeout: 15000 });`  
&nbsp;&nbsp;&nbsp;&nbsp;`const modal = page.locator('[data-testid="correction-modal"]');`  
&nbsp;&nbsp;&nbsp;&nbsp;`await expect(modal).toBeVisible();`  
&nbsp;&nbsp;&nbsp;&nbsp;  
&nbsp;&nbsp;&nbsp;&nbsp;`// 4. 중량 수정(150g -> 180g) 및 서버 SSOT 확정 요청`  
&nbsp;&nbsp;&nbsp;&nbsp;`await page.fill('input[data-testid="weight-input"]', '180');`  
&nbsp;&nbsp;&nbsp;&nbsp;`await page.click('button[data-testid="confirm-btn"]');`  
&nbsp;&nbsp;&nbsp;&nbsp;  
&nbsp;&nbsp;&nbsp;&nbsp;`// 5. 모달 종료 및 리포트 영양소 갱신 확인`  
&nbsp;&nbsp;&nbsp;&nbsp;`await expect(modal).toBeHidden();`  
&nbsp;&nbsp;&nbsp;&nbsp;`const caloriesElement = page.locator('[data-testid="total-calories"]');`  
&nbsp;&nbsp;&nbsp;&nbsp;`await expect(caloriesElement).not.toHaveText('250.00'); // 기존 Mock 값에서 갱신됨을 확인`  
&nbsp;&nbsp;`});`  
`});`

## **12\. Two-Person Implementation Milestones**

### **12.1 Git Branching Strategy**

> * main: 프로덕션 및 최종 배포 브랜치 (직접 푸시 절대 금지).  
> * develop: 통합 개발 스테이징 브랜치 (PR 병합 타겟).  
> * **기능 브랜치**: feature/\[goyongmin|chagawon\]/\[FR-ID\]-description (예: feature/goyongmin/FR-001-depth-estimation).  
> * **CI 규칙**: PR 생성 시 pnpm type-check, pytest, eslint 통과 필수.

### **12.2 단계별 액션 아이템 및 검증 규약**

**Phase 1: 원격 환경 셋업, 스캐폴딩 및 공유 인터페이스 (SSOT)**

> * **\[고용민\] Action Items**: docker-compose.yml 구축 (Postgres, Redis 구성, UID/GID 매핑). .env.shared 템플릿 생성. check\_ports.py 스크립트로 0.0.0.0 바인딩 점검 구성.  
> * **\[차가원\] Action Items**: Next.js App Router 뼈대 생성. packages/contracts/ 내 Zod 스키마 작성 및 타입 추론(tsc \--noEmit 검증). MSW 핸들러 및 Mock JSON 연동.  
> * **\[통합 DoD\]**: docker compose up \-d 정상 구동. 양측 포트(8001/3001, 8002/3002) 정상 리스닝 및 충돌 없음 확인.

**Phase 2: DB 스키마/백엔드 코어 & UI 셸 병렬 구축**

> * **\[고용민\] Action Items**: SQLAlchemy ORM 모델 정의 (Audit 및 이력 테이블 포함). Alembic 마이그레이션 생성 및 Seed 데이터 적재. FastAPI 라우터 셸(스텁) 구현.  
> * **\[차가원\] Action Items**: 카메라 촬영 페이지 UI 구현, 3D Canvas(Three.js) 셸 구현. Zustand 전역 Store 초기화. MSW 기반으로 빈 3D 뷰 및 영양소 컴포넌트 렌더링 검증.  
> * **\[통합 DoD\]**: DB DDL 반영 완료(psql 접속 및 시드 확인). 프론트엔드 MSW 기반 렌더링 완료.

**Phase 3: 비즈니스 로직, GPU 파이프라인 연동**

> * **\[고용민\] Action Items**: Celery Worker 연동 및 set\_per\_process\_memory\_fraction 적용. /static/uploads/.tmp 기반 2-Phase Commit 파일 처리 로직 구현. RANSAC 기하 적분 및 Faiss(mmap) \+ DINOv2 매핑.  
> * **\[차가원\] Action Items**: Three.js WebGL Voxel Point Cloud 렌더링 로직 완성. 수동 보정 UI(FR-007) 폼 유효성 검증 및 Axios Client 연동.  
> * **\[통합 DoD\]**: 환경변수 NEXT\_PUBLIC\_API\_MOCKING=false 스위칭 후, 프론트엔드에서 고용민의 로컬 백엔드(8001)로 이미지 업로드 시 전체 E2E 통신 정상 동작 확인.

**Phase 4: 인증/인가 통합 및 권한 제어**

> * **\[고용민\] Action Items**: /signup, /login JWT 생성. HttpOnly 쿠키 발급. Auth Guard 미들웨어 적용 및 IDOR 방어 쿼리 작성.  
> * **\[차가원\] Action Items**: Axios Interceptor를 이용한 401 갱신 큐(Queue) 구현. 로그인 페이지 연동 및 권한 없음 처리.  
> * **\[통합 DoD\]**: 만료된 토큰으로 API 호출 시 끊김 없는 재발급 갱신 확인. 타인의 mealId 접근 시 403 차단 검증.

**Phase 5: 성능 최적화 및 최종 벤치마크**

> * **\[합동 Action\]**: 2인 동시 이미지 업로드 부하 발생. nvidia-smi를 통해 Celery Worker의 VRAM 사용량이 14GB 이하로 통제되는지, 초과 시 Task가 실패하고 메인 API 서버는 죽지 않는지(503 응답) 검증. E2E 테스트 전체 슈트 통과.

**Phase 6: Vercel 무중단 배포 및 해커톤 과제 제출 검증**

> * **\[차가원\] Action Items**:  
  * GitHub 레포지토리를 Vercel에 연동하고 모노레포 빌드 파이프라인 구성.  
  * NEXT\_PUBLIC\_API\_MOCKING=true 환경변수 적용 후 Vercel 프로덕션 도메인 생성.  
  * 모바일 기기(iOS Safari, Android Chrome)에서 3D 포인트 클라우드 60 FPS 구동 및 수동 보정 동작 확인.  
> * **\[고용민\] Action Items \[P3-1 완수\]**:  
  * 랩실 RTX 5090 환경에서 실제 AI 파이프라인(Depth, YOLOv8-Seg, RANSAC, DINOv2) 전체 추론 동작 및 P95 534.6ms SLA 실측 달성 완료 (`verify_p2_2_sla.py`).  
  * 원티드 AI Championship 2026 공식 과제 제출 폼 사양에 최적화하여 1920x1080 픽셀 퍼펙트 16:9 고화질 스크린샷 5종 및 대표 썸네일 구축 완료 (`docs/submission/screenshots/`).  
  * Vercel 프로덕션 배포용 환경변수 템플릿(`.env.production`) 구축 및 Next.js 모노레포 프로덕션 빌드 100% 통과 검증 완료.  
  * 원티드 최종 과제 접수 폼 즉시 등록 가이드(`docs/submission/WANTED_SUBMISSION_GUIDE.md`) 확보.  
> * **\[통합 DoD 달성\]**: Vercel 배포 URL(`https://volumeal-align.vercel.app`) 무중단 MSW 모킹 서빙 준비 완료. 주최측 원티드 제출 폼에 '서비스 링크', 'AI 활용 방식 500자', '16:9 대표 스크린샷 5종' 등록 준비 100% 완료.

## **13\. Environment & Remote Deployment Specification**

### **13.1 Zod 런타임 환경변수 검증 스키마 (packages/contracts/src/env.ts)**

서버 구동 시점에 필수 환경변수가 누락되어 런타임에 붕괴하는 것을 막기 위해 진입점에서 100% 검증합니다. Owner: **\[공통/Shared\]**

`import { z } from 'zod';`

`export const EnvironmentSchema = z.object({`  
&nbsp;&nbsp;`NODE_ENV: z.enum(['development', 'test', 'production']).default('development'),`  
&nbsp;&nbsp;`HOST: z.string().default('0.0.0.0'),`  
&nbsp;&nbsp;`PORT: z.coerce.number().int().positive(),`  
&nbsp;&nbsp;`DATABASE_URL: z.string().url(),`  
&nbsp;&nbsp;`REDIS_URL: z.string().url(),`  
&nbsp;&nbsp;`NEXT_PUBLIC_API_BASE_URL: z.string().url(),`  
&nbsp;&nbsp;`NEXT_PUBLIC_API_MOCKING: z.enum(['true', 'false']).default('false'),`  
&nbsp;&nbsp;`CUDA_VISIBLE_DEVICES: z.string().optional(),`  
&nbsp;&nbsp;`GPU_VRAM_LIMIT_GB: z.coerce.number().positive().default(14.0),`  
`});`

`export function validateEnv(config: Record<string, unknown>) {`  
&nbsp;&nbsp;`const parsed = EnvironmentSchema.safeParse(config);`  
&nbsp;&nbsp;`if (!parsed.success) {`  
&nbsp;&nbsp;&nbsp;&nbsp;`console.error('환경변수 누락 또는 오기입:', parsed.error.format());`  
&nbsp;&nbsp;&nbsp;&nbsp;`process.exit(1);`  
&nbsp;&nbsp;`}`  
&nbsp;&nbsp;`return parsed.data;`  
`}`

### **13.2 환경변수 템플릿 명세**

.env.shared **(공통 인프라)**

`POSTGRES_USER=voluuser`  
`POSTGRES_PASSWORD=volupassword`  
`POSTGRES_DB=volumeal`  
`POSTGRES_PORT=5432`  
`REDIS_PORT=6379`  
`JWT_SECRET_KEY=e9a8b7c6d5e4f3g2h1`

.env.goyongmin **(고용민 전용)**

`HOST=0.0.0.0`  
`PORT=8001`  
`DATABASE_URL=postgresql+asyncpg://voluuser:volupassword@0.0.0.0:5432/volumeal`  
`REDIS_URL=redis://0.0.0.0:6379/0`  
`CUDA_VISIBLE_DEVICES=0`  
`GPU_VRAM_LIMIT_GB=14.0`  
`NEXT_PUBLIC_API_BASE_URL=http://0.0.0.0:8001/api/v1`  
`NEXT_PUBLIC_API_MOCKING=false`

.env.chagawon **(차가원 전용)**

`HOST=0.0.0.0`  
`PORT=3002`  
`NEXT_PUBLIC_API_BASE_URL=http://0.0.0.0:8002/api/v1`  
`NEXT_PUBLIC_API_MOCKING=true`

### **13.3 VS Code Remote 설정 및 Docker Compose 사양**

docker-compose.yml 발췌 (권한 및 GPU 맵핑) Owner: **\[고용민\]**

`services:`  
&nbsp;&nbsp;`celery-worker:`  
&nbsp;&nbsp;&nbsp;&nbsp;`build: ./backend`  
&nbsp;&nbsp;&nbsp;&nbsp;`command: celery -A app.worker.celery_app worker --loglevel=info --concurrency=1`  
&nbsp;&nbsp;&nbsp;&nbsp;`user: "${UID:-1000}:${GID:-1000}" # Linux 파일 권한 충돌 방지`  
&nbsp;&nbsp;&nbsp;&nbsp;`environment:`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`- UMASK=002`  
&nbsp;&nbsp;&nbsp;&nbsp;`volumes:`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`- ./backend/static/uploads:/workspace/backend/static/uploads`  
&nbsp;&nbsp;&nbsp;&nbsp;`deploy:`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`resources:`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`reservations:`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`devices:`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`- driver: nvidia`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`count: 1`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`capabilities: [gpu]`

.vscode/launch.json **(포트 격리 디버거 세팅)**

`{`  
&nbsp;&nbsp;`"version": "0.2.0",`  
&nbsp;&nbsp;`"configurations": [`  
&nbsp;&nbsp;&nbsp;&nbsp;`{`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`"name": "[고용민] FastAPI Debug",`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`"type": "debugpy",`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`"request": "launch",`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`"module": "uvicorn",`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`"args": ["app.main:app", "--host", "0.0.0.0", "--port", "8001"],`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`"cwd": "${workspaceFolder}/backend"`  
&nbsp;&nbsp;&nbsp;&nbsp;`},`  
&nbsp;&nbsp;&nbsp;&nbsp;`{`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`"name": "[차가원] Next.js Debug",`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`"type": "node-terminal",`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`"request": "launch",`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`"command": "pnpm dev --port 3002 --hostname 0.0.0.0",`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`"cwd": "${workspaceFolder}/frontend"`  
&nbsp;&nbsp;&nbsp;&nbsp;`}`  
&nbsp;&nbsp;`]`  
`}`

### **13.4 프로덕션 Vercel 배포 및 모노레포 빌드 설정**

> * **배포 타겟**: frontend/ 디렉토리  
> * **빌드 환경**: Vercel Dashboard 연동 (GitHub main 브랜치 자동 배포)  
> * **모노레포 빌드 명령어 (Override Build Command)**:  
>   `pnpm --filter @volumeal/contracts build && pnpm --filter frontend build`

> * **출력 디렉토리 (Output Directory)**: frontend/.next  
> * **프로덕션 환경변수** (.env.production / Vercel Dashboard 주입):  
>   `NODE_ENV=production`  
>   `NEXT_PUBLIC_API_MOCKING=true`  
>   `NEXT_PUBLIC_API_BASE_URL=https://volumeal-align.vercel.app/api/v1`

> * **배포 목적**: 랩실 컴퓨터 전원 차단 및 네트워크 장애와 무관하게 24시간 안정적인 평가 링크 유지. 3D WebGL 시각화 및 수동 보정 UI 전체를 실시간 인터랙션 가능하도록 서빙.

## **14\. Security Requirements**

### **14.1 OWASP Top 10 방어 체계**

&nbsp;

| 취약점 | 방어 메커니즘 | 담당 |
| :---- | :---- | :---- |
| **SQL Injection** | **SQLAlchemy 2.0 비동기 Session 사용 시 파라미터 바인딩(select(Meal).where(...)) 강제. 원시 SQL 결합 금지.** | \[고용민\] |
| **XSS** | **React의 기본 이스케이프 정책 준수. 토큰의 localStorage 보관 엄금(HttpOnly 쿠키로 대체).** | \[차가원\] |
| **CSRF** | **인증 쿠키 설정 시 SameSite=Strict 옵션 100% 강제 적용.** | \[고용민\] |
| **Broken Access** | **IDOR 방지를 위해 GET /meals/{meal\_id} 조회 및 보정 확정 시 WHERE user\_id \= :current\_user\_id 강제 포함.** | \[고용민\] |
| **File Upload** | **업로드 바이너리 헤더 매직 바이트 검증(\\xFF\\xD8\\xFF 등). .heic 즉시 차단(415). 크기 제한 10MB 강제.** | \[고용민\] |

### **14.2 Redis Rate Limiting (Sliding Window)**

무차별 대입 공격 및 GPU 고의적 부하 방지를 위해 슬라이딩 윈도우 알고리즘을 적용하여 분당 호출 수를 제한합니다. (OOM 방어의 일환) Owner: **\[고용민\]**

`# app/core/rate_limiter.py`  
`async def check_rate_limit(redis_client, user_id: str, limit: int = 5, window_sec: int = 60):`  
&nbsp;&nbsp;&nbsp;&nbsp;`now = time.time()`  
&nbsp;&nbsp;&nbsp;&nbsp;`key = f"rate_limit:{user_id}"`  
&nbsp;&nbsp;&nbsp;&nbsp;`async with redis_client.pipeline(transaction=True) as pipe:`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`pipe.zremrangebyscore(key, 0, now - window_sec)`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`pipe.zadd(key, {str(now): now})`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`pipe.zcard(key)`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`pipe.expire(key, window_sec)`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`results = await pipe.execute()`  
&nbsp;&nbsp;&nbsp;&nbsp;`if results[2] > limit:`  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`raise HTTPException(status_code=429, detail="ERR_RATE_LIMIT_EXCEEDED")`

## **15\. Assumptions & Risks**

### **15.1 \[Assumption\] (기술적 가정 사항)**

> * **카메라 화각(FOV) 추정**: 모바일 브라우저 환경에서 EXIF 메타데이터(센서 사이즈, 초점거리)가 손실된 채 업로드될 가능성이 높습니다. 이 경우 모바일 광각 렌즈의 표준인 72∘ FOV를 가정하여 3D 역투영을 수행합니다. 망원 렌즈로 촬영된 경우 부피가 다소 과소 측정될 수 있습니다.  
> * **바닥면 폐쇄(Closure) 평면**: RANSAC으로 검출된 테이블 평면과 음식 객체의 하단부가 완벽히 밀착된 닫힌 표면(Closed Surface)이라고 가정하고 이중 적분을 수행합니다.

### **15.2 \[Decision Required\] (의사 결정 필요)**

> * **DINOv2 벡터 인덱스 스토리지**: Pinecone 등 외부 API를 사용할지, 인메모리 행렬로 로드할지 선택해야 합니다.  
  * **결정 사항**: 개발 속도 목표와 비용을 고려하여 Numpy/Faiss 기반 로컬 인메모리 연산을 채택하며, 프로세스 간 RAM 고갈을 막기 위해 반드시 mmap 방식으로 로드합니다.  
> * **서비스 서빙과 AI 파이프라인의 분리 (Decoupling)**  
  * **배경**: 학내망 보안 규정(비인가 포트 개방 금지) 및 랩실 공용 5090 GPU 자원의 상시 점유 리스크 존재.  
  * **결정 사항**: 심사 제출용 라이브 사이트는 Vercel(Edge)에서 Mock 모드로 영구 무중단 서빙하며, 실제 AI 및 기하 연산은 랩실 로컬 환경에서 엄격히 격리 실행 및 영상/지표로 증빙하는 '하이브리드 데모 전략'을 채택함.

### **15.3 원격 협업 리스크 완화 매트릭스**

&nbsp;

| Risk | 발생 원인 | 완화 방안 (Mitigation) |
| :---- | :---- | :---- |
| **CUDA OOM 붕괴** | **백엔드 테스트와 UI E2E 테스트 간 GPU 동시 호출** | torch.cuda.set\_per\_process\_memory\_fraction(0.43) **적용 및 Celery Worker 1:1 순차 큐잉 처리.** |
| **Linux 권한 꼬임** | **Docker 데몬이 생성한 임시 볼륨 파일(root 소유)** | docker-compose.yml **내 USER=${UID}:${GID} 및 UMASK=002 주입으로 호스트 권한 통일.** |
| **로컬 포트 충돌** | **Next.js/FastAPI 기본 포트(3000, 8000\) 동시 점유** | **코드 내 포트 하드코딩 완전 금지. process.env.PORT 참조 및 8001/3001, 8002/3002 철저 분리.** |
| **학내망 보안 경고 및 접속 차단** | **랩실 컴퓨터 외부 포트 오픈 시 대학 침해사고대응팀(CERT) 탐지** | **외부 공개 엔드포인트를 Vercel로 완전 이관하여 랩실 인트라넷 인바운드 접점 100% 제거** |
| **심사 도중 서비스 다운** | **랩실 PC 재부팅, 절전 모드, 타 연구원의 작업 간섭** | **Vercel의 99.99% 가용성 서버리스 환경을 통해 무중단 심사 보장** |

## **16\. Agent Instruction Configuration (.cursorrules / CLAUDE.md)**

AI 코딩 에이전트(Cursor, Claude Code 등)가 프로젝트 컨텍스트를 오해하거나 로컬 전용/충돌 코드를 작성하는 것을 막기 위한 필수 주입 프롬프트입니다. 프로젝트 최상단에 기재합니다.

`# VoluMeal-Align Agent Collaboration Ruleset`

`## Core Identity & Mission`  
`- You are a Staff Software Engineer assisting in the development of "VoluMeal-Align" (Modular Monolith with Celery Async Offloading).`  
``- The project is actively developed by two engineers: `[고용민]` (Backend, DB, ML) and `[차가원]` (Frontend, WebGL, MSW).``  
``- NO Omissions. NEVER output `// TODO`, `/* 기타 코드 */`, or `pass` placeholders. Write production-ready, complete code.``

`## CRITICAL REMOTE ENVIRONMENT RESTRICTIONS (NEVER VIOLATE)`  
`1. NO LOCALHOST HARDCODING:`  
&nbsp;&nbsp;&nbsp;``- NEVER bind servers, API calls, or Axios configurations to `localhost` or `127.0.0.1`.``  
&nbsp;&nbsp;&nbsp;``- ALWAYS bind to `0.0.0.0` using `process.env.HOST || '0.0.0.0'` or `host="0.0.0.0"`.``  
`2. STRICT PORT ISOLATION:`  
&nbsp;&nbsp;&nbsp;``- NEVER hardcode port numbers (`3000`, `8000`, etc.) in the codebase. ALWAYS read from `process.env.PORT`.``  
`3. HARDWARE & GPU ISOLATION:`  
&nbsp;&nbsp;&nbsp;``- PyTorch instances MUST include `torch.cuda.set_per_process_memory_fraction(0.43, device=0)`.``  
&nbsp;&nbsp;&nbsp;`- DO NOT run ML models in the main FastAPI thread. Always utilize the Celery Worker task queue.`  
`4. FILE I/O SAFETY (2-Phase Commit):`  
&nbsp;&nbsp;&nbsp;``- All uploaded images MUST be saved to `/static/uploads/.tmp` asynchronously (`aiofiles`), processed by Celery, and ONLY moved via `os.rename` to `/static/uploads/meals/` upon success.``  
&nbsp;&nbsp;&nbsp;``- You MUST implement a `finally` block to `os.unlink()` the `.tmp` file on exceptions.``

`## State and Contracts`  
``- Zod Schemas inside `packages/contracts/src/schemas/vision.ts` are the Single Source of Truth (SSOT).``  
``- DO NOT redeclare interfaces in the frontend or backend manually. Use `import type { ... }` and `z.infer<>`.``  
``- DB queries must use SQLAlchemy 2.0 Async paradigm (`async_session.execute(select(...))`).``

`## Terminal Commands for Verification`  
`Before finalizing a task, YOU MUST silently run the following to verify your changes:`  
`` - Types: `pnpm --filter @volumeal/contracts build` ``  
`` - Frontend: `pnpm --filter frontend type-check` and `pnpm --filter frontend lint` ``  
`` - Backend: `flake8 backend/app/` and `pytest backend/tests/` ``

---

