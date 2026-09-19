import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
const baseURL = (process.env.NEXT_PUBLIC_API_BASE_URL || '/api/v1').replace(/\/$/, '');
export const apiClient = axios.create({ baseURL, withCredentials: true, timeout: 120000 });
type RetryConfig = InternalAxiosRequestConfig & { _retry?: boolean };
let refreshPromise: Promise<void> | null = null;
// In-memory only (never localStorage, per Section 9.1); cleared on reload, refreshed via HttpOnly refresh_token cookie.
let accessToken: string | null = null;
export function setAccessToken(token: string | null) { accessToken = token; }
function notify(status: number, message: string) { if (typeof window !== 'undefined') window.dispatchEvent(new CustomEvent('volumeal:api-error', { detail: { status, message } })); }
apiClient.interceptors.request.use(config => { if (accessToken) config.headers.set('Authorization', `Bearer ${accessToken}`); return config; });
async function refresh() {
  const response = await axios.post<{ accessToken?: string }>(`${baseURL}/auth/refresh`, undefined, { withCredentials: true, timeout: 10000 });
  setAccessToken(response.data?.accessToken ?? null);
}
apiClient.interceptors.response.use(response => response, async (error: AxiosError<{ error?: { message?: string }; detail?: string }>) => {
  const status = error.response?.status; const config = error.config as RetryConfig | undefined;
  if (status === 401 && config && !config._retry && !config.url?.includes('/auth/')) { config._retry = true; refreshPromise ??= refresh().finally(() => { refreshPromise = null; }); await refreshPromise; return apiClient(config); }
  const message = error.response?.data?.error?.message || error.response?.data?.detail || error.message;
  if (status === 403 || status === 503 || status === 504) notify(status, message);
  return Promise.reject(error);
});
