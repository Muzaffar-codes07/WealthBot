'use client';

import { useState } from 'react';
import { MainLayout, Header } from '@/components/layout';
import { RefreshCw, Loader2, TrendingDown, Wallet, Calendar, Zap } from 'lucide-react';
import { useRequireAuth, useSafeToSpend, useTransactions } from '@/hooks';
import { CATEGORY_CONFIG } from '@/constants/data';
import { formatCurrency } from '@/lib/utils';
import type { AssistantMessage } from '@/types';

/**
 * Clean up raw bank narrations for display when merchant_name is missing.
 */
function cleanMerchantDisplay(raw: string): string {
  let text = raw
    .replace(/^(?:UPI|IMPS|NEFT|RTGS|POS|ATM|ECS|NACH)[-/]/i, '')
    .replace(/\d{10,}/g, '')
    .replace(/[a-zA-Z0-9._%+-]+@[a-z]+/gi, '')
    .replace(/[-*_]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
  const words = text.split(' ');
  const noise = new Set(['HYD', 'MUM', 'BLR', 'DEL', 'CHN', 'KOL', 'PUN', 'ORDER', 'BILLING', 'PAYMENT']);
  while (words.length > 1 && noise.has(words[words.length - 1].toUpperCase())) words.pop();
  text = words.join(' ');
  return text.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()).join(' ') || raw;
}

// ---------------------------------------------------------------------------
// Risk-level colors
// ---------------------------------------------------------------------------
function getGaugeTheme(riskLevel: string) {
  switch (riskLevel) {
    case 'low':    return { color: '#22c55e', bg: '#22c55e20', label: 'On Track', emoji: '✅' };
    case 'medium': return { color: '#f59e0b', bg: '#f59e0b20', label: 'Watch It', emoji: '⚠️' };
    case 'high':   return { color: '#ef4444', bg: '#ef444420', label: 'Overspending', emoji: '🔴' };
    default:       return { color: '#94a3b8', bg: '#94a3b820', label: 'Unknown', emoji: '❓' };
  }
}

// ---------------------------------------------------------------------------
// Safe-to-Spend Gauge — simple proven semi-circle with dashoffset
// Uses a single <path> semi-circle from left to right, filled via dashoffset.
// No complex trig — just a clean, reliable SVG arc.
// ---------------------------------------------------------------------------
function SafeToSpendGauge({
  amount,
  dailyAllowance,
  riskLevel,
  daysLeft,
  safeUntil,
  modelUsed,
}: {
  amount: number;
  dailyAllowance: number;
  riskLevel: string;
  daysLeft: number;
  safeUntil: string;
  modelUsed: string;
}) {
  const theme = getGaugeTheme(riskLevel);
  const displayAmount = Math.round(amount);

  // Dynamic max scale
  const rawMax = Math.max(amount * 1.4, 1000);
  const max = Math.ceil(rawMax / 1000) * 1000;
  const ratio = Math.min(Math.max(amount / max, 0), 1);

  // Arc geometry: semicircle from (30, 140) to (270, 140) with radius 120
  // The arc path is: M 30 140 A 120 120 0 0 1 270 140
  // Half-circumference = π × 120 ≈ 376.99
  const radius = 120;
  const circumference = Math.PI * radius;
  const dashOffset = circumference * (1 - ratio);

  const formattedDate = (() => {
    try {
      return new Date(safeUntil + 'T00:00:00').toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
    } catch { return safeUntil; }
  })();

  // Format max for display (e.g., 12000 → "12K")
  const maxLabel = max >= 1000 ? `${(max / 1000).toFixed(0)}K` : `${max}`;
  const midLabel = max >= 1000 ? `${(max / 2000).toFixed(0)}K` : `${max / 2}`;

  return (
    <div className="flex flex-col items-center w-full">
      {/* SVG Gauge */}
      <div className="relative w-full max-w-[320px] sm:max-w-[360px]">
        <svg
          viewBox="0 0 300 170"
          className="w-full"
          role="img"
          aria-label={`Safe to spend: ₹${displayAmount.toLocaleString('en-IN')}`}
        >
          <defs>
            <linearGradient id="gaugeGradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor={theme.color} stopOpacity="0.4" />
              <stop offset="50%" stopColor={theme.color} stopOpacity="0.8" />
              <stop offset="100%" stopColor={theme.color} />
            </linearGradient>
            <filter id="gaugeGlow" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {/* Background track */}
          <path
            d="M 30 140 A 120 120 0 0 1 270 140"
            fill="none"
            stroke="#1e293b"
            strokeWidth="20"
            strokeLinecap="round"
          />

          {/* Filled arc */}
          <path
            d="M 30 140 A 120 120 0 0 1 270 140"
            fill="none"
            stroke="url(#gaugeGradient)"
            strokeWidth="20"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={dashOffset}
            filter="url(#gaugeGlow)"
            style={{ transition: 'stroke-dashoffset 1s ease-out' }}
          />

          {/* Scale labels */}
          <text x="25" y="160" textAnchor="middle" fill="#475569" fontSize="10" fontFamily="system-ui">0</text>
          <text x="150" y="12" textAnchor="middle" fill="#475569" fontSize="10" fontFamily="system-ui">{midLabel}</text>
          <text x="275" y="160" textAnchor="middle" fill="#475569" fontSize="10" fontFamily="system-ui">{maxLabel}</text>

          {/* Small tick marks at 0%, 25%, 50%, 75%, 100% */}
          {[0, 0.25, 0.5, 0.75, 1].map((frac, i) => {
            const angle = Math.PI * (1 - frac); // 180° to 0°
            const ix = 150 + (radius - 14) * Math.cos(angle);
            const iy = 140 - (radius - 14) * Math.sin(angle);
            const ox = 150 + (radius + 2) * Math.cos(angle);
            const oy = 140 - (radius + 2) * Math.sin(angle);
            return (
              <line
                key={i}
                x1={ix} y1={iy} x2={ox} y2={oy}
                stroke="#334155"
                strokeWidth="2"
                strokeLinecap="round"
              />
            );
          })}

          {/* Center amount text */}
          <text
            x="150" y="110"
            textAnchor="middle"
            fill="white"
            fontSize="36"
            fontWeight="700"
            fontFamily="system-ui"
          >
            ₹{displayAmount.toLocaleString('en-IN')}
          </text>
          <text
            x="150" y="132"
            textAnchor="middle"
            fill="#94a3b8"
            fontSize="13"
            fontFamily="system-ui"
          >
            Safe to Spend
          </text>
        </svg>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-3 w-full mt-2 px-1">
        <div className="text-center py-2.5 px-2 rounded-xl bg-white/[0.03] border border-white/[0.05]">
          <p className="text-[10px] uppercase tracking-widest text-text-muted mb-1">Daily Budget</p>
          <p className="text-sm font-bold text-text-primary">{formatCurrency(Math.round(dailyAllowance))}</p>
        </div>
        <div className="text-center py-2.5 px-2 rounded-xl bg-white/[0.03] border border-white/[0.05]">
          <p className="text-[10px] uppercase tracking-widest text-text-muted mb-1">Status</p>
          <p className="text-sm font-bold" style={{ color: theme.color }}>{theme.emoji} {theme.label}</p>
        </div>
        <div className="text-center py-2.5 px-2 rounded-xl bg-white/[0.03] border border-white/[0.05]">
          <p className="text-[10px] uppercase tracking-widest text-text-muted mb-1">Days Left</p>
          <p className="text-sm font-bold text-text-primary">{daysLeft}</p>
        </div>
      </div>

      {/* Badges */}
      <div className="flex flex-wrap items-center justify-center gap-2 mt-3">
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/[0.04] border border-white/[0.06] text-xs text-text-secondary">
          <Calendar className="w-3 h-3" />
          Safe until <span className="text-semantic-success font-semibold">{formattedDate}</span>
        </span>
        {modelUsed === 'xgboost' && (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-brand-primary/10 border border-brand-primary/20 text-[10px] text-brand-primary font-semibold">
            <Zap className="w-2.5 h-2.5" /> ML-Powered
          </span>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Skeleton + error states
// ---------------------------------------------------------------------------
function SkeletonGauge() {
  return (
    <div className="flex flex-col items-center py-8 w-full">
      <div className="w-72 h-36 rounded-2xl bg-background-hover animate-pulse" />
      <div className="grid grid-cols-3 gap-3 w-full mt-4">
        {[1, 2, 3].map(i => <div key={i} className="h-16 rounded-xl bg-background-hover animate-pulse" />)}
      </div>
    </div>
  );
}

function GaugeError({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="flex flex-col items-center py-12 text-center">
      <p className="text-sm text-text-secondary mb-3">Couldn&apos;t fetch your Safe-to-Spend right now.</p>
      <button onClick={onRetry} className="flex items-center gap-1.5 text-sm text-brand-primary hover:underline">
        <RefreshCw className="w-3.5 h-3.5" /> Retry
      </button>
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
              <div className="w-28 h-4 rounded bg-background-hover animate-pulse" />
              <div className="w-16 h-3 mt-1 rounded bg-background-hover animate-pulse" />
            </div>
          </div>
          <div className="w-16 h-4 rounded bg-background-hover animate-pulse" />
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Dashboard Page
// ---------------------------------------------------------------------------
const initialMessages: AssistantMessage[] = [
  {
    id: '1',
    type: 'suggestion',
    content: 'Your spending velocity is 12% higher than last week. Consider skipping Swiggy today — you can save ₹200!',
    timestamp: new Date().toISOString(),
    actions: [{ label: 'Show me alternatives', variant: 'primary' }],
  },
];

export default function DashboardPage() {
  const { user, isLoading: authLoading } = useRequireAuth();
  const { data: safeToSpend, isLoading: stsLoading, isError: stsError, refetch: refetchSTS } = useSafeToSpend();
  const { data: txPage, isLoading: txLoading } = useTransactions({ limit: 5 });
  const [messages, setMessages] = useState<AssistantMessage[]>(initialMessages);

  const recentTransactions = txPage?.data ?? [];
  const firstName = user?.first_name ?? 'there';

  const handleSendMessage = (message: string) => {
    setMessages([...messages, {
      id: Date.now().toString(),
      type: 'question',
      content: message,
      timestamp: new Date().toISOString(),
    }]);
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

      {/* ── Hero: Safe-to-Spend Gauge ──────────────────────────────────── */}
      <div className="glass-card flex flex-col items-center py-8 mb-6 relative overflow-hidden">
        {stsLoading ? (
          <SkeletonGauge />
        ) : stsError || !safeToSpend ? (
          <GaugeError onRetry={() => refetchSTS()} />
        ) : (
          <>
            {/* Background radial glow */}
            <div
              className="absolute inset-0 opacity-[0.07] pointer-events-none"
              style={{
                background: `radial-gradient(ellipse 60% 50% at 50% 40%, ${getGaugeTheme(safeToSpend.risk_level).color} 0%, transparent 70%)`,
              }}
            />

            <SafeToSpendGauge
              amount={safeToSpend.amount}
              dailyAllowance={safeToSpend.daily_allowance}
              riskLevel={safeToSpend.risk_level}
              daysLeft={safeToSpend.days_until_payday}
              safeUntil={safeToSpend.safe_until}
              modelUsed={safeToSpend.model_used}
            />

            <button
              onClick={() => refetchSTS()}
              className="mt-4 flex items-center gap-1.5 text-xs text-text-muted hover:text-brand-primary transition-colors"
            >
              <RefreshCw className="w-3.5 h-3.5" /> Recalculate
            </button>
          </>
        )}
      </div>

      {/* ── Smart Insights ─────────────────────────────────────────────── */}
      {safeToSpend?.recommendations && safeToSpend.recommendations.length > 0 && (
        <div className="glass-card mb-6">
          <div className="flex items-center gap-2 mb-3">
            <TrendingDown className="w-4 h-4 text-brand-primary" />
            <h3 className="text-sm font-semibold text-text-primary">Smart Insights</h3>
          </div>
          <div className="space-y-2">
            {safeToSpend.recommendations.map((tip, i) => (
              <p key={i} className="text-xs text-text-secondary flex items-start gap-2">
                <Wallet className="w-3 h-3 mt-0.5 text-text-muted shrink-0" />
                {tip}
              </p>
            ))}
          </div>
        </div>
      )}

      {/* ── Recent Activity ────────────────────────────────────────────── */}
      <div className="glass-card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-medium text-text-secondary">Recent Activity</h3>
          <a href="/transactions" className="text-xs text-brand-primary hover:underline">View All →</a>
        </div>
        {txLoading ? (
          <SkeletonTransactions />
        ) : recentTransactions.length === 0 ? (
          <p className="text-sm text-text-muted text-center py-6">No transactions yet.</p>
        ) : (
          <div className="space-y-1">
            {recentTransactions.map((tx) => {
              const config = CATEGORY_CONFIG[tx.category] || CATEGORY_CONFIG.Other;
              return (
                <div
                  key={tx.id}
                  className="flex items-center justify-between py-2.5 px-2 -mx-2 rounded-lg hover:bg-background-hover/50 transition-colors border-b border-border-primary/30 last:border-0"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <span
                      className="w-9 h-9 rounded-full flex items-center justify-center text-sm shrink-0"
                      style={{ backgroundColor: `${config.color}20` }}
                    >
                      {config.icon}
                    </span>
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-text-primary truncate">
                        {tx.merchant_name || cleanMerchantDisplay(tx.description ?? 'Unknown')}
                      </p>
                      <p className="text-xs text-text-muted">{tx.category}</p>
                    </div>
                  </div>
                  <span className={`text-sm font-semibold shrink-0 ml-3 ${
                    tx.transaction_type === 'income' ? 'text-semantic-success' : 'text-text-primary'
                  }`}>
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
