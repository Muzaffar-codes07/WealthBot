import axios, { AxiosError, AxiosHeaders, type AxiosRequestConfig, type InternalAxiosRequestConfig } from 'axios';

export const AUTH_TOKEN_KEY = 'auth_token';
export const REFRESH_TOKEN_KEY = 'refresh_token';

// In the browser, use relative URLs so requests go through the Next.js rewrite
// proxy (same-origin → no CORS). During SSR, use the full backend URL directly.
const BASE_URL =
  typeof window !== 'undefined'
    ? ''  // browser: relative → hits Next.js rewrite at /api/:path*
    : (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000');

const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
});

apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem(AUTH_TOKEN_KEY);
    if (token) config.headers.set('Authorization', `Bearer ${token}`);
  }
  return config;
});

type RetriableConfig = AxiosRequestConfig & { _retry?: boolean };

let refreshPromise: Promise<string | null> | null = null;

async function performRefresh(): Promise<string | null> {
  if (typeof window === 'undefined') return null;
  const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
  if (!refreshToken) return null;

  try {
    const { data } = await axios.post<{ access_token: string; refresh_token: string }>(
      `${BASE_URL}/api/v1/auth/refresh`,
      { refresh_token: refreshToken },
      { headers: { 'Content-Type': 'application/json' } },
    );
    localStorage.setItem(AUTH_TOKEN_KEY, data.access_token);
    localStorage.setItem(REFRESH_TOKEN_KEY, data.refresh_token);
    return data.access_token;
  } catch {
    localStorage.removeItem(AUTH_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
      window.location.assign('/login');
    }
    return null;
  }
}

apiClient.interceptors.response.use(
  (r) => r,
  async (error: AxiosError) => {
    const original = error.config as RetriableConfig | undefined;
    if (!original || error.response?.status !== 401 || original._retry) {
      return Promise.reject(error);
    }
    const url = original.url ?? '';
    if (url.includes('/auth/refresh') || url.includes('/auth/token')) {
      return Promise.reject(error);
    }

    original._retry = true;
    refreshPromise = refreshPromise ?? performRefresh();
    const newToken = await refreshPromise;
    refreshPromise = null;

    if (!newToken) return Promise.reject(error);

    const headers = AxiosHeaders.from(original.headers as never);
    headers.set('Authorization', `Bearer ${newToken}`);
    original.headers = headers;
    return apiClient(original);
  },
);

export default apiClient;
