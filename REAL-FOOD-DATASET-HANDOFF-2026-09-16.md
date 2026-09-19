# 실제 음식 데이터셋 연결 정리

작성일: 2026-09-16

## 1. 현재 확인된 파일

### 현재 음식 데이터셋

```text
/workspace/backend/data/kfood
```

하위 이미지 경로:

```text
/workspace/backend/data/kfood/images/train
/workspace/backend/data/kfood/images/val
```

- 이미지 수: 총 150장
- 성격: 실제 촬영 데이터가 아닌 합성 다각형 이미지
- 용도: YOLO segmentation 파이프라인 및 GPU 추론 테스트
- 실사진 정확도 검증용으로 사용하면 안 됨

### 현재 세그멘테이션 모델

```text
/workspace/backend/weights/kfood_seg_run/weights/best.onnx
/workspace/backend/weights/kfood_seg_run/weights/best.pt
```

이 모델의 ONNX 메타데이터는 다음 데이터셋으로 학습되었다고 기록되어 있다.

```text
/workspace/backend/data/kfood.yaml
```

현재 클래스:

```text
0 white_rice
1 spinach_namul
2 kimchi_stew
3 soybean_paste_stew
4 bulgogi
5 grilled_salmon
6 banana
7 grapefruit
8 boiled_egg
9 coumadin_pill
```

즉, 음식 9종과 약제 1종을 대상으로 한 모델이며 일반적인 모든 음식 인식 모델은 아니다.

## 2. 실사진 데이터셋 상태

현재 `/workspace` 안에서는 별도의 실사진 음식 데이터셋이나 실사진으로 학습됐다고 확인할 수 있는 음식 세그멘테이션 모델을 찾지 못했다.

확인된 모델 중 다음 파일은 실사진 음식 데이터셋 학습 모델로 확인되지 않았다.

```text
/workspace/backend/weights/kfood_seg_run/weights/best.onnx
```

이 모델은 합성 `kfood` 데이터셋 기반이다.

다음 모델은 별도 검증이 필요하다.

```text
/workspace/backend/weights/dinov2_food_embedder.onnx
/workspace/backend/weights/depth_anything_v2_vits.onnx
```

- DINO 임베더: 음식 크롭을 벡터로 변환하지만, 현재 파일만으로 실사진 학습 출처를 확정할 수 없음
- Depth 모델: 깊이 추정 모델이며 음식 분류용 모델이 아님

## 3. 실사진을 넣을 폴더

실제 사진을 아래 경로에 넣는다.

```text
/workspace/backend/data/real_food/images/test
```

추후 재학습할 때는 다음 구조를 사용한다.

```text
/workspace/backend/data/real_food/
  images/
    train/
    val/
    test/
  labels/
    train/
    val/
    test/
```

실사진 파일만 먼저 테스트할 때는 `images/test`만 사용해도 된다. 이 단계에는 라벨이 필요 없다.

## 4. 실제 사진 테스트 방법

1. 음식 사진을 `backend/data/real_food/images/test`에 복사한다.
2. 개발 PC 백엔드를 실행한다.
3. 프론트엔드에서 사진을 업로드하거나 `/api/v1/vision/estimate`로 전송한다.
4. 검출 음식명, confidence, 부피, 깊이 출력, 오류 코드를 확인한다.
5. 사진별 결과를 기록한다.

현재 백엔드는 다음 모델을 사용한다.

```text
ONNX_USE_CUDA=true
ONNX_SEG_MODEL_PATH=/workspace/backend/weights/kfood_seg_run/weights/best.onnx
```

실제 사진 테스트에서 음식이 검출되지 않으면 모델이 해당 음식 또는 실제 촬영 환경을 학습하지 않았을 가능성이 높다.

## 5. 재학습에 필요한 자료

재학습하려면 사진만으로는 부족하다.

필수 자료:

- 실제 음식 사진
- 음식별 segmentation polygon 라벨
- train/val/test 분리
- 클래스 목록
- 클래스와 `foodId`의 매핑
- 음식별 밀도·영양 데이터

라벨 예시:

```text
class_id x1 y1 x2 y2 x3 y3 x4 y4 ...
```

좌표는 YOLO segmentation 형식의 0~1 정규화 polygon 좌표를 사용한다.

## 6. 권장 클래스 전략

처음부터 음식 종류를 너무 많이 늘리지 않고, 시연에 필요한 음식부터 실제 사진을 준비한다.

1차 후보:

- white_rice
- kimchi_stew
- bulgogi
- grilled_salmon
- banana
- boiled_egg

기존 클래스와 다른 음식은 새 클래스 ID를 추가하고, `kfood.yaml`, 식품 카탈로그, 밀도 데이터, 영양 데이터의 `foodId`를 함께 맞춰야 한다.

## 7. 재학습 흐름

```text
실사진 수집
  -> polygon 라벨링
  -> train/val/test 분리
  -> kfood.yaml 또는 real_food.yaml 작성
  -> RTX 5090에서 YOLO segmentation 재학습
  -> best.pt 생성
  -> ONNX export
  -> ONNX_SEG_MODEL_PATH 교체
  -> 실사진 test 재검증
```

실사진을 폴더에 넣는 것만으로 현재 모델이 자동 학습되지는 않는다. 사용자 업로드 사진을 즉시 자동 학습에 사용하지 않는다.

## 8. 현재 결론

현재 바로 연결 가능한 것은 합성 데이터셋 기반 모델의 실사진 추론 테스트까지다.

실사진 기반 정확한 인식 서비스를 만들려면 다음 중 하나가 필요하다.

- 직접 촬영한 사진을 수집하고 라벨링한다.
- 사용 허가가 있는 공개 음식 이미지 데이터셋을 준비한다.
- 준비한 실사진으로 RTX 5090에서 재학습한다.

실사진 데이터가 준비되기 전에는 현재 모델을 실제 음식 인식 성능이 검증된 모델로 소개하면 안 된다.
