'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import apiClient, { AUTH_TOKEN_KEY, REFRESH_TOKEN_KEY } from '@/lib/api';
import type {
  AIChatResponse,
  LoginRequest,
  PaginatedResponse,
  RegisterRequest,
  SafeToSpendData,
  SpendingVelocityResponse,
  StatementUploadResponse,
  SubscriptionsResponse,
  TokenResponse,
  TransactionData,
  UserProfile,
} from '@/types';

function getToken(): string | null {
  return typeof window !== 'undefined' ? localStorage.getItem(AUTH_TOKEN_KEY) : null;
}

// =============================================================================
// Auth Hooks
// =============================================================================

export function useLogin() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (body: LoginRequest) => {
      const { data } = await apiClient.post<TokenResponse>(
        '/api/v1/auth/token',
        body,
      );
      return data;
    },
    onSuccess: (data) => {
      localStorage.setItem(AUTH_TOKEN_KEY, data.access_token);
      localStorage.setItem(REFRESH_TOKEN_KEY, data.refresh_token);
      queryClient.invalidateQueries({ queryKey: ['currentUser'] });
    },
  });
}

export function useRegister() {
  return useMutation({
    mutationFn: async (body: RegisterRequest) => {
      const { data } = await apiClient.post<UserProfile>(
        '/api/v1/auth/register',
        body,
      );
      return data;
    },
  });
}

export function useCurrentUser() {
  return useQuery({
    queryKey: ['currentUser'],
    queryFn: async () => {
      const { data } = await apiClient.get<UserProfile>('/api/v1/users/me');
      return data;
    },
    enabled: !!getToken(),
    retry: false,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

export function useLogout() {
  const queryClient = useQueryClient();
  const router = useRouter();

  return () => {
    localStorage.removeItem(AUTH_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    queryClient.clear();
    router.push('/login');
  };
}

// =============================================================================
// Safe-to-Spend Hook
// =============================================================================

export function useSafeToSpend() {
  return useQuery({
    queryKey: ['safeToSpend'],
    queryFn: async () => {
      const { data } = await apiClient.get<SafeToSpendData>(
        '/api/v1/safe-to-spend',
      );
      return {
        ...data,
        amount: Number(data.amount),
        daily_allowance: Number(data.daily_allowance),
      };
    },
    enabled: !!getToken(),
    refetchInterval: 2 * 60 * 1000, // Re-fetch every 2 minutes
    refetchOnWindowFocus: true,      // Re-fetch when user returns to tab
    staleTime: 60 * 1000,            // Consider stale after 1 minute
  });
}

// =============================================================================
// Transaction Hooks
// =============================================================================

export function useTransactions(params?: {
  search?: string;
  limit?: number;
  offset?: number;
}) {
  const { search, limit = 20, offset = 0 } = params ?? {};

  return useQuery({
    queryKey: ['transactions', search, limit, offset],
    queryFn: async () => {
      const searchParams = new URLSearchParams();
      searchParams.set('limit', String(limit));
      searchParams.set('offset', String(offset));
      if (search) searchParams.set('search', search);

      const { data } = await apiClient.get<PaginatedResponse<TransactionData>>(
        `/api/v1/transactions?${searchParams.toString()}`,
      );
      return {
        ...data,
        data: data.data.map((tx) => ({
          ...tx,
          amount: Number(tx.amount),
        })),
      };
    },
    enabled: !!getToken(),
  });
}

export function useUpdateTransactionCategory() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ id, category }: { id: string; category: string }) => {
      const { data } = await apiClient.patch<TransactionData>(
        `/api/v1/transactions/${id}/category`,
        { category },
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] });
      queryClient.invalidateQueries({ queryKey: ['safeToSpend'] });
    },
  });
}

// =============================================================================
// Analytics Hooks
// =============================================================================

export function useSpendingVelocity() {
  return useQuery({
    queryKey: ['spendingVelocity'],
    queryFn: async () => {
      const { data } = await apiClient.get<SpendingVelocityResponse>(
        '/api/v1/analytics/velocity',
      );
      return {
        weekly: data.weekly.map((point) => ({
          ...point,
          this_month: Number(point.this_month),
          last_month: Number(point.last_month),
        })),
        categories: data.categories.map((item) => ({
          ...item,
          this_month: Number(item.this_month),
          last_month: Number(item.last_month),
        })),
      };
    },
    enabled: !!getToken(),
  });
}

export function useSubscriptions() {
  return useQuery({
    queryKey: ['subscriptions'],
    queryFn: async () => {
      const { data } = await apiClient.get<SubscriptionsResponse>(
        '/api/v1/analytics/subscriptions',
      );
      return {
        subscriptions: data.subscriptions.map((sub) => ({
          ...sub,
          amount: Number(sub.amount),
        })),
        total_monthly_commitment: Number(data.total_monthly_commitment),
      };
    },
    enabled: !!getToken(),
  });
}

// =============================================================================
// Statement Upload Hook
// =============================================================================

export function useUploadStatement() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append('file', file);
      const { data } = await apiClient.post<StatementUploadResponse>(
        '/api/v1/statements/upload',
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        }
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] });
      queryClient.invalidateQueries({ queryKey: ['safeToSpend'] });
    },
  });
}

// =============================================================================
// AI Assistant Hook
// =============================================================================

export function useAIChat() {
  return useMutation({
    mutationFn: async (message: string) => {
      const { data } = await apiClient.post<AIChatResponse>(
        '/api/v1/ai/chat',
        { message },
      );
      return data;
    },
  });
}
