import type { MealEstimateResponse } from '../types/vision';
import { apiClient, setAccessToken } from '../lib/apiClient';
export interface VisionEstimateResponse { success: true; data: MealEstimateResponse; }
export class AuthenticationError extends Error {}
interface ApiFailure { response?: { status?: number; data?: any } }
async function request(path: string, options: RequestInit = {}) {
  try {
    const response = await apiClient.request({
      url: path,
      method: options.method || 'GET',
      data: options.body,
      headers: options.headers as Record<string, string> | undefined,
    });
    return response.data;
  } catch (error: unknown) {
    const failure = error as ApiFailure;
    const status = failure.response?.status;
    const payload = failure.response?.data;
    const code = payload?.error?.code || payload?.detail?.error?.code;
    const guidance: Record<string, string> = {
      ERR_GEOMETRY_PLANE_NOT_FOUND: '테이블 기준 평면을 찾지 못했습니다. 밝은 곳에서 접시와 주변 테이블이 함께 보이도록 다시 촬영해 주세요.',
      ERR_ZERO_OBJECT_DETECTED: '현재 모델이 지원하는 음식(백미밥, 시금치나물, 김치찌개, 된장찌개, 불고기, 연어구이, 바나나, 사과, 삶은 달걀)이 검출되지 않았습니다. 이 사진의 식재료를 분석하려면 실사진 학습 데이터 추가가 필요합니다.',
    };
    const detail = guidance[code] || payload?.error?.message || payload?.detail?.error?.message || payload?.detail;
    const message = typeof detail === 'string' ? detail : error instanceof Error ? error.message : `요청을 완료할 수 없습니다 (${status || 'unknown'}).`;
    if (status === 401) throw new AuthenticationError(message);
    throw new Error(message);
  }
}
export async function login(email: string, password: string): Promise<void> {
  const result = await request('/auth/login', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email, password }),
  });
  if (!result?.accessToken) throw new Error('로그인 응답 형식이 올바르지 않습니다.');
  setAccessToken(result.accessToken);
}
export async function register(email: string, password: string, name: string): Promise<void> {
  await request('/auth/register', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email, password, name }),
  });
}
export function logout(): void { setAccessToken(null); void apiClient.post('/auth/logout').catch(() => undefined); }
export async function getServiceStatus(): Promise<string> {
  const health = await request('/health');
  if (!health.metricDepthConfigured || !health.foodRecognitionConfigured || !health.nutritionConfigured) return '분석 데이터 준비 필요';
  if (!health.modelLoaded) return '모델 대기 중';
  return health.inferenceProviders.includes('CUDAExecutionProvider') ? 'GPU 추론 준비' : 'CPU 추론 준비';
}
export async function estimateMealVision(imageFile: File): Promise<VisionEstimateResponse> {
  if (imageFile.size === 0 || imageFile.size > 10 * 1024 * 1024) throw new Error('0바이트보다 크고 10MB 이하인 이미지를 선택해 주세요.');
  const formData = new FormData();
  formData.append('file', imageFile);
  const payload = await request('/vision/estimate', { method: 'POST', body: formData });
  if (payload?.success !== true || !payload.data) throw new Error('분석 응답 형식이 올바르지 않습니다.');
  return payload;
}

export interface MealListItem {
  id: string; imageUrl: string; totalCaloriesKcal: number; foodItemCount: number; highestRiskLevel: string; createdAt: string;
}
export interface MealDetail {
  id: string; createdAt: string; totalCaloriesKcal: number;
  foodItems: Array<{ id: string; foodName: string; volumeCm3: number; weightG: number; caloriesKcal: number }>;
  drugWarnings: Array<{ id: string; warningTitle: string; warningMessage: string }>;
}
export async function listMeals(): Promise<MealListItem[]> {
  const payload = await request('/meals');
  if (payload?.success !== true || !Array.isArray(payload?.data?.items)) {
    throw new Error('식단 기록 응답 형식이 올바르지 않습니다.');
  }
  return payload.data.items;
}
export async function getMeal(id: string): Promise<MealDetail> { return request(`/meals/${encodeURIComponent(id)}`); }

// Ref: FR-008, send identity and measurements; the server calculates nutrition.
export async function confirmMealVision(result: MealEstimateResponse): Promise<MealEstimateResponse> {
  if (result.foodItems.length === 0 || result.foodItems.some(item => item.requiresConfirmation)) {
    throw new Error('모든 음식 후보를 먼저 선택해 주세요.');
  }
  const payload = await request('/vision/confirm', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      mealId: result.mealId, imageUrl: result.imageUrl,
      focalLengthMm: result.focalLengthMm, isCalibrated: result.isCalibrated,
      detectedPills: result.detectedPills || [],
      confirmedItems: result.foodItems.map(item => ({
        itemId: item.id, foodId: item.foodId, weightG: item.weightG,
        volumeCm3: item.volumeCm3, confidenceScore: item.confidenceScore,
        bbox2d: item.bbox2d, bbox3d: item.bbox3d,
      })),
    }),
  });
  if (payload?.success !== true || payload?.data?.isPersisted !== true ||
      payload.data.mealId !== result.mealId || !Array.isArray(payload.data.foodItems) ||
      payload.data.foodItems.length !== result.foodItems.length ||
      result.foodItems.some(item => !payload.data.foodItems.some((saved: { id: string }) => saved.id === item.id))) {
    throw new Error('확정 저장 응답 형식이 올바르지 않습니다.');
  }
  return {
    ...result, ...payload.data, requiresConfirmation: false,
    foodItems: result.foodItems.map(item => ({
      ...item, ...payload.data.foodItems.find((saved: { id: string }) => saved.id === item.id),
      requiresConfirmation: false,
    })),
  };
}
