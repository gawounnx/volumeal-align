# VoluMeal-Align frontend

백엔드를 8000 포트에서 실행한 다음 다음 명령으로 프론트를 실행합니다.

```sh
npm ci
npm run build
npm start
```

개발 모드는 `npm run dev`입니다. 브라우저는 프론트와 동일한 출처의 `/api/v1`로 요청합니다. Next 서버가 `API_BACKEND_URL`(기본 `http://0.0.0.0:8001`)로 전달합니다. 원격 배포에서 별도 백엔드를 사용하면 이 서버 환경변수를 빌드 시 설정하세요. 브라우저용 localhost 주소를 설정할 필요가 없습니다.

로그인 후 저장된 식단 목록과 상세를 조회할 수 있습니다. 토큰은 메모리에 보관하며 새로고침 또는 만료 후 다시 로그인합니다. 실제 분석 모델·영양 데이터가 준비되기 전에는 서버가 분석 성공 응답을 반환하지 않습니다.

## 검증

```sh
npm test
npm run typecheck
npx playwright install chromium
npm run test:e2e
```

E2E 테스트는 실행 중인 프론트·백엔드를 사용합니다. 기본 URL은 `http://127.0.0.1:3000`이며 `E2E_BASE_URL`로 바꿀 수 있습니다. 실제 서버 상태/인증 실패를 검증하고, 성공 시나리오는 명시적인 fixture 응답으로 로그인·업로드·WebGL·식단 기록 UI를 검증합니다. 실제 모델의 분석 정확도 검증과는 별개입니다. 데스크톱과 390px 모바일 화면을 검사하며 개인정보는 입력하지 않습니다.
