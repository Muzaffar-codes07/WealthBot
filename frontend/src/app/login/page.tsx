'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Eye, EyeOff, Loader2 } from 'lucide-react';
import { useLogin, useRegister } from '@/hooks/useApi';

type Mode = 'login' | 'register';

export default function LoginPage() {
  const router = useRouter();
  const loginMutation = useLogin();
  const registerMutation = useRegister();

  const [mode, setMode] = useState<Mode>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isLoading = loginMutation.isPending || registerMutation.isPending;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (mode === 'register') {
      registerMutation.mutate(
        { email, password, first_name: firstName || undefined, last_name: lastName || undefined },
        {
          onSuccess: () => {
            loginMutation.mutate(
              { email, password },
              {
              onSuccess: () => {
                const token = localStorage.getItem('auth_token');
                if (!token) {
                  setMode('login');
                  setError('Account created! Please log in.');
                  return;
                }
                router.push('/dashboard');
              },
                onError: () => {
                  setMode('login');
                  setError('Account created! Please log in.');
                },
              },
            );
          },
          onError: (err) => {
            const msg =
              (err as { response?: { data?: { detail?: string } } }).response?.data
                ?.detail ?? 'Registration failed. Please try again.';
            setError(msg);
          },
        },
      );
    } else {
      loginMutation.mutate(
        { email, password },
        {
          onSuccess: () => {
            // Verify token was actually stored (catches silent CORS / network failures)
            const token = localStorage.getItem('auth_token');
            if (!token) {
              setError('Login succeeded but session could not be established. Please try again.');
              return;
            }
            router.push('/dashboard');
          },
          onError: (err) => {
            const msg =
              (err as { response?: { data?: { detail?: string } } }).response?.data
                ?.detail ?? 'Invalid email or password.';
            setError(msg);
          },
        },
      );
    }
  };

  return (
    <div className="min-h-screen bg-background-primary flex items-center justify-center px-4 relative overflow-hidden">
      {/* Ambient background glow */}
      <div className="absolute inset-0 bg-gradient-hero pointer-events-none" />

      <div className="w-full max-w-md relative z-10">
        {/* Logo */}
        <div className="flex flex-col items-center mb-8 relative">
          <div className="absolute -top-8 w-32 h-32 rounded-full glow-orange opacity-50 pointer-events-none" />
          <div className="w-12 h-12 rounded-full bg-brand-primary flex items-center justify-center mb-3 relative">
            <span className="text-white font-bold text-xl">W</span>
          </div>
          <h1 className="text-2xl font-bold text-text-primary">WealthBot</h1>
          <p className="text-sm text-text-muted mt-1">
            {mode === 'login' ? 'Sign in to your account' : 'Create your account'}
          </p>
        </div>

        {/* Form card */}
        <div className="glass-card">
          <form onSubmit={handleSubmit} className="space-y-4">
            {mode === 'register' && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label htmlFor="firstName" className="block text-xs font-medium text-text-secondary mb-1">
                    First Name
                  </label>
                  <input
                    id="firstName"
                    type="text"
                    value={firstName}
                    onChange={(e) => setFirstName(e.target.value)}
                    className="input w-full"
                    placeholder="Rahul"
                  />
                </div>
                <div>
                  <label htmlFor="lastName" className="block text-xs font-medium text-text-secondary mb-1">
                    Last Name
                  </label>
                  <input
                    id="lastName"
                    type="text"
                    value={lastName}
                    onChange={(e) => setLastName(e.target.value)}
                    className="input w-full"
                    placeholder="Sharma"
                  />
                </div>
              </div>
            )}

            <div>
              <label htmlFor="email" className="block text-xs font-medium text-text-secondary mb-1">
                Email
              </label>
              <input
                id="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="input w-full"
                placeholder="you@example.com"
                autoComplete="email"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-xs font-medium text-text-secondary mb-1">
                Password
              </label>
              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  required
                  minLength={8}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="input w-full pr-10"
                  placeholder="Min 8 characters"
                  autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-secondary transition-colors"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {error && (
              <div className="text-sm text-status-error bg-status-error/10 px-3 py-2 rounded-lg">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={isLoading}
              className="btn-primary w-full flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading && <Loader2 className="w-4 h-4 animate-spin" />}
              {mode === 'login' ? 'Sign In' : 'Create Account'}
            </button>
          </form>

          {/* Mode toggle */}
          <div className="mt-6 text-center text-sm text-text-muted">
            {mode === 'login' ? (
              <>
                Don&apos;t have an account?{' '}
                <button
                  onClick={() => { setMode('register'); setError(null); }}
                  className="text-brand-primary hover:underline font-medium"
                >
                  Sign Up
                </button>
              </>
            ) : (
              <>
                Already have an account?{' '}
                <button
                  onClick={() => { setMode('login'); setError(null); }}
                  className="text-brand-primary hover:underline font-medium"
                >
                  Sign In
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
