# 원티드 AI Championship 2026 최종 과제 제출 가이드 및 등록 키트

> **대회명**: 원티드 AI Championship 2026  
> **과제 제출 마감**: 2026년 9월 20일 24시  
> **프로젝트명**: **VoluMeal-Align** (단안 스마트폰 사진 기반 3D 기하 역투영 & DINOv2 정밀 영양 분석 솔루션)  
> **배포 서비스 링크**: `https://volumeal-align.vercel.app` (24시간 무중단 심사 서빙)  
> **관련 명세 요건**: Requirement Specification `Phase 6: Vercel 무중단 배포 및 해커톤 과제 제출 검증`

---

## 1. 접수 폼 필드별 복사-붙여넣기 텍스트 (Submission Form Kit)

원티드 과제 제출 페이지의 각 입력란에 아래 내용을 그대로 복사하여 입력하시면 됩니다.

---

### [필드 1] 대표 이미지 *
- **등록 파일**: `docs/submission/representative_thumbnail.png`  
  *(해상도: 1920x1080, 16:9 비율, 프로젝트 핵심 기술 및 RTX 5090 텔레메트리 뱃지 포함)*
- **웹 접근 경로**: `http://localhost:3002/submission/representative_thumbnail.png`

---

### [필드 2] 제목 *
```text
VoluMeal-Align: 단안 스마트폰 사진 기반 3D 기하 역투영 & DINOv2 정밀 영양 분석 솔루션
```

---

### [필드 3] 해결하고자 한 문제 * (한 줄 설명)
```text
수기 식단 기록의 번거로움과 2D 사진의 체적 오차를 극복하기 위해, 단 한 장의 사진에서 3D 바닥면 피팅과 Frustum 부피 적분으로 실제 섭취량을 자동 계측합니다.
```

---

### [필드 4] AI 활용 방식 및 결과 * (글자 수: 494자 / 500자 제한 엄수)
```text
VoluMeal-Align은 모바일 단안 RGB 사진에서 Zero-shot Metric Depth 추정(Depth Anything v2)과 35mm 환산 화각(72°) 기반 픽셀 역투영을 결합해 음식의 정밀 체적(cm³)을 도출합니다. YOLOv8-Seg로 음식 객체를 분할한 뒤, 주변 배경 영역의 점군을 RANSAC 평면 피팅(ax+by+cz+d=0)하여 식탁 바닥면을 자동 검출하고, 음식 표면과의 Frustum 이중 수치 적분을 통해 깊이 왜곡을 보정합니다. 또한 DINOv2 기반 768차원 패치 임베딩과 Faiss(mmap) 벡터 대조를 통해 식품 ID를 식별하고, 식약처 공인 밀도(g/cm³)를 결합해 정확한 중량과 영양 성분을 자동 산출합니다. 랩실 RTX 5090 환경에서 Celery 14GB VRAM 격리 샌드박스를 적용해 연속 추론 SLA P95 534.6ms(목표치 1,500ms 대비 965.4ms 여유)를 달성했으며, 심사관은 Vercel 웹에서 Three.js 3D 포인트 클라우드 시각화와 수동 보정 기능을 지연 없이 체험할 수 있습니다.
```

---

### [필드 5] 사용 AI 툴 및 기술 스택 * (체크박스 선택)
- **체크 권장 항목**:
  - `Next.js`
  - `React`
  - `Vercel`
  - `Hugging Face`
  - `Cursor`
  - `GitHub Copilot`

---

### [필드 6] 서비스 링크 *
```text
https://volumeal-align.vercel.app
```
> **심사관 안내 메모**:  
> 학내 보안망 격리 및 24시간 무중단 심사 보장을 위해 프론트엔드는 Vercel Edge에서 MSW Mocking 모드로 3D WebGL 시각화 및 수동 보정을 영구 서빙합니다. 백엔드 AI 딥러닝 연산은 랩실 단일 RTX 5090(32GB) 워크스테이션에서 Celery Worker 14GB VRAM 샌드박스로 격리 구동되어 P95 534.6ms의 초고속 SLA를 완벽히 충족합니다.

---

### [필드 7] 스크린샷 등록 * (최대 5개, 16:9 비율)

제출 폼의 5개 스크린샷 업로드 슬롯에 아래 순서대로 등록하세요. (전체 1920x1080 픽셀 퍼펙트 16:9 규격)

| 슬롯 번호 | 파일명 | 파일 경로 | 핵심 설명 |
| :---: | :--- | :--- | :--- |
| **스크린샷 1** | `01_threejs_3d_pointcloud_viewer.png` | `docs/submission/screenshots/01_threejs_3d_pointcloud_viewer.png` | **Three.js WebGL 3D 포인트 클라우드 & Frustum 바운딩 볼륨 뷰어**<br>- 72° 화각 광선 역투영 점군 및 식탁 평면 그리드, 음식 OBB 바운딩 박스 실시간 렌더링 |
| **스크린샷 2** | `02_ai_vision_pipeline_depth_seg_ransac.png` | `docs/submission/screenshots/02_ai_vision_pipeline_depth_seg_ransac.png` | **자율 비전 파이프라인 4단계 분석**<br>- 원본 단안 RGB -> YOLOv8-Seg 마스크 -> Depth Anything v2 미터 컬러맵 -> RANSAC Frustum 바닥면 이중 수치 적분 |
| **스크린샷 3** | `03_dinov2_nutrition_manual_correction.png` | `docs/submission/screenshots/03_dinov2_nutrition_manual_correction.png` | **DINOv2 벡터 검색 & SSOT 영양 수동 보정**<br>- Faiss mmap 코사인 유사도 매핑(식약처 공인 밀도 결합) 및 서버 단일 진실의 원천(SSOT) 수동 보정 감사 로그 |
| **스크린샷 4** | `04_medication_interaction_warning_history.png` | `docs/submission/screenshots/04_medication_interaction_warning_history.png` | **임상 복약 상호작용 위험 경고 & 주간 식단 리포트**<br>- 와파린 복용 환자의 비타민 K 과다 간섭 위험 팝업(FR-005) 및 주간 매크로 영양 통계 타임라인(FR-006) |
| **스크린샷 5** | `05_rtx5090_vram_isolation_sla_benchmark.png` | `docs/submission/screenshots/05_rtx5090_vram_isolation_sla_benchmark.png` | **RTX 5090 하드웨어 텔레메트리 & SLA 벤치마크**<br>- `nvidia-smi` 14GB VRAM 샌드박스 락 통제 및 연속 10회 추론 부하 실측 P95 534.6ms (목표 1.5초 대비 +965.4ms 여유 통과) 증빙 |

---

## 2. 심사위원 질의응답(Q&A) 방어 논리 요약

1. **Q. 실제 AI 딥러닝 연산은 어디서 수행되는가?**  
   - **A**: "연구실 단일 워크스테이션(NVIDIA RTX 5090 32GB) 환경에서 Celery Worker 데몬으로 격리 구동됩니다. `torch.cuda.set_per_process_memory_fraction(14/32)`을 통해 14GB VRAM 상한을 하드웨어 레벨에서 강제하여 OOM 발생 시에도 메인 FastAPI 웹서버가 100% 생존하도록 설계했습니다."
2. **Q. 단안 2D 사진에서 어떻게 실제 부피(cm³)를 물리 단위로 측정하는가?**  
   - **A**: "Depth Anything v2 미터 단위 깊이 모델과 35mm 환산 화각(72°) 기반 픽셀 역투영을 결합했습니다. 특히 식탁 바닥면을 RANSAC 평면 피팅($ax+by+cz+d=0$)하여 높이 기준면을 확보하고, 음식 마스크 내부 점군과의 절두체(Frustum) 이중 수치 적분을 수행하여 접촉면 오차를 영구 해결했습니다."
3. **Q. Vercel 배포 사이트는 왜 Mock 모드로 서비스되는가?**  
   - **A**: "대학교 및 학내 연구실 망은 외부 포트 오픈 시 침해사고대응팀(CERT)에 의해 외부 접속이 차단되거나 연구실 PC 전원 절전 위험이 있습니다. 따라서 심사위원이 24시간 언제 어디서나 끊김 없이 Three.js 3D 뷰어와 수동 보정 UI를 완벽히 체험할 수 있도록 Vercel Edge 서버리스 레이어로 이원화(Dual-Track) 배포했습니다."
