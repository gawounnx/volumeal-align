import { test, expect } from '@playwright/test';

test('register then auto-login works without 403', async ({ page }) => {
  const email = `verify_${Date.now()}@example.com`;
  const errors: string[] = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.goto('/');
  await page.getByRole('button', { name: '회원가입하기' }).click();
  await page.getByLabel('이름').fill('검증계정');
  await page.getByLabel('이메일').fill(email);
  await page.getByLabel('비밀번호').fill('VerifyPassword123!');
  await page.getByRole('button', { name: '회원가입', exact: true }).click();
  await expect(page.getByRole('button', { name: '로그아웃', exact: true })).toBeVisible({ timeout: 10000 });
  const alert = page.getByRole('alert');
  await expect(alert).toHaveCount(0);
  expect(errors).toEqual([]);
});
