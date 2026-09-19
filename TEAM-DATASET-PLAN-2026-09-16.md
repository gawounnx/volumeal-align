# 2인 실사진 데이터셋 작업 분담

작성일: 2026-09-16
목표: 6개 음식, 총 360장 실사진 데이터셋 구축

## 1. 전체 목표

대상 음식:

```text
white_rice
spinach_namul
kimchi_stew
bulgogi
banana
grapefruit
```

음식별 목표:

- 학습 40장
- 검증 10장
- 테스트 10장
- 음식별 총 60장
- 팀 전체 총 360장

## 2. 팀원 A: 식사·반찬류

담당 음식:

```text
white_rice
spinach_namul
kimchi_stew
```

각 음식별 촬영·라벨링 수량:

```text
white_rice: 40 train + 10 val + 10 test = 60장
spinach_namul: 40 train + 10 val + 10 test = 60장
kimchi_stew: 40 train + 10 val + 10 test = 60장
```

팀원 A의 담당량은 총 180장이다.

## 3. 팀원 B: 육류·과일류

담당 음식:

```text
bulgogi
banana
grapefruit
```

각 음식별 촬영·라벨링 수량:

```text
bulgogi: 40 train + 10 val + 10 test = 60장
banana: 40 train + 10 val + 10 test = 60장
grapefruit: 40 train + 10 val + 10 test = 60장
```

팀원 B의 담당량은 총 180장이다.

## 4. 촬영 조건

각 담당자는 맡은 음식마다 다음 조건을 다양하게 섞는다.

- 위에서 촬영한 사진과 사선 촬영 사진
- 적은 양, 보통 양, 많은 양
- 서로 다른 접시와 그릇
- 밝은 조명과 약간 어두운 조명
- 서로 다른 배경
- 음식 하나만 있는 사진과 여러 음식이 함께 있는 사진
- 음식이 겹치거나 일부 가려진 사진

같은 사진을 복사하거나 거의 같은 연속 프레임만으로 수량을 채우지 않는다.

## 5. 파일명 규칙

팀원 A:

```text
A_white_rice_001.jpg
A_spinach_namul_001.jpg
A_kimchi_stew_001.jpg
```

팀원 B:

```text
B_bulgogi_001.jpg
B_banana_001.jpg
B_grapefruit_001.jpg
```

파일명에는 담당자, 클래스명, 일련번호를 포함한다.

## 6. 저장 경로

최종 이미지는 다음 경로에 저장한다.

```text
/workspace/backend/data/real_food/images/train
/workspace/backend/data/real_food/images/val
/workspace/backend/data/real_food/images/test
```

라벨은 이미지와 같은 파일명으로 다음 경로에 저장한다.

```text
/workspace/backend/data/real_food/labels/train
/workspace/backend/data/real_food/labels/val
/workspace/backend/data/real_food/labels/test
```

예시:

```text
images/train/A_white_rice_001.jpg
labels/train/A_white_rice_001.txt
images/val/B_banana_041.jpg
labels/val/B_banana_041.txt
images/test/A_grapefruit_051.jpg
labels/test/A_grapefruit_051.txt
```

## 7. 라벨링과 교차 검수

담당자가 자신의 사진을 먼저 YOLO segmentation polygon 형식으로 라벨링한다. 이후 서로 상대방의 사진과 라벨을 검수한다.

- 팀원 A: 팀원 B의 사진·라벨 검수
- 팀원 B: 팀원 A의 사진·라벨 검수

검수 항목:

- polygon이 음식 외곽을 정확히 감싸는가
- 배경과 접시가 음식 polygon에 포함되지 않았는가
- 음식이 여러 개면 모든 인스턴스가 라벨되었는가
- 클래스 ID가 올바른가
- 이미지와 라벨 파일명이 정확히 일치하는가
- 흐리거나 음식이 거의 보이지 않는 사진은 제외했는가

## 8. 분할 규칙

- 같은 사진의 복사본을 train과 test에 동시에 넣지 않는다.
- 같은 촬영 연속 프레임은 같은 분할에만 둔다.
- 테스트 사진은 학습 중 사용하지 않는다.
- 각 음식의 train 40장, val 10장, test 10장을 유지한다.
- 새 촬영 환경이 train·val·test에 모두 포함되도록 한다.

## 9. 완료 후 작업

1. 6개 클래스만 포함한 `real_food.yaml` 작성
2. YOLO 라벨 클래스 ID 검증
3. 이미지·라벨 누락 검사
4. RTX 5090에서 재학습
5. 테스트 세트로 성능 측정
6. 실사진 기준 DINO 임베딩 인덱스 재생성
7. 새 ONNX 모델을 백엔드에 연결

실시간 추론만 먼저 확인할 때는 `images/test`에 사진만 넣어도 된다. 재학습과 정량 평가에는 라벨 파일이 필요하다.
