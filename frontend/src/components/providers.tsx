'use client';

import { useEffect, useRef } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useAuthStore } from '@/stores/auth';
import { authApi } from '@/lib/api';
import { setRoleCookie, clearRoleCookie } from '@/lib/auth';

// Stable QueryClient instance (created once per browser session)
function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 60 * 1000, // 1 min
        retry: 1,
      },
    },
  });
}

let browserQueryClient: QueryClient | undefined;

function getQueryClient() {
  if (typeof window === 'undefined') return makeQueryClient();
  if (!browserQueryClient) browserQueryClient = makeQueryClient();
  return browserQueryClient;
}

/**
 * SessionGate — on first mount, attempt a silent token refresh so users
 * who previously logged in don't see a flash of the login page.
 */
function SessionGate({ children }: { children: React.ReactNode }) {
  const { setAuth, clearAuth, setInitialized, isInitialized } = useAuthStore();
  const attempted = useRef(false);

  useEffect(() => {
    if (attempted.current) return;
    attempted.current = true;

    authApi
      .refresh()
      .then(async (res) => {
        const token = res.data.access_token;
        // Fetch user info with the new token
        const meRes = await authApi.me();
        const user = meRes.data;
        setAuth(token, user);
        setRoleCookie(user.role);
      })
      .catch(() => {
        // No valid refresh token — user needs to log in
        clearAuth();
        clearRoleCookie();
      })
      .finally(() => {
        setInitialized();
      });
  }, [setAuth, clearAuth, setInitialized]);

  // Brief loading gate — avoids hydration flash
  if (!isInitialized) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-brand-600 border-t-transparent" />
      </div>
    );
  }

  return <>{children}</>;
}

export function Providers({ children }: { children: React.ReactNode }) {
  const queryClient = getQueryClient();

  return (
    <QueryClientProvider client={queryClient}>
      <SessionGate>{children}</SessionGate>
    </QueryClientProvider>
  );
}
