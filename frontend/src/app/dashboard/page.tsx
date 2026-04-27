'use client';

import { useState } from 'react';
import { MainLayout, Header } from '@/components/layout';
import { RefreshCw, Loader2, TrendingDown, Wallet, Calendar, Zap } from 'lucide-react';
import { useRequireAuth, useSafeToSpend, useTransactions } from '@/hooks';
import { CATEGORY_CONFIG } from '@/constants/data';
import { formatCurrency } from '@/lib/utils';
import type { AssistantMessage, SafeToSpendData } from '@/types';

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
  const words = text.split(' ');
  const noise = new Set(['HYD', 'MUM', 'BLR', 'DEL', 'CHN', 'KOL', 'PUN', 'ORDER', 'BILLING', 'PAYMENT']);
  while (words.length > 1 && noise.has(words[words.length - 1].toUpperCase())) words.pop();
  text = words.join(' ');
  return text.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()).join(' ') || raw;
}

// ---------------------------------------------------------------------------
// Gauge color + risk label helpers
// ---------------------------------------------------------------------------
function getGaugeInfo(riskLevel: string): { color: string; gradientFrom: string; gradientTo: string; label: string; emoji: string } {
  switch (riskLevel) {
    case 'low':
      return { color: '#22c55e', gradientFrom: '#22c55e', gradientTo: '#4ade80', label: 'On Track', emoji: '✅' };
    case 'medium':
      return { color: '#f59e0b', gradientFrom: '#f59e0b', gradientTo: '#fbbf24', label: 'Watch It', emoji: '⚠️' };
    case 'high':
      return { color: '#ef4444', gradientFrom: '#ef4444', gradientTo: '#f87171', label: 'Overspending', emoji: '🔴' };
    default:
      return { color: '#94a3b8', gradientFrom: '#94a3b8', gradientTo: '#cbd5e1', label: 'Unknown', emoji: '❓' };
  }
}

// ---------------------------------------------------------------------------
// Premium Safe-to-Spend Gauge — SVG arc with gradient, tick marks, glow
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
  const { color, gradientFrom, gradientTo, label, emoji } = getGaugeInfo(riskLevel);

  // Dynamic max: round up to nearest nice number for scale
  const rawMax = Math.max(amount * 1.5, 1000);
  const max = Math.ceil(rawMax / 1000) * 1000;
  const ratio = Math.min(Math.max(amount / max, 0), 1);

  // SVG arc math for a 220° arc (more premium than 180°)
  const cx = 150, cy = 140, r = 110;
  const startAngle = 200; // degrees from top
  const endAngle = 340;
  const totalAngle = endAngle - startAngle;

  const polarToCart = (angleDeg: number, radius: number) => {
    const rad = ((angleDeg - 90) * Math.PI) / 180;
    return { x: cx + radius * Math.cos(rad), y: cy + radius * Math.sin(rad) };
  };

  const arcPath = (startA: number, endA: number, radius: number) => {
    const s = polarToCart(startA, radius);
    const e = polarToCart(endA, radius);
    const sweep = endA - startA > 180 ? 1 : 0;
    return `M ${s.x} ${s.y} A ${radius} ${radius} 0 ${sweep} 1 ${e.x} ${e.y}`;
  };

  const filledEnd = startAngle + totalAngle * ratio;

  // Tick marks
  const tickCount = 5;
  const ticks = Array.from({ length: tickCount + 1 }, (_, i) => {
    const frac = i / tickCount;
    const angle = startAngle + totalAngle * frac;
    const inner = polarToCart(angle, r - 6);
    const outer = polarToCart(angle, r + 6);
    const labelPos = polarToCart(angle, r + 18);
    const value = Math.round((max * frac) / 1000);
    return { inner, outer, labelPos, value, angle };
  });

  // Needle endpoint
  const needleEnd = polarToCart(filledEnd, r - 2);

  const formattedDate = new Date(safeUntil + 'T00:00:00').toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
  const displayAmount = Math.round(amount);

  return (
    <div className="flex flex-col items-center w-full">
      <svg viewBox="0 0 300 200" className="w-full max-w-xs sm:max-w-sm" role="img" aria-label={`Safe to spend: ₹${displayAmount.toLocaleString('en-IN')}`}>
        <defs>
          <linearGradient id="gaugeGrad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor={gradientFrom} />
            <stop offset="100%" stopColor={gradientTo} />
          </linearGradient>
          <filter id="glow">
            <feGaussianBlur stdDeviation="4" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          <filter id="softGlow">
            <feGaussianBlur stdDeviation="8" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* Background arc (track) */}
        <path
          d={arcPath(startAngle, endAngle, r)}
          fill="none"
          stroke="#1e293b"
          strokeWidth="14"
          strokeLinecap="round"
        />

        {/* Filled arc with gradient + glow */}
        {ratio > 0.01 && (
          <>
            <path
              d={arcPath(startAngle, filledEnd, r)}
              fill="none"
              stroke={color}
              strokeWidth="14"
              strokeLinecap="round"
              opacity="0.2"
              filter="url(#softGlow)"
              className="transition-all duration-1000 ease-out"
            />
            <path
              d={arcPath(startAngle, filledEnd, r)}
              fill="none"
              stroke="url(#gaugeGrad)"
              strokeWidth="14"
              strokeLinecap="round"
              filter="url(#glow)"
              className="transition-all duration-1000 ease-out"
            />
          </>
        )}

        {/* Tick marks */}
        {ticks.map((t, i) => (
          <g key={i}>
            <line
              x1={t.inner.x} y1={t.inner.y}
              x2={t.outer.x} y2={t.outer.y}
              stroke="#334155"
              strokeWidth="1.5"
              strokeLinecap="round"
            />
            <text
              x={t.labelPos.x} y={t.labelPos.y}
              textAnchor="middle"
              dominantBaseline="middle"
              fill="#64748b"
              fontSize="8"
              fontFamily="system-ui"
            >
              {t.value}K
            </text>
          </g>
        ))}

        {/* Needle dot */}
        {ratio > 0.01 && (
          <circle
            cx={needleEnd.x}
            cy={needleEnd.y}
            r="5"
            fill={color}
            filter="url(#glow)"
            className="transition-all duration-1000 ease-out"
          />
        )}

        {/* Center text */}
        <text
          x={cx} y={cy - 12}
          textAnchor="middle"
          fill="white"
          fontSize="28"
          fontWeight="bold"
          fontFamily="system-ui"
        >
          ₹{displayAmount.toLocaleString('en-IN')}
        </text>
        <text
          x={cx} y={cy + 8}
          textAnchor="middle"
          fill="#94a3b8"
          fontSize="11"
          fontFamily="system-ui"
        >
          Safe to Spend
        </text>
      </svg>

      {/* Info cards below gauge */}
      <div className="grid grid-cols-3 gap-3 w-full mt-2">
        <div className="flex flex-col items-center p-2 rounded-lg bg-background-secondary/50">
          <span className="text-[10px] text-text-muted uppercase tracking-wider mb-0.5">Daily Budget</span>
          <span className="text-sm font-semibold text-text-primary">
            {formatCurrency(Math.round(dailyAllowance))}
          </span>
        </div>
        <div className="flex flex-col items-center p-2 rounded-lg bg-background-secondary/50">
          <span className="text-[10px] text-text-muted uppercase tracking-wider mb-0.5">Status</span>
          <span className="text-sm font-semibold" style={{ color }}>
            {emoji} {label}
          </span>
        </div>
        <div className="flex flex-col items-center p-2 rounded-lg bg-background-secondary/50">
          <span className="text-[10px] text-text-muted uppercase tracking-wider mb-0.5">Days Left</span>
          <span className="text-sm font-semibold text-text-primary">
            {daysLeft}
          </span>
        </div>
      </div>

      {/* Safe until + model badge */}
      <div className="flex items-center gap-3 mt-3">
        <div className="px-3 py-1 rounded-full bg-background-hover/60 border border-white/[0.06] text-xs text-text-secondary flex items-center gap-1.5">
          <Calendar className="w-3 h-3" />
          Safe until <span className="text-semantic-success font-semibold">{formattedDate}</span>
        </div>
        {modelUsed === 'xgboost' && (
          <div className="px-2 py-1 rounded-full bg-brand-primary/10 border border-brand-primary/20 text-[10px] text-brand-primary font-medium flex items-center gap-1">
            <Zap className="w-2.5 h-2.5" /> ML-Powered
          </div>
        )}
      </div>
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
    <div className="flex flex-col items-center py-6 w-full">
      <div className="w-64 h-36 rounded-xl bg-background-hover animate-pulse" />
      <div className="grid grid-cols-3 gap-3 w-full mt-4">
        {[1, 2, 3].map(i => <div key={i} className="h-14 rounded-lg bg-background-hover animate-pulse" />)}
      </div>
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
  const { data: txPage, isLoading: txLoading } = useTransactions({ limit: 5 });
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
      <div className="glass-card flex flex-col items-center py-6 mb-6 relative overflow-hidden">
        {stsLoading ? (
          <SkeletonGauge />
        ) : stsError || !safeToSpend ? (
          <GaugeError onRetry={() => refetchSTS()} />
        ) : (
          <>
            <div
              className="absolute inset-0 opacity-10 pointer-events-none"
              style={{
                background: `radial-gradient(circle at 50% 60%, ${getGaugeInfo(safeToSpend.risk_level).color}40 0%, transparent 60%)`,
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
              className="mt-3 flex items-center gap-1.5 text-xs text-text-muted hover:text-brand-primary transition-colors"
            >
              <RefreshCw className="w-3.5 h-3.5" /> Recalculate
            </button>
          </>
        )}
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Recommendations (from ML/heuristic)                                */}
      {/* ------------------------------------------------------------------ */}
      {safeToSpend?.recommendations && safeToSpend.recommendations.length > 0 && (
        <div className="glass-card mb-6 p-4">
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

      {/* ------------------------------------------------------------------ */}
      {/* Recent Activity — last 5 transactions                              */}
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
          <div className="space-y-1">
            {recentTransactions.map((tx) => {
              const config = CATEGORY_CONFIG[tx.category] || CATEGORY_CONFIG.Other;
              return (
                <div
                  key={tx.id}
                  className="flex items-center justify-between py-2.5 px-2 -mx-2 rounded-lg hover:bg-background-hover/50 transition-colors border-b border-border-primary/50 last:border-0"
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
                  <span
                    className={`text-sm font-semibold shrink-0 ml-3 ${
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
