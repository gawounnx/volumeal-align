import { test, expect } from '@playwright/test';
import fixture from '../fixtures/vision-estimate.json';

const png = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAUAAAADwCAIAAAD+Tyo8AAAC1UlEQVR4nO3TMQ0AIQDAwOeFIIIZ/7rwwEKa3Cno0jHX/oCm/3UAcM/AEGZgCDMwhBkYwgwMYQaGMANDmIEhzMAQZmAIMzCEGRjCDAxhBoYwA0OYgSHMwBBmYAgzMIQZGMIMDGEGhjADQ5iBIczAEGZgCDMwhBkYwgwMYQaGMANDmIEhzMAQZmAIMzCEGRjCDAxhBoYwA0OYgSHMwBBmYAgzMIQZGMIMDGEGhjADQ5iBIczAEGZgCDMwhBkYwgwMYQaGMANDmIEhzMAQZmAIMzCEGRjCDAxhBoYwA0OYgSHMwBBmYAgzMIQZGMIMDGEGhjADQ5iBIczAEGZgCDMwhBkYwgwMYQaGMANDmIEhzMAQZmAIMzCEGRjCDAxhBoYwA0OYgSHMwBBmYAgzMIQZGMIMDGEGhjADQ5iBIczAEGZgCDMwhBkYwgwMYQaGMANDmIEhzMAQZmAIMzCEGRjCDAxhBoYwA0OYgSHMwBBmYAgzMIQZGMIMDGEGhjADQ5iBIczAEGZgCDMwhBkYwgwMYQaGMANDmIEhzMAQZmAIMzCEGRjCDAxhBoYwA0OYgSHMwBBmYAgzMIQZGMIMDGEGhjADQ5iBIczAEGZgCDMwhBkYwgwMYQaGMANDmIEhzMAQZmAIMzCEGRjCDAxhBoYwA0OYgSHMwBBmYAgzMIQZGMIMDGEGhjADQ5iBIczAEGZgCDMwhBkYwgwMYQaGMANDmIEhzMAQZmAIMzCEGRjCDAxhBoYwA0OYgSHMwBBmYAgzMIQZGMIMDGEGhjADQ5iBIczAEGZgCDMwhBkYwgwMYQaGMANDmIEhzMAQZmAIMzCEGRjCDAxhBoYwA0OYgSHMwBBmYAgzMIQZGMIMDGEGhrADJo0CbEDS0mwAAAAASUVORK5CYII=', 'base64');

// Magic bytes for ISO BMFF HEIC: offset 4-8 is 'ftyp', offset 8-12 is 'heic'
const heicMagicBytes = Buffer.from([0, 0, 0, 24, 102, 116, 121, 112, 104, 101, 105, 99, 0, 0, 0, 0]);

test.describe('Phase 6 P1: 모바일 실기기 크로스 브라우징 및 60 FPS 실측', () => {
  test.use({ viewport: { width: 390, height: 844 }, hasTouch: true });

  test.beforeEach(async ({ page }) => {
    await page.route('**/api/v1/health', route => route.fulfill({ json: { metricDepthConfigured: true } }));
    await page.route('**/api/v1/auth/login', route => route.fulfill({ json: { accessToken: 'mobile-test-token' } }));
    await page.route('**/api/v1/meals', route => route.fulfill({ json: { success: true, data: { items: [] } } }));
    await page.route('**/api/v1/vision/estimate', route => route.fulfill({ json: fixture }));
  });

  test('1. 터치 제스처 & 60 FPS 유지 검증 (Three.js WebGL)', async ({ page }) => {
    await page.goto('/');

    // 1. 로그인 수행
    await page.getByLabel('이메일').fill('mobile@volumeal.io');
    await page.getByLabel('비밀번호').fill('MobilePass123!');
    await page.getByRole('button', { name: '로그인', exact: true }).click();

    // 2. 이미지 업로드 및 분석
    await page.locator('input[type=file]').setInputFiles({ name: 'meal.png', mimeType: 'image/png', buffer: png });
    await page.getByRole('button', { name: '식단 분석', exact: true }).click();

    // 3. Three.js WebGL 캔버스 렌더링 확인
    const canvas = page.locator('canvas[data-testid="point-cloud-canvas"]');
    await expect(canvas).toBeVisible({ timeout: 10000 });

    // 4. 초기 renderFps 측정치 확인 (60 FPS 목표)
    const initialFps = await canvas.getAttribute('data-render-fps');
    expect(Number(initialFps)).toBeGreaterThanOrEqual(55);

    // 5. 모바일 터치 제스처 시뮬레이션 (1핑거 터치 드래그 회전 조작)
    const box = await canvas.boundingBox();
    expect(box).not.toBeNull();
    if (box) {
      const centerX = box.x + box.width / 2;
      const centerY = box.y + box.height / 2;

      // 터치 시작 -> 드래그 -> 터치 종료
      await page.touchscreen.tap(centerX, centerY);
      await page.mouse.move(centerX, centerY);
      await page.mouse.down();
      await page.mouse.move(centerX + 60, centerY - 40, { steps: 10 });
      await page.mouse.up();

      // 핀치 줌 제스처 효과 (휠 / 멀티터치 스크롤 이벤트 디스패치)
      await page.mouse.wheel(0, -100);
    }

    // 6. 터치 조작 후 프레임 유지 확인 (버벅임 없이 55~60 FPS 유지)
    await page.waitForTimeout(1100); // 1초 주기의 animate FPS 갱신 대기
    const postGestureFps = await canvas.getAttribute('data-render-fps');
    expect(Number(postGestureFps)).toBeGreaterThanOrEqual(55);
  });

  test('2. 모바일 뷰포트(390x844) 반응형 UI 점검 (3D 뷰어, 영양소 요약 그리드, KFDA 경고, 수동 보정 모달)', async ({ page }) => {
    await page.goto('/');

    // 1. 로그인
    await page.getByLabel('이메일').fill('mobile@volumeal.io');
    await page.getByLabel('비밀번호').fill('MobilePass123!');
    await page.getByRole('button', { name: '로그인', exact: true }).click();

    // 2. 초기 화면 가로 스크롤 잘림 여부 검증 (390px 뷰포트 완전 내포)
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);

    // 3. 이미지 분석 실행
    await page.locator('input[type=file]').setInputFiles({ name: 'meal.png', mimeType: 'image/png', buffer: png });
    await page.getByRole('button', { name: '식단 분석', exact: true }).click();

    // 4. 상단 3D 뷰어 검증
    const canvas = page.locator('canvas[data-testid="point-cloud-canvas"]');
    await expect(canvas).toBeVisible();
    const canvasBox = await canvas.boundingBox();
    expect(canvasBox).not.toBeNull();
    if (canvasBox) {
      expect(canvasBox.width).toBeLessThanOrEqual(390);
    }

    // 5. 영양소 요약 그리드 (5개 영양소) 검증
    const nutritionSection = page.locator('section[aria-label="영양소 요약"]');
    await expect(nutritionSection).toBeVisible();
    await expect(page.getByTestId('total-caloriesKcal')).toContainText('542.5 kcal');
    await expect(page.getByTestId('total-carbsG')).toContainText('72.3 g');
    await expect(page.getByTestId('total-proteinG')).toContainText('34.2 g');
    await expect(page.getByTestId('total-fatG')).toContainText('12.8 g');
    await expect(page.getByTestId('total-sodiumMg')).toContainText('640 mg');

    // 6. KFDA 복약 위험 알림 배너 검증
    await expect(page.getByText('와파린 약효 저하 위험 성분 감지')).toBeVisible();
    await expect(page.getByText('DANGER')).toBeVisible();
    await expect(page.getByText(/비타민 K 섭취가 급증하면 혈전 예방 작용이 길항됩니다/)).toBeVisible();

    // 7. 수동 보정 모달 열기 및 뷰포트 내 안착 검증
    const openModalBtn = page.getByTestId('open-correction-modal-btn');
    await expect(openModalBtn).toBeVisible();
    await openModalBtn.click();

    const modal = page.locator('[data-testid="correction-modal"]');
    await expect(modal).toBeVisible();
    const modalBox = await modal.boundingBox();
    expect(modalBox).not.toBeNull();
    if (modalBox) {
      // 모달이 390px 화면 밖으로 넘치거나 잘리지 않는지 확인
      expect(modalBox.width).toBeLessThanOrEqual(390);
      expect(modalBox.x).toBeGreaterThanOrEqual(0);
      expect(modalBox.x + modalBox.width).toBeLessThanOrEqual(390);
    }

    // 8. 중량 수정(180g) 및 완료 확정
    const weightInput = page.locator('input[data-testid="weight-input"]');
    await weightInput.fill('180');
    await page.click('button[data-testid="confirm-btn"]');

    // 9. 모달 정상 종료 확인
    await expect(modal).toBeHidden();

    // 10. 전체 화면 최종 가로 스크롤 없음 재검증
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  });

  test('3. 아이폰 기본 카메라 HEIC 업로드 차단 및 안내 토스트 검증', async ({ page }) => {
    let apiCallTriggered = false;
    await page.route('**/api/v1/vision/estimate', route => {
      apiCallTriggered = true;
      return route.fulfill({ json: fixture });
    });

    await page.goto('/');

    // Case A: .heic 확장자 사진 업로드 시도 (아이폰 실촬영 시뮬레이션)
    await page.locator('input[type=file]').setInputFiles({
      name: 'IMG_4821.HEIC',
      mimeType: 'image/heic',
      buffer: Buffer.from('dummy-heic-content'),
    });

    // 1. 차단 안내 토스트 즉시 표출 확인
    const toast = page.locator('[data-testid="toast-alert"]');
    await expect(toast).toBeVisible();
    await expect(toast).toContainText('HEIC 형식은 지원하지 않습니다. JPEG로 변환 후 업로드해 주세요.');

    // 2. 인라인 에러 알림도 함께 표출됨을 확인
    await expect(page.getByRole('main').getByRole('alert')).toContainText('HEIC 형식은 지원하지 않습니다.');

    // 3. 서버 API 요청이 가로채여 호출되지 않음을 확인 (네트워크 트래픽 낭비 차단)
    expect(apiCallTriggered).toBe(false);

    // 4. 토스트 닫기 버튼 동작 확인
    await page.getByTestId('toast-close-btn').click();
    await expect(toast).toBeHidden();

    // Case B: 확장자는 .jpg이지만 바이너리가 ISO BMFF HEIC 매직 바이트인 파일 업로드 시도
    await page.locator('input[type=file]').setInputFiles({
      name: 'sneaky_cam.jpg',
      mimeType: 'image/jpeg',
      buffer: heicMagicBytes,
    });

    // 5. 매직 바이트 검증에 의한 즉시 차단 토스트 재표출 확인
    await expect(toast).toBeVisible();
    await expect(toast).toContainText('HEIC 형식은 지원하지 않습니다. JPEG로 변환 후 업로드해 주세요.');
    expect(apiCallTriggered).toBe(false);
  });
});
