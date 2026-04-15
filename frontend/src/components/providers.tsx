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

/** Read a cookie value by name from document.cookie (client-side only). */
function getClientCookie(name: string): string | undefined {
  if (typeof document === 'undefined') return undefined;
  return document.cookie
    .split('; ')
    .find((row) => row.startsWith(`${name}=`))
    ?.split('=')[1];
}

/**
 * SessionGate — silently refreshes the access token on mount.
 * If the user already has a tb_role cookie (still logged in), we skip
 * the blocking spinner and refresh in the background.
 * Only shows a spinner on first-ever load with no cookie.
 * The middleware handles all auth-based redirects — this component only
 * manages the in-memory token and the blocking spinner.
 */
function SessionGate({ children }: { children: React.ReactNode }) {
  const { setAuth, setAccessToken, clearAuth, setInitialized, isInitialized } = useAuthStore();
  const attempted = useRef(false);

  // If the role cookie is present, the user is considered provisionally
  // authenticated — don't block rendering with a spinner.
  const hasRoleCookie = typeof window !== 'undefined' && !!getClientCookie('tb_role');

  useEffect(() => {
    if (attempted.current) return;
    attempted.current = true;

    authApi
      .refresh()
      .then(async (res) => {
        const token = res.data.access_token;
        setAccessToken(token);
        const meRes = await authApi.me();
        const user = meRes.data;
        // Single batched update — no double render
        setAuth(token, user);
        setRoleCookie(user.role);
      })
      .catch(() => {
        // Refresh failed — clear state. The middleware will redirect to /login
        // on the next navigation if the user hits a protected route.
        clearAuth();
        clearRoleCookie();
      })
      .finally(() => {
        setInitialized();
      });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Only block with spinner when there's no cookie hint — i.e. truly first load
  if (!isInitialized && !hasRoleCookie) {
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
