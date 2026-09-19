import { test, expect } from '@playwright/test';
import fixture from '../fixtures/vision-estimate.json';
// A synthetic local image. Success responses below are fixtures, not model validation.
const png = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAUAAAADwCAIAAAD+Tyo8AAAC1UlEQVR4nO3TMQ0AIQDAwOeFIIIZ/7rwwEKa3Cno0jHX/oCm/3UAcM/AEGZgCDMwhBkYwgwMYQaGMANDmIEhzMAQZmAIMzCEGRjCDAxhBoYwA0OYgSHMwBBmYAgzMIQZGMIMDGEGhjADQ5iBIczAEGZgCDMwhBkYwgwMYQaGMANDmIEhzMAQZmAIMzCEGRjCDAxhBoYwA0OYgSHMwBBmYAgzMIQZGMIMDGEGhjADQ5iBIczAEGZgCDMwhBkYwgwMYQaGMANDmIEhzMAQZmAIMzCEGRjCDAxhBoYwA0OYgSHMwBBmYAgzMIQZGMIMDGEGhjADQ5iBIczAEGZgCDMwhBkYwgwMYQaGMANDmIEhzMAQZmAIMzCEGRjCDAxhBoYwA0OYgSHMwBBmYAgzMIQZGMIMDGEGhjADQ5iBIczAEGZgCDMwhBkYwgwMYQaGMANDmIEhzMAQZmAIMzCEGRjCDAxhBoYwA0OYgSHMwBBmYAgzMIQZGMIMDGEGhjADQ5iBIczAEGZgCDMwhBkYwgwMYQaGMANDmIEhzMAQZmAIMzCEGRjCDAxhBoYwA0OYgSHMwBBmYAgzMIQZGMIMDGEGhjADQ5iBIczAEGZgCDMwhBkYwgwMYQaGMANDmIEhzMAQZmAIMzCEGRjCDAxhBoYwA0OYgSHMwBBmYAgzMIQZGMIMDGEGhjADQ5iBIczAEGZgCDMwhBkYwgwMYQaGMANDmIEhzMAQZmAIMzCEGRjCDAxhBoYwA0OYgSHMwBBmYAgzMIQZGMIMDGEGhjADQ5iBIczAEGZgCDMwhBkYwgwMYQaGMANDmIEhzMAQZmAIMzCEGRjCDAxhBoYwA0OYgSHMwBBmYAgzMIQZGMIMDGEGhjADQ5iBIczAEGZgCDMwhBkYwgwMYQaGMANDmIEhzMAQZmAIMzCEGRjCDAxhBoYwA0OYgSHMwBBmYAgzMIQZGMIMDGEGhrADJo0CbEDS0mwAAAAASUVORK5CYII=', 'base64');

test('live proxy, authentication boundary and mobile layout', async ({ page, request }) => {
  const health = await request.get('/api/v1/health');
  expect(health.status()).toBe(200);
  expect(typeof (await health.json()).metricDepthConfigured).toBe('boolean');
  expect((await request.get('/api/v1/meals')).status()).toBe(401);
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('/');
  await expect(page.locator('header').getByText(/분석 데이터 준비 필요|모델 대기 중|CPU 추론 준비|GPU 추론 준비|서버 연결 확인 필요/, { exact: true })).toBeVisible();
  await page.getByLabel('이메일').fill('browser-check@test.invalid');
  await page.getByLabel('비밀번호').fill('wrong-password');
  await page.getByRole('button', { name: '로그인', exact: true }).click();
  await expect(page.getByRole('main').getByRole('alert')).toContainText('올바르지 않습니다');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  expect(errors).toEqual([]);
});

test('fixture login, upload, WebGL and saved meal detail', async ({ page }, testInfo) => {
  let saved = false;
  let authorized = false;
  await page.route('**/api/v1/auth/login', route => route.fulfill({ json: { accessToken: 'test-token' } }));
  await page.route('**/api/v1/meals', route => {
    authorized = route.request().headers()['authorization'] === 'Bearer test-token';
    return route.fulfill({ json: { success: true, data: { items: saved ? [{ id: fixture.data.mealId, totalCaloriesKcal: 542.5, foodItemCount: 1, warningCount: 1, createdAt: fixture.data.processedAt }] : [] } } });
  });
  await page.route(`**/api/v1/meals/${fixture.data.mealId}`, route => route.fulfill({ json: {
    id: fixture.data.mealId, createdAt: fixture.data.processedAt, totalCaloriesKcal: 542.5,
    foodItems: fixture.data.foodItems, drugWarnings: fixture.data.drugWarnings,
  } }));
  await page.route('**/api/v1/vision/estimate', route => { saved = true; return route.fulfill({ json: fixture }); });
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('/');
  await page.getByLabel('이메일').fill('fixture@test.invalid');
  await page.getByLabel('비밀번호').fill('test-password');
  await page.getByRole('button', { name: '로그인', exact: true }).click();
  await expect(page.getByText('저장된 식단이 없습니다.')).toBeVisible();
  expect(authorized).toBe(true);
  await page.locator('input[type=file]').setInputFiles({ name: 'sample.png', mimeType: 'image/png', buffer: png });
  await page.getByRole('button', { name: '식단 분석', exact: true }).click();
  await expect(page.getByText('백미밥', { exact: true })).toBeVisible();
  await expect(page.getByText('추정 점군 · 3D 경계 상자 (m)')).toBeVisible();
  await page.getByRole('button', { name: /542.5 kcal · 음식 1개/ }).click();
  await expect(page.getByLabel('식단 상세')).toContainText('백미밥');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: testInfo.outputPath('analysis.png'), fullPage: true });
  expect(errors).toEqual([]);
});

test('expired token restores login UI', async ({ page }) => {
  await page.route('**/api/v1/auth/login', route => route.fulfill({ json: { accessToken: 'test-token' } }));
  await page.route('**/api/v1/meals', route => route.fulfill({ json: { success: true, data: { items: [] } } }));
  await page.route('**/api/v1/vision/estimate', route => route.fulfill({ status: 401, json: { detail: '로그인이 만료되었습니다.' } }));
  await page.goto('/');
  await page.getByLabel('이메일').fill('fixture@test.invalid');
  await page.getByLabel('비밀번호').fill('test-password');
  await page.getByRole('button', { name: '로그인', exact: true }).click();
  await expect(page.getByRole('button', { name: '로그아웃', exact: true })).toBeVisible();
  await page.locator('input[type=file]').setInputFiles({ name: 'sample.png', mimeType: 'image/png', buffer: png });
  await page.getByRole('button', { name: '식단 분석', exact: true }).click();
  await expect(page.getByRole('button', { name: '로그인', exact: true })).toBeVisible();
  await expect(page.getByRole('main').getByRole('alert')).toContainText('만료');
});
