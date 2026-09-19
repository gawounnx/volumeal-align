import { test, expect } from '@playwright/test';
import path from 'path';

test('Live E2E: Phase 3 DoD - Mock Off, real image upload to backend (8001) and 3D viewer rendering', async ({ page }) => {
  test.setTimeout(60000);
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));

  // 1. 프론트엔드 접속 (포트 3002)
  await page.goto('/');
  await expect(page.locator('h1')).toContainText('VoluMeal-Align');

  // 2. 로그인 (백엔드 8001과 직접 통신)
  await page.getByLabel('이메일').fill('live-e2e-tester@example.com');
  await page.getByLabel('비밀번호').fill('Password123!');
  await page.getByRole('button', { name: '로그인', exact: true }).click();
  await expect(page.getByRole('button', { name: '로그아웃', exact: true })).toBeVisible({ timeout: 10000 });

  // 3. 실사진 파일 업로드
  const filePath = path.join(__dirname, '../fixtures/real_apple.jpg');
  await page.locator('input[type=file]').setInputFiles(filePath);

  // 4. 식단 분석 요청
  const analyzeBtn = page.getByRole('button', { name: '식단 분석', exact: true });
  await expect(analyzeBtn).toBeEnabled();
  await analyzeBtn.click();

  // 5. 백엔드(8001) 비전 추론 결과 대기 및 렌더링 확인 (최대 30초)
  await expect(page.getByRole('button', { name: /사과/ })).toBeVisible({ timeout: 30000 });
  await expect(page.getByText('추정 점군 · 3D 경계 상자 (m)')).toBeVisible();

  // 6. 3D WebGL Canvas 렌더링 점군 개수 검증 (최대 5,000점)
  const canvas = page.locator('canvas[data-testid="point-cloud-canvas"]');
  await expect(canvas).toBeVisible();
  const pointCountStr = await canvas.getAttribute('data-point-count');
  expect(pointCountStr).toBeTruthy();
  const pointCount = Number(pointCountStr);
  expect(pointCount).toBeGreaterThan(0);
  expect(pointCount).toBeLessThanOrEqual(5000);

  // 7. 영양소 DTO 확인 (칼로리 등 수치 표시)
  await expect(page.locator('body')).toContainText('kcal');

  // 8. 뷰포트 오버플로 및 에러 점검
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  expect(errors).toEqual([]);

  // 9. 결과 스크린샷 저장
  await page.screenshot({ path: path.join(__dirname, '../../test-results/live_e2e_verified.png'), fullPage: true });
});
