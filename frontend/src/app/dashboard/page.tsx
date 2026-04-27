'use client';

import { useState } from 'react';
import { MainLayout, Header } from '@/components/layout';
import { RefreshCw, Loader2 } from 'lucide-react';
import { useRequireAuth, useSafeToSpend, useTransactions } from '@/hooks';
import { CATEGORY_CONFIG } from '@/constants/data';
import { formatCurrency, getGaugeColor } from '@/lib/utils';
import type { AssistantMessage } from '@/types';

/**
 * Clean up raw bank narrations for display when merchant_name is missing.
 * UPI-STARBUCKS-COFFEE-JUBILEE → Starbucks Coffee
 */
function cleanMerchantDisplay(raw: string): string {
  let text = raw
    .replace(/^(?:UPI|IMPS|NEFT|RTGS|POS|ATM|ECS|NACH)[-/]/i, '')
    .replace(/\d{10,}/g, '')
    .replace(/[a-zA-Z0-9._%+-]+@[a-z]+/gi, '')
    .replace(/[-*_]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
  // Strip trailing city codes / noise words
  const words = text.split(' ');
  const noise = new Set(['HYD', 'MUM', 'BLR', 'DEL', 'CHN', 'KOL', 'PUN', 'ORDER', 'BILLING', 'PAYMENT']);
  while (words.length > 1 && noise.has(words[words.length - 1].toUpperCase())) words.pop();
  text = words.join(' ');
  return text.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()).join(' ') || raw;
}

// ---------------------------------------------------------------------------
// Safe-to-Spend Gauge — semi-circular SVG speedometer
// Color scales: Red (<₹200) → Yellow → Green (>₹800)
// ---------------------------------------------------------------------------
function SafeToSpendGauge({ amount, max = 2000 }: { amount: number; max?: number }) {
  const ratio = Math.min(amount / max, 1);
  const color = getGaugeColor(amount);

  // SVG arc math for a 180° semicircle
  const radius = 100;
  const circumference = Math.PI * radius; // half-circle
  const offset = circumference * (1 - ratio);

  return (
    <div className="flex flex-col items-center">
      <svg
        viewBox="0 0 240 140"
        className="w-56 sm:w-72 h-32 sm:h-40"
        role="img"
        aria-label={`Safe to spend today: ${formatCurrency(amount)}`}
      >
        {/* Track */}
        <path
          d="M 20 130 A 100 100 0 0 1 220 130"
          fill="none"
          stroke="#1e293b"
          strokeWidth="18"
          strokeLinecap="round"
        />
        {/* Filled arc */}
        <path
          d="M 20 130 A 100 100 0 0 1 220 130"
          fill="none"
          stroke={color}
          strokeWidth="18"
          strokeLinecap="round"
          strokeDasharray={`${circumference}`}
          strokeDashoffset={`${offset}`}
          className="transition-all duration-700 ease-out"
          style={{ filter: `drop-shadow(0 0 8px ${color}40)` }}
        />
        {/* Center amount */}
        <text x="120" y="105" textAnchor="middle" className="fill-white text-4xl font-bold" fontSize="36" aria-hidden="true">
          ₹{amount.toLocaleString('en-IN')}
        </text>
        <text x="120" y="128" textAnchor="middle" className="fill-slate-400 text-sm" fontSize="13" aria-hidden="true">
          Safe to Spend
        </text>
      </svg>
    </div>
  );
}

function GaugeError({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="flex flex-col items-center py-10 text-center">
      <p className="text-sm text-text-secondary mb-3">
        Couldn&apos;t fetch your Safe-to-Spend right now.
      </p>
      <button
        onClick={onRetry}
        className="flex items-center gap-1.5 text-sm text-brand-primary hover:underline"
      >
        <RefreshCw className="w-3.5 h-3.5" /> Retry
      </button>
    </div>
  );
}

function SkeletonGauge() {
  return (
    <div className="flex flex-col items-center py-10">
      <div className="w-72 h-40 rounded-xl bg-background-hover animate-pulse" />
      <div className="mt-4 w-40 h-6 rounded-full bg-background-hover animate-pulse" />
    </div>
  );
}

function SkeletonTransactions() {
  return (
    <div className="space-y-3">
      {[1, 2, 3].map((i) => (
        <div key={i} className="flex items-center justify-between py-2">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-full bg-background-hover animate-pulse" />
            <div>
              <div className="w-24 h-4 rounded bg-background-hover animate-pulse" />
              <div className="w-16 h-3 mt-1 rounded bg-background-hover animate-pulse" />
            </div>
          </div>
          <div className="w-16 h-4 rounded bg-background-hover animate-pulse" />
        </div>
      ))}
    </div>
  );
}

const initialMessages: AssistantMessage[] = [
  {
    id: '1',
    type: 'suggestion',
    content: 'Your spending velocity is 12% higher than last week. Consider skipping Swiggy today — you can save ₹200!',
    timestamp: new Date().toISOString(),
    actions: [
      { label: 'Show me alternatives', variant: 'primary' },
    ],
  },
];

export default function DashboardPage() {
  const { user, isLoading: authLoading } = useRequireAuth();
  const { data: safeToSpend, isLoading: stsLoading, isError: stsError, refetch: refetchSTS } = useSafeToSpend();
  const { data: txPage, isLoading: txLoading } = useTransactions({ limit: 3 });
  const [messages, setMessages] = useState<AssistantMessage[]>(initialMessages);

  const recentTransactions = txPage?.data ?? [];
  const firstName = user?.first_name ?? 'there';

  const handleSendMessage = (message: string) => {
    const newMessage: AssistantMessage = {
      id: Date.now().toString(),
      type: 'question',
      content: message,
      timestamp: new Date().toISOString(),
    };
    setMessages([...messages, newMessage]);
  };

  if (authLoading) {
    return (
      <MainLayout>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-brand-primary" />
        </div>
      </MainLayout>
    );
  }

  return (
    <MainLayout
      assistantMessages={messages}
      onAssistantMessage={handleSendMessage}
      assistantPlaceholder="Ask WealthBot anything..."
    >
      <Header
        title={`Hey ${firstName} 👋`}
        subtitle="Here's your spending pulse for today."
      />

      {/* ------------------------------------------------------------------ */}
      {/* Hero: Safe-to-Spend Gauge                                          */}
      {/* ------------------------------------------------------------------ */}
      <div className="glass-card flex flex-col items-center py-10 mb-6 relative overflow-hidden">
        {stsLoading ? (
          <SkeletonGauge />
        ) : stsError || !safeToSpend ? (
          <GaugeError onRetry={() => refetchSTS()} />
        ) : (
          <>
            <div
              className="absolute inset-0 opacity-10 pointer-events-none"
              style={{
                background: `radial-gradient(circle at 50% 80%, ${getGaugeColor(safeToSpend.amount)}40 0%, transparent 60%)`,
              }}
            />

            <SafeToSpendGauge amount={safeToSpend.amount} />

            <div className="mt-4 px-4 py-1.5 rounded-full bg-background-hover/60 border border-white/[0.06] text-sm text-text-secondary">
              Safe until <span className="text-semantic-success font-semibold">{new Date(safeToSpend.safe_until + 'T00:00:00').toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })}</span>
            </div>

            <button
              onClick={() => refetchSTS()}
              className="mt-3 flex items-center gap-1.5 text-xs text-text-muted hover:text-brand-primary transition-colors"
            >
              <RefreshCw className="w-3.5 h-3.5" /> Recalculate
            </button>
          </>
        )}
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Recent Activity — last 3 transactions                              */}
      {/* ------------------------------------------------------------------ */}
      <div className="glass-card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-medium text-text-secondary">Recent Activity</h3>
          <a href="/transactions" className="text-xs text-brand-primary hover:underline">
            View All →
          </a>
        </div>
        {txLoading ? (
          <SkeletonTransactions />
        ) : recentTransactions.length === 0 ? (
          <p className="text-sm text-text-muted text-center py-6">No transactions yet.</p>
        ) : (
          <div className="space-y-3">
            {recentTransactions.map((tx) => {
              const config = CATEGORY_CONFIG[tx.category] || CATEGORY_CONFIG.Other;
              return (
                <div
                  key={tx.id}
                  className="flex items-center justify-between py-2 border-b border-border-primary last:border-0"
                >
                  <div className="flex items-center gap-3">
                    <span
                      className="w-9 h-9 rounded-full flex items-center justify-center text-sm"
                      style={{ backgroundColor: `${config.color}20` }}
                    >
                      {config.icon}
                    </span>
                    <div>
                      <p className="text-sm font-medium text-text-primary">{tx.merchant_name || cleanMerchantDisplay(tx.description ?? 'Unknown')}</p>
                      <p className="text-xs text-text-muted">{tx.category}</p>
                    </div>
                  </div>
                  <span
                    className={`text-sm font-semibold ${
                      tx.transaction_type === 'income' ? 'text-semantic-success' : 'text-text-primary'
                    }`}
                  >
                    {tx.transaction_type === 'income' ? '+' : '-'}
                    {formatCurrency(tx.amount)}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </MainLayout>
  );
}
