'use client';

import { useCallback, useEffect, useRef } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { useCurrentUser } from '@/hooks/useApi';
import { AUTH_TOKEN_KEY, REFRESH_TOKEN_KEY } from '@/lib/api';

const PUBLIC_ROUTES = ['/login'];

/**
 * Decode a JWT payload without verification (client-side only).
 * Returns null if the token is invalid or missing.
 */
function decodeJwtExp(token: string): number | null {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    return typeof payload.exp === 'number' ? payload.exp : null;
  } catch {
    return null;
  }
}

/**
 * Core auth hook — returns current user state from React Query.
 */
export function useAuth() {
  const { data: user, isLoading, isError } = useCurrentUser();

  const isAuthenticated =
    typeof window !== 'undefined' && !!localStorage.getItem(AUTH_TOKEN_KEY) && !!user;

  return { user: user ?? null, isLoading, isError, isAuthenticated };
}

/**
 * Guard hook — redirects unauthenticated users to /login.
 * Also manages session expiry warnings and multi-tab sync.
 * Use at the top of every protected page.
 */
export function useRequireAuth() {
  const router = useRouter();
  const pathname = usePathname();
  const queryClient = useQueryClient();
  const { user, isLoading, isAuthenticated } = useAuth();
  const warningTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // -------------------------------------------------------------------------
  // Redirect unauthenticated users
  // -------------------------------------------------------------------------
  useEffect(() => {
    if (isLoading) return;

    const hasToken =
      typeof window !== 'undefined' && !!localStorage.getItem(AUTH_TOKEN_KEY);

    if (!hasToken && !PUBLIC_ROUTES.includes(pathname)) {
      router.replace('/login');
    }
  }, [isLoading, isAuthenticated, pathname, router]);

  // -------------------------------------------------------------------------
  // Session expiry warning — toast 5 min before access token expires
  // -------------------------------------------------------------------------
  const scheduleExpiryWarning = useCallback(() => {
    if (warningTimerRef.current) {
      clearTimeout(warningTimerRef.current);
    }

    const token = typeof window !== 'undefined'
      ? localStorage.getItem(AUTH_TOKEN_KEY)
      : null;
    if (!token) return;

    const exp = decodeJwtExp(token);
    if (!exp) return;

    const nowSec = Math.floor(Date.now() / 1000);
    const secsUntilExpiry = exp - nowSec;
    const warningThresholdSec = 5 * 60; // 5 minutes

    if (secsUntilExpiry <= 0) return;

    const delayMs =
      secsUntilExpiry > warningThresholdSec
        ? (secsUntilExpiry - warningThresholdSec) * 1000
        : 0;

    warningTimerRef.current = setTimeout(() => {
      toast.warning('Your session expires soon. Saving your work...', {
        duration: 10_000,
      });
    }, delayMs);
  }, []);

  useEffect(() => {
    scheduleExpiryWarning();
    return () => {
      if (warningTimerRef.current) clearTimeout(warningTimerRef.current);
    };
  }, [isAuthenticated, scheduleExpiryWarning]);

  // -------------------------------------------------------------------------
  // Multi-tab session sync via storage event
  // -------------------------------------------------------------------------
  useEffect(() => {
    function handleStorageChange(e: StorageEvent) {
      if (e.key === AUTH_TOKEN_KEY) {
        if (!e.newValue) {
          // Token was removed in another tab — log out here too
          queryClient.clear();
          router.replace('/login');
        } else {
          // Token was refreshed in another tab — refetch user
          queryClient.invalidateQueries({ queryKey: ['currentUser'] });
          scheduleExpiryWarning();
        }
      }
    }

    window.addEventListener('storage', handleStorageChange);
    return () => window.removeEventListener('storage', handleStorageChange);
  }, [queryClient, router, scheduleExpiryWarning]);

  return { user: user ?? null, isLoading };
}
