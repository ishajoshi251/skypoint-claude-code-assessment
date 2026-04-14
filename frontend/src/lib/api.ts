/**
 * Typed axios client.
 *
 * - Attaches the in-memory access token to every request.
 * - On 401, attempts a silent token refresh then retries once.
 * - On second 401 (refresh failed), clears auth state and redirects to /login.
 */
import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios';
import { useAuthStore } from '@/stores/auth';

const BASE_URL =
  typeof window === 'undefined'
    ? process.env.NEXT_PUBLIC_API_URL || 'http://api:8000'
    : '/api'; // browser → rewrite via next.config.mjs

export const apiClient = axios.create({
  baseURL: `${BASE_URL}/api/v1`,
  withCredentials: true, // send httpOnly refresh_token cookie
  headers: { 'Content-Type': 'application/json' },
});

// ---- Request interceptor: attach access token ----
apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = useAuthStore.getState().accessToken;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ---- Response interceptor: handle 401 with silent refresh ----
let _refreshing = false;
let _queue: Array<(token: string | null) => void> = [];

function _processQueue(token: string | null) {
  _queue.forEach((cb) => cb(token));
  _queue = [];
}

apiClient.interceptors.response.use(
  (res) => res,
  async (error: AxiosError) => {
    const original = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    if (error.response?.status !== 401 || original?._retry) {
      return Promise.reject(error);
    }

    if (_refreshing) {
      // Queue request until refresh resolves
      return new Promise((resolve, reject) => {
        _queue.push((token) => {
          if (token) {
            original.headers.Authorization = `Bearer ${token}`;
            resolve(apiClient(original));
          } else {
            reject(error);
          }
        });
      });
    }

    original._retry = true;
    _refreshing = true;

    try {
      const { data } = await axios.post(
        `${BASE_URL}/api/v1/auth/refresh`,
        {},
        { withCredentials: true },
      );
      const newToken: string = data.access_token;
      useAuthStore.getState().setAccessToken(newToken);
      _processQueue(newToken);
      original.headers.Authorization = `Bearer ${newToken}`;
      return apiClient(original);
    } catch {
      _processQueue(null);
      useAuthStore.getState().clearAuth();
      if (typeof window !== 'undefined') {
        window.location.href = '/login';
      }
      return Promise.reject(error);
    } finally {
      _refreshing = false;
    }
  },
);

// ---------------------------------------------------------------------------
// Typed API helpers
// ---------------------------------------------------------------------------

export interface User {
  id: number;
  email: string;
  role: 'HR' | 'CANDIDATE';
  is_active: boolean;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export const authApi = {
  login: (email: string, password: string) =>
    apiClient.post<AuthResponse>('/auth/login', { email, password }),

  register: (email: string, password: string, role: 'HR' | 'CANDIDATE') =>
    apiClient.post<AuthResponse>('/auth/register', { email, password, role }),

  refresh: () =>
    apiClient.post<{ access_token: string }>('/auth/refresh'),

  logout: () =>
    apiClient.post('/auth/logout'),

  me: () =>
    apiClient.get<User>('/auth/me'),
};
