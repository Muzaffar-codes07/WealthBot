'use client';

import { useEffect } from 'react';

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    if (process.env.NEXT_PUBLIC_SENTRY_ENABLED === 'true') {
      import('@sentry/react').then((Sentry) => {
        Sentry.captureException(error);
      });
    }
  }, [error]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-background-primary text-text-primary p-6">
      <div className="glass-card max-w-md w-full text-center space-y-4">
        <h1 className="text-2xl font-semibold">Something went wrong</h1>
        <p className="text-sm text-text-secondary">
          We hit an unexpected error. Your data is safe — try again in a moment.
        </p>
        {error.digest && (
          <p className="text-xs text-text-muted font-mono">ref: {error.digest}</p>
        )}
        <div className="flex gap-3 justify-center pt-2">
          <button onClick={reset} className="btn-primary">
            Try again
          </button>
          <a href="/dashboard" className="btn-secondary">
            Go home
          </a>
        </div>
      </div>
    </div>
  );
}
