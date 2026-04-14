/**
 * Zustand auth store — access token lives here (in-memory, never localStorage).
 * The store is reset on page refresh; the httpOnly refresh_token cookie
 * lets the user recover a session silently via /auth/refresh.
 */
import { create } from 'zustand';
import type { User } from '@/lib/api';

interface AuthState {
  accessToken: string | null;
  user: User | null;
  isInitialized: boolean;

  setAuth: (token: string, user: User) => void;
  setAccessToken: (token: string) => void;
  clearAuth: () => void;
  setInitialized: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  accessToken: null,
  user: null,
  isInitialized: false,

  setAuth: (token, user) => set({ accessToken: token, user }),

  setAccessToken: (token) => set({ accessToken: token }),

  clearAuth: () => set({ accessToken: null, user: null }),

  setInitialized: () => set({ isInitialized: true }),
}));
