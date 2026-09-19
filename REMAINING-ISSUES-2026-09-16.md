# VoluMeal-Align 남은 문제 및 수정 계획

작성일: 2026-09-16
기준 문서: `CODEX-WORK-SUMMARY-2026-09-16.md`

## 1. 현재 상태 요약

RTX 5090과 ONNX Runtime CUDA provider는 개발 PC에서 확인되었다. 현재 로컬 `.env`는 CUDA 사용과 실제 세그멘테이션 모델 경로를 사용하도록 설정되어 있다.

```text
ONNX_USE_CUDA=true
ONNX_SEG_MODEL_PATH=/workspace/backend/weights/kfood_seg_run/weights/best.onnx
```

다만 현재 분석 모델과 데이터는 실사진 기반으로 검증되지 않았다. `backend/data/kfood`는 합성 다각형 이미지 150장이며, 현재 세그멘테이션 모델도 이 데이터셋을 기반으로 학습되었다.

## 2. 우선순위 P0: 실사진 학습·검증 부재

### 문제

- 현재 workspace에 실제 음식 사진 데이터셋이 없다.
- `/workspace/backend/data/kfood/images/train`과 `/workspace/backend/data/kfood/images/val`은 합성 이미지다.
- 현재 모델은 음식 9종과 약제 1종만 대상으로 한다.
- 실사진에서의 인식 정확도, 재현율, segmentation 품질이 검증되지 않았다.

### 수정 방향

1. 실제 음식 사진을 수집한다.
2. `backend/data/real_food/images/test`에 먼저 넣어 추론만 검증한다.
3. 필요한 사진에 YOLO segmentation polygon 라벨을 작성한다.
4. `train/val/test`로 분리한다.
5. RTX 5090에서 재학습한다.
6. 새 `best.pt`를 ONNX로 변환한다.
7. 실사진 test 세트로 재검증한다.

### 관련 경로

```text
/workspace/backend/data/real_food/images/test
/workspace/backend/data/real_food/images/train
/workspace/backend/data/real_food/images/val
/workspace/backend/data/real_food/labels/train
/workspace/backend/data/real_food/labels/val
/workspace/backend/data/real_food/labels/test
```

## 3. 우선순위 P0: 깊이 모델의 metric 단위 미검증

### 문제

`depth_anything_v2_vits.onnx`가 출력값을 반환하는 것은 확인했지만, 출력값이 실제 미터 단위라는 사실은 검증되지 않았다. 합성 이미지에서 출력 범위가 약 2.52~3.56이었지만, 이것만으로 절대 깊이라고 판단할 수 없다.

### 수정 방향

- 실제 거리를 측정한 기준 물체를 준비한다.
- 카메라 초점거리와 촬영 거리를 기록한다.
- 여러 거리와 각도에서 깊이값을 비교한다.
- 실제 거리 대비 오차를 계산한다.
- metric 계약이 확인되기 전에는 `DEPTH_MODEL_IS_METRIC=true`를 운영 신뢰값으로 사용하지 않는다.

## 4. 우선순위 P0: 합성 이미지 기반 임베딩 인덱스

### 문제

`backend/scripts/setup_models_and_data.py`는 현재 KFood 검증 이미지에서 DINO 임베딩 인덱스를 만든다. 따라서 `food_reference_embeddings.npz`도 실사진 기준 이미지 인덱스라고 볼 수 없다.

또한 라벨이 없는 클래스에 대해 랜덤 fallback 벡터를 생성한다.

```python
rng = np.random.RandomState(hash(fid) % 10000)
centroid = rng.randn(384).astype(np.float32)
```

랜덤 벡터는 실제 음식 검색 결과를 만들 수 있으므로 운영 경로에서 허용하면 안 된다.

### 수정 방향

- 실사진 기준 이미지에서 클래스별 임베딩을 다시 생성한다.
- 모든 지원 `foodId`에 기준 이미지가 있는지 검사한다.
- 기준 이미지 또는 임베딩이 하나라도 없으면 준비 상태를 실패시킨다.
- 랜덤 fallback 생성 코드를 제거한다.
- 임베딩 모델의 출력 차원과 foodId 인덱스 정합성을 검사한다.

## 5. 우선순위 P1: 모델 경로와 배포 설정 불일치

### 문제

로컬 개발 PC에서는 다음 경로를 사용하도록 설정했지만, Render 설정은 모델 경로와 CUDA 사용을 별도로 지정하지 않는다.

```text
/workspace/backend/weights/kfood_seg_run/weights/best.onnx
```

`render.yaml`은 Render에 백엔드도 배포하도록 되어 있고, Render 백엔드는 GPU를 사용할 수 없다. 무료 서버의 메모리 한도와 모델 크기도 실제 추론에 적합한지 별도 확인이 필요하다.

### 수정 방향

권장 배포 구조:

```text
Render 프론트엔드
  -> 개발 PC의 HTTPS 분석 API
  -> RTX 5090 ONNX Runtime
```

- Render에는 프론트엔드만 배포한다.
- 개발 PC에서 FastAPI와 모델을 실행한다.
- 분석 API만 HTTPS 터널로 외부에 노출한다.
- DB 포트는 외부에 노출하지 않는다.
- Render 프론트엔드의 `API_BACKEND_URL`을 개발 PC 분석 API로 변경한다.
- 시연 중 개발 PC, 백엔드, 외부 터널을 계속 실행한다.

## 6. 우선순위 P1: GPU/CPU 의존성 분리 미완료

### 문제

`backend/requirements.txt`는 CPU용 패키지를 선언한다.

```text
onnxruntime==1.18.0
```

현재 개발 환경에서는 CUDA provider가 동작하지만, requirements를 새로 설치하면 동일한 GPU 환경이 보장되지 않는다.

### 수정 방향

```text
backend/requirements.txt       # Render CPU용
backend/requirements-gpu.txt   # RTX 5090 개발용
```

GPU용 ONNX Runtime은 실제 CUDA/cuDNN 환경과 호환되는 버전으로 고정하고, 설치 후 다음을 확인한다.

- `ort.get_available_providers()`에 `CUDAExecutionProvider` 존재
- 세그멘터·깊이·DINO 세션의 `get_providers()` 확인
- 실제 추론 중 `nvidia-smi`의 GPU 메모리·사용률 확인

## 7. 우선순위 P1: 학습 스크립트가 합성 데이터셋에 고정됨

### 문제

[train_kfood_segmentor.py](backend/src/ml/train_kfood_segmentor.py)는 기본적으로 다음 데이터셋을 사용한다.

```text
/workspace/backend/data/kfood.yaml
```

실사진 데이터셋으로 재학습하려면 매번 인자를 직접 넘기거나 코드 기본값을 변경해야 한다.

### 수정 방향

- 실제 데이터셋용 `real_food.yaml`을 만든다.
- 학습 스크립트가 `--data-yaml`, `--model-size`, `--output-dir`를 받도록 한다.
- 학습 후 생성된 ONNX 경로를 출력한다.
- 학습 데이터와 모델의 클래스 목록이 일치하는지 자동 검사한다.

## 8. 우선순위 P1: 클래스와 foodId 계약 불완전

### 문제

세그멘테이션 클래스 이름, 식품 catalog의 `foodId`, density profile, nutrient profile, embedding index가 모두 같은 항목을 가져야 한다. 새 실사진 클래스를 추가하면 한 파일만 수정해서는 안 된다.

### 수정 방향

새 음식 추가 시 다음을 함께 갱신한다.

- dataset YAML class 목록
- segmentation 라벨 class ID
- `food_catalog.json`
- `food_density_profiles.json`
- `food_nutrients.json`
- `food_reference_embeddings.npz`
- interaction tags 및 복약 규칙 필요 여부

모든 집합이 일치하지 않으면 readiness 단계에서 실패시켜야 한다.

## 9. 우선순위 P2: 실제 음식 분석 오류 처리 및 threshold 검증

### 문제

합성 이미지에서 낮은 confidence 검출은 있었지만, 기본 confidence `0.25`에서는 `ERR_ZERO_OBJECT_DETECTED`로 종료되었다. 이것은 GPU 오류가 아니며 모델·데이터 품질과 threshold의 문제다.

### 수정 방향

- 실사진 validation set에서 confidence threshold를 측정한다.
- threshold를 무조건 낮춰 성공시키지 않는다.
- 낮은 threshold에서 false positive가 증가하는지 확인한다.
- 음식 미검출, 약제만 검출, 음식과 약제 동시 검출을 별도 테스트한다.
- 임의의 1인분이나 임의 영양값으로 대체하지 않는다.

## 10. 데이터셋 확보 방법

### 세그멘테이션 학습용

- AI Hub 한국 음식 이미지: 한국 음식에 적합할 수 있으나 계정, 이용 승인, 라이선스를 확인해야 한다.
- UECFOOD-100/256: 실제 음식 이미지가 있지만 polygon이 아닌 라벨이면 별도 segmentation 라벨링이 필요하다.
- Food-101: 실제 음식 이미지지만 주로 분류 라벨이므로 segmentation 학습에 바로 사용할 수 없다.
- Nutrition5k: 음식 이미지와 영양 연구 데이터지만 현재 클래스·영양 계약과 바로 일치하지 않으며 사용 조건 확인이 필요하다.

### 영양 데이터용

영양 API는 음식 이미지 학습 데이터셋을 대체하지 않는다. USDA FoodData Central이나 공식 식품 영양 DB는 영양성분 조회에 사용하고, 음식 이미지·segmentation 라벨은 별도로 준비해야 한다.

## 11. 실시간 API와 데이터셋의 관계

실시간 API는 학습 데이터 연결용이 아니라 학습된 모델의 추론용이다.

```text
사용자 사진
  -> POST /api/v1/vision/estimate
  -> 개발 PC RTX 5090 모델 추론
  -> 음식·깊이·부피·영양 결과
```

데이터셋은 다음 과정으로 준비한다.

```text
공개 데이터셋 다운로드 또는 직접 촬영
  -> 라벨 확인·수정
  -> train/val/test 분리
  -> RTX 5090 재학습
  -> 모델 검증
  -> 실시간 API에 새 모델 연결
```

사용자 업로드 사진을 자동으로 즉시 학습에 넣으면 잘못된 예측이 모델에 누적될 수 있으므로 사용하지 않는다.

## 12. 권장 수정 순서

1. 실제 음식 사진을 확보하고 `real_food/images/test`에 넣는다.
2. 현재 모델의 실사진 추론 결과를 수집한다.
3. 실사진 라벨을 작성하고 `real_food.yaml`을 만든다.
4. 합성 데이터 생성 경로와 실사진 학습 경로를 분리한다.
5. 랜덤 임베딩 fallback을 제거한다.
6. 실사진 기준 임베딩 인덱스를 재생성한다.
7. RTX 5090에서 세그멘테이션 모델을 재학습한다.
8. 깊이 모델의 metric 단위를 검증한다.
9. 모델 경로·GPU/CPU requirements·Render 배포 구성을 분리한다.
10. 실사진 기반 전체 API, 영양 계산, 복약 경고, 저장 흐름을 검증한다.
11. 검증이 끝난 뒤에만 Render 프론트엔드를 개발 PC API에 연결한다.

## 13. 완료 기준

- 실사진 test 세트에서 음식별 검출 성능 측정 결과가 있음
- segmentation 라벨과 클래스 매핑이 검증됨
- 모든 지원 foodId에 실사진 임베딩 기준값이 있음
- 랜덤 임베딩 fallback이 제거됨
- 깊이 출력의 미터 단위가 기준 물체로 검증됨
- RTX 5090과 CPU 배포 의존성이 분리됨
- Render는 프론트엔드만 제공하고 분석 API는 개발 PC에서 동작함
- 실사진 기반 전체 사용자 흐름이 성공함
