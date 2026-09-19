import { test, expect } from '@playwright/test';
import fixture from '../fixtures/vision-estimate.json';
import type { MealEstimateResponse } from '../../src/types/vision';

test('FR-008 candidate, weight correction, failed save and retry', async ({ page }) => {
  const data: MealEstimateResponse = structuredClone(fixture.data);
  data.isPersisted = false;
  data.requiresConfirmation = true;
  const item = data.foodItems[0];
  item.requiresConfirmation = true;
  item.topCandidates = [{ foodId: 'chosen', foodName: '선택 음식', score: 0.7,
    densityGCm3: 1, weightG: 100, caloriesKcal: 200, carbsG: 30, proteinG: 5, fatG: 3, sodiumMg: 20 }];
  let attempts = 0;
  await page.route('**/api/v1/health', route => route.fulfill({ json: {} }));
  await page.route('**/api/v1/auth/login', route => route.fulfill({ json: { accessToken: 'fixture' } }));
  await page.route('**/api/v1/meals', route => route.fulfill({ json: { success: true, data: { items: [] } } }));
  await page.route('**/api/v1/vision/estimate', route => route.fulfill({ json: { success: true, data } }));
  await page.route('**/api/v1/vision/confirm', async route => {
    attempts++;
    const body = route.request().postDataJSON();
    expect(body.mealId).toBe(data.mealId);
    expect(body.confirmedItems[0].foodId).toBe('chosen');
    expect(body.confirmedItems[0].weightG).toBe(200);
    expect(body.confirmedItems[0].volumeCm3).toBe(item.volumeCm3);
    expect(body.confirmedItems[0].caloriesKcal).toBeUndefined();
    if (attempts === 1) return route.fulfill({ status: 503, json: { error: { message: '저장 실패' } } });
    return route.fulfill({ json: { success: true, data: {
      ...data, isPersisted: true, requiresConfirmation: false, drugWarnings: [],
      totalNutrition: { caloriesKcal: 400, carbsG: 60, proteinG: 10, fatG: 6, sodiumMg: 40 },
      foodItems: [{ ...item, foodId: 'chosen', foodName: '선택 음식', weightG: 200, caloriesKcal: 400 }],
    } } });
  });
  await page.goto('/');
  await page.getByLabel('이메일').fill('fixture@test.invalid');
  await page.getByLabel('비밀번호').fill('fixture-password');
  await page.getByRole('button', { name: '로그인', exact: true }).click();
  await page.locator('input[type=file]').setInputFiles({ name: 'test.png', mimeType: 'image/png', buffer: Buffer.from('fixture') });
  await page.getByRole('button', { name: '식단 분석', exact: true }).click();
  const save = page.getByRole('button', { name: '확정하고 저장' });
  await expect(save).toBeDisabled();
  await page.getByRole('button', { name: /선택 음식/ }).click();
  await page.getByLabel('선택 음식 중량').fill('200');
  await expect(page.getByTestId('total-caloriesKcal')).toHaveText('400 kcal');
  await save.click();
  await expect(page.getByText('저장 실패', { exact: true })).toBeVisible();
  await expect(page.getByLabel('선택 음식 중량')).toHaveValue('200');
  await save.click();
  await expect(page.getByText('저장되었습니다.', { exact: true })).toBeVisible();
  await expect(save).toBeDisabled();
  expect(attempts).toBe(2);
});

test('FR-008 plane failure gives retake guidance', async ({ page }) => {
  await page.route('**/api/v1/health', route => route.fulfill({ json: {} }));
  await page.route('**/api/v1/auth/login', route => route.fulfill({ json: { accessToken: 'fixture' } }));
  await page.route('**/api/v1/meals', route => route.fulfill({ json: { success: true, data: { items: [] } } }));
  await page.route('**/api/v1/vision/estimate', route => route.fulfill({ status: 422,
    json: { error: { code: 'ERR_GEOMETRY_PLANE_NOT_FOUND', message: 'internal geometry detail' } } }));
  await page.goto('/');
  await page.getByLabel('이메일').fill('fixture@test.invalid');
  await page.getByLabel('비밀번호').fill('fixture-password');
  await page.getByRole('button', { name: '로그인', exact: true }).click();
  await page.locator('input[type=file]').setInputFiles({ name: 'test.png', mimeType: 'image/png', buffer: Buffer.from('fixture') });
  await page.getByRole('button', { name: '식단 분석', exact: true }).click();
  await expect(page.getByRole('main').getByRole('alert')).toContainText('접시와 주변 테이블이 함께 보이도록 다시 촬영');
});
