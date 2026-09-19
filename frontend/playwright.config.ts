import { defineConfig, devices } from '@playwright/test';
export default defineConfig({
  testDir: 'tests/e2e',
  testMatch: ['**/*.spec.ts'],
  testIgnore: ['**/src/**', '**/node_modules/**'],
  workers: 1,
  timeout: 45000,
  use: { baseURL: process.env.E2E_BASE_URL || 'http://localhost:3002',
    launchOptions: { args: ['--enable-unsafe-swiftshader'] },
    screenshot: 'only-on-failure', trace: 'retain-on-failure' },
  projects: [
    { name: 'desktop', use: { ...devices['Desktop Chrome'] } },
    { name: 'mobile', use: { ...devices['Desktop Chrome'], viewport: { width: 390, height: 844 } } },
  ],
});
