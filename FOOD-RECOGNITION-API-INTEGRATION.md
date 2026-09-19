# 외부 음식 인식 API 연동안

작성일: 2026-09-16

## 1. 목적

현재 로컬 세그멘테이션 모델은 합성 이미지 중심으로 학습되어 실제 음식 사진에서 검출이 실패할 수 있다. 외부 음식 인식 API를 선택적으로 연결하여 실사진 음식 인식의 대안을 제공한다.

외부 API는 프론트엔드에서 직접 호출하지 않고 백엔드가 호출한다.

```text
프론트 사진 업로드
  -> FastAPI /api/v1/vision/estimate
  -> 백엔드가 외부 음식 인식 API 호출
  -> 음식명·신뢰도·영역 수신
  -> 내부 foodId로 변환
  -> 영양·복약·3D 계산
  -> 프론트 응답a
```

## 2. 제공업체 선정 기준

후보 제공업체는 LogMeal, Clarifai Food Model, Google Cloud Vision 등이다. 실제 도입 전 다음 항목을 확인한다.

- 비빔밥, 김치찌개, 불고기 등 한국 음식 지원 여부
- 음식별 segmentation mask 제공 여부
- 음식별 bounding box 제공 여부
- confidence score 제공 여부
- 호출당 비용, rate limit, 무료 한도
- 업로드 이미지의 보관·재사용·지역 처리 정책
- API 장애 시 timeout과 재시도 정책
- 결과를 상업적·공모전 시연에 사용할 수 있는 라이선스

일반적인 이미지 라벨 API는 음식명을 반환하더라도 한국 음식 인식률이 보장되지 않을 수 있다. 문서상 지원 여부만으로 판단하지 말고 실제 테스트 이미지로 검증한다.

## 3. API 반환값과 가능한 기능

| 외부 API 반환값 | 가능한 기능 | 현재 파이프라인 연결성 |
|---|---|---|
| 음식명만 | 음식 분류, foodId 매핑, 영양 조회 | 가능하지만 3D 부피 계산 불가 |
| 음식명 + bbox | 음식 위치 표시, 후보 선택 | 제한적으로 가능 |
| 음식명 + segmentation mask | 음식 영역·부피·영양 계산 | 가장 적합 |
| 음식명 + 중량 | 영양 계산 | 자체 깊이·부피 계산과 중복 가능 |

외부 API가 bbox만 반환하면 음식 인식과 영양 계산은 할 수 있지만, 현재 RANSAC 기반 3D 부피 계산에는 직접 사용할 수 없다. 현재 기능을 유지하려면 segmentation mask를 반환하는 API를 우선한다.

## 4. 보안 및 환경변수

API key는 백엔드에만 보관한다. 프론트엔드 코드나 `NEXT_PUBLIC_*` 환경변수에 넣지 않는다.

```env
FOOD_RECOGNITION_PROVIDER=logmeal
LOGMEAL_API_TOKEN=<backend-only-secret>
LOGMEAL_API_BASE_URL=https://api.logmeal.com
LOGMEAL_TIMEOUT_SECONDS=8
```

운영 환경에서는 실제 키를 문서·Git·로그에 기록하지 않는다. 외부 API로 전송되는 이미지에 개인정보나 약제 정보가 포함될 수 있으므로, 제공업체의 저장·학습 재사용 정책과 사용자 고지 사항을 확인한다.

## 5. 내부 응답 계약

외부 업체마다 응답 형식이 다르므로 백엔드 어댑터에서 다음 내부 형식으로 정규화한다.

```python
class FoodRecognition:
    name: str
    confidence: float
  polygons: list[list[tuple[float, float]]] | None
  bbox: dict[str, float] | None
  processed_width: int | None
  processed_height: int | None
  provider_item_id: str | None
```

실제 구현에서는 프로젝트의 기존 schema와 validation 방식을 우선 사용한다. 외부 응답을 프론트엔드에 그대로 전달하지 않는다.

## 6. provider 어댑터 구조

```python
class FoodRecognitionProvider(Protocol):
    async def recognize(self, image_bytes: bytes) -> list[FoodRecognition]:
        ...
```

권장 provider 분기:

```text
FOOD_RECOGNITION_PROVIDER=local
  -> 현재 YOLO 세그멘테이션 모델

FOOD_RECOGNITION_PROVIDER=logmeal
  -> LogMeal segmentation/complete adapter
```

외부 API 호출 구현은 기존 vision endpoint에 직접 넣지 말고 별도 service/adapter로 분리한다. provider를 바꿔도 `/vision/estimate`의 내부 응답 계약은 유지해야 한다.

## 7. foodId 매핑

외부 음식명은 내부 식품 ID로 명시적으로 매핑한다.

```python
FOOD_NAME_MAP = {
    "banana": "banana",
    "apple": "apple",
    "bibimbap": "bibimbap",
    "kimchi stew": "kimchi_stew",
    "bulgogi": "bulgogi",
}
```

매핑되지 않은 음식은 임의의 foodId나 임의 영양값으로 성공 처리하지 않는다. 후보 선택을 요구하거나 지원하지 않는 음식 오류를 반환한다.

새 foodId를 추가할 때는 다음 데이터 계약을 함께 갱신한다.

- `food_catalog.json`
- `food_density_profiles.json`
- `food_nutrients.json`
- 기준 이미지 임베딩 인덱스
- 복약 상호작용 태그가 필요한 경우 interaction 규칙

## 8. 비빔밥 처리

1차 구현에서는 비빔밥을 재료별로 분리하지 않고 하나의 음식 객체로 처리한다.

```text
bibimbap = 하나의 음식 객체
```

사진에서는 밥·계란·나물·고추장 등을 포함한 전체 음식 영역을 하나의 mask로 라벨링한다. 그릇 테두리와 음식 바깥의 빈 공간은 포함하지 않는다.

영양 데이터는 대표 1인분 기준으로 등록한다. 재료별 영양 계산은 별도 확장 기능으로 남긴다.

## 9. 외부 API 도입 순서

1. 후보 API의 한국 음식 지원과 mask 제공 여부를 확인한다.
2. 실제 바나나·사과·비빔밥·김치찌개·불고기 사진으로 provider별 인식률을 비교한다.
3. API key를 백엔드 환경변수에만 설정한다.
4. provider adapter와 내부 응답 정규화를 구현한다.
5. 외부 음식명을 내부 `foodId`로 매핑한다.
6. API timeout, rate limit, 4xx/5xx, 빈 결과를 표준 오류로 변환한다.
7. `FOOD_RECOGNITION_PROVIDER=logmeal`로 통합 테스트한다.
8. mask가 반환되는 경우에만 3D 부피 계산과 연결한다.
9. 외부 API 장애 시 local provider 또는 명확한 503 오류로 처리한다.

## 10. 검증 항목

- 정상 이미지에서 지원 음식이 올바른 foodId로 매핑되는가
- confidence가 낮을 때 후보 선택을 요구하는가
- 여러 음식이 있는 이미지에서 각 음식이 분리되는가
- mask가 음식 외곽을 정확히 포함하는가
- mask가 없을 때 3D 부피 계산을 성공 처리하지 않는가
- 지원하지 않는 음식이 임의 foodId로 저장되지 않는가
- 외부 API timeout과 rate limit이 표준 오류로 변환되는가
- API key가 프론트 번들·응답·로그에 노출되지 않는가
- 외부 API 결과로 복약 경고와 영양 계산이 정상 동작하는가

## 11. 현재 결론

외부 음식 인식 API는 실제 사진 인식 문제의 대안이 될 수 있지만, 단순 영양 API는 사진 속 음식 검출을 해결하지 못한다. 현재 서비스의 3D 부피 계산까지 유지하려면 음식명뿐 아니라 segmentation mask를 제공하는 API가 필요하다.

LogMeal은 한국 음식 실사진 15장 검증(바나나·사과·비빔밥·김치찌개·불고기)을 통과하기 전까지 기본 provider로 활성화하지 않는다. 공식 응답 샘플을 기준으로 adapter, 환경변수, 테스트를 함께 유지한다.