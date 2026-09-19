# 실제 음식 사진 데이터 준비

현재 이 폴더에는 실사진이 없다. 실제 음식 사진을 준비한 뒤 아래 구조로 넣는다.

```text
real_food/
  images/
    train/
    val/
    test/
  labels/
    train/
    val/
    test/
```

## 1차 시연용 사진 수량

처음에는 아래 6개 음식만 준비한다. 음식별로 학습 40장, 검증 10장, 테스트 10장씩 총 60장이다.

| 클래스 | 학습 | 검증 | 테스트 | 총합 |
|---|---:|---:|---:|---:|
| `white_rice` | 40 | 10 | 10 | 60 |
| `spinach_namul` | 40 | 10 | 10 | 60 |
| `kimchi_stew` | 40 | 10 | 10 | 60 |
| `bulgogi` | 40 | 10 | 10 | 60 |
| `banana` | 40 | 10 | 10 | 60 |
| `apple` | 40 | 10 | 10 | 60 |

전체 목표는 음식 사진 360장이다. 사진 한 장에 음식 인스턴스가 여러 개 있으면 각 인스턴스에 모두 polygon 라벨을 작성한다.

## 음식별 촬영 구성

- `white_rice`: 흰쌀밥 1인분·반 인분·많은 양, 접시와 공기의 변화
- `spinach_namul`: 반찬 그릇·접시, 적은 양·많은 양, 겹쳐 놓인 나물
- `kimchi_stew`: 국물과 건더기가 보이는 그릇, 위·사선 촬영, 양 변화
- `bulgogi`: 고기 조각이 흩어진 상태와 겹친 상태, 접시·반찬 배경 변화
- `banana`: 껍질을 벗긴 바나나 조각과 통바나나, 방향과 절단면 변화
- `apple`: 통사과와 자른 사과, 껍질 유무와 조명 변화

각 음식은 위에서 찍은 사진과 사선 사진을 섞고, 밝기·배경·그릇·음식 양을 바꾼다. 같은 사진을 복사해서 수량만 늘리면 안 된다.

## 파일을 넣는 정확한 위치

예를 들어 `white_rice` 사진은 다음처럼 넣는다.

```text
/workspace/backend/data/real_food/images/train/white_rice_001.jpg
/workspace/backend/data/real_food/images/train/white_rice_040.jpg
/workspace/backend/data/real_food/images/val/white_rice_041.jpg
/workspace/backend/data/real_food/images/val/white_rice_050.jpg
/workspace/backend/data/real_food/images/test/white_rice_051.jpg
/workspace/backend/data/real_food/images/test/white_rice_060.jpg
```

나머지 클래스도 같은 규칙을 사용한다.

```text
/workspace/backend/data/real_food/images/train/<class>_001.jpg ~ <class>_040.jpg
/workspace/backend/data/real_food/images/val/<class>_041.jpg ~ <class>_050.jpg
/workspace/backend/data/real_food/images/test/<class>_051.jpg ~ <class>_060.jpg
```

## 라벨 파일 위치

학습과 정량 검증을 하려면 이미지와 같은 이름의 `.txt` 파일을 만든다.

```text
/workspace/backend/data/real_food/labels/train/white_rice_001.txt
/workspace/backend/data/real_food/labels/val/white_rice_041.txt
/workspace/backend/data/real_food/labels/test/white_rice_051.txt
```

라벨은 YOLO segmentation polygon 형식이며 좌표는 0~1로 정규화한다.

```text
0 x1 y1 x2 y2 x3 y3 x4 y4
```

현재 임시 클래스 ID는 다음과 같다.

```text
0 white_rice
1 spinach_namul
2 kimchi_stew
3 bulgogi
4 banana
5 apple
```

`/workspace/backend/data/real_food.yaml`은 위 6개 클래스를 0부터 연속된 ID로 정의한다.

## 필요한 자료

- 음식이 실제로 촬영된 JPEG 또는 PNG 이미지
- 음식별 YOLO segmentation polygon 라벨
- 이미지와 같은 파일명의 `.txt` 라벨
- 학습에 사용할 클래스 목록과 foodId 매핑

## 촬영 권장 조건

- 위에서 찍은 사진과 사선에서 찍은 사진을 모두 준비
- 음식 전체와 접시 경계가 보이도록 촬영
- 밝기와 배경을 다양하게 구성
- 한 음식 사진, 여러 음식 사진, 약제가 함께 있는 사진을 구분해 준비
- 학습·검증·테스트 사진이 서로 중복되지 않도록 분리

## 중요한 주의사항

현재 모델 `/workspace/backend/weights/kfood_seg_run/weights/best.onnx`는 합성 데이터셋
`/workspace/backend/data/kfood`로 학습된 모델이다. 실사진을 이 폴더에 넣는 것만으로
모델이 실사진을 학습하는 것은 아니다. 실제 학습을 하려면 라벨링 후 별도 학습을 실행하고,
검증된 새 `best.pt` 또는 `best.onnx`를 만든 뒤 백엔드의 `ONNX_SEG_MODEL_PATH`를 교체해야 한다.

실사진 라벨이 아직 없으면 먼저 `test/`에 사진만 모아 추론 검증용으로 사용한다. 이 경우
학습 데이터가 아니므로 모델 정확도 개선이나 실사진 학습 완료로 판단하지 않는다.
