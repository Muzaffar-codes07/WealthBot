'use client';

import { useMemo, useState } from 'react';
import dynamic from 'next/dynamic';
import { MainLayout, Header } from '@/components/layout';
import { AlertTriangle, Loader2, TrendingDown, TrendingUp } from 'lucide-react';
import { useRequireAuth, useSpendingVelocity, useSubscriptions } from '@/hooks';
import { formatCurrency } from '@/lib/utils';
import type { AssistantMessage } from '@/types';

const VelocityChart = dynamic(() => import('@/components/charts/VelocityChart'), { ssr: false });

const initialMessages: AssistantMessage[] = [
  {
    id: '1',
    type: 'alert',
    content: 'Your spending velocity has changed this month. Want me to find where the money went?',
    timestamp: new Date().toISOString(),
    actions: [{ label: 'Show breakdown', variant: 'primary' }],
  },
];

function subscriptionIcon(merchantName: string): string {
  const name = merchantName.toLowerCase();
  if (name.includes('netflix')) return '🎬';
  if (name.includes('spotify')) return '🎵';
  if (name.includes('chatgpt') || name.includes('openai')) return '🤖';
  if (name.includes('apple') || name.includes('icloud')) return '☁️';
  if (name.includes('youtube')) return '📺';
  return '🔁';
}

export default function AnalyticsPage() {
  const { isLoading: authLoading } = useRequireAuth();
  const { data: velocity, isLoading: velocityLoading } = useSpendingVelocity();
  const { data: subscriptionsData, isLoading: subscriptionsLoading } = useSubscriptions();
  const [messages, setMessages] = useState<AssistantMessage[]>(initialMessages);

  const handleSendMessage = (message: string) => {
    const newMessage: AssistantMessage = {
      id: Date.now().toString(),
      type: 'question',
      content: message,
      timestamp: new Date().toISOString(),
    };
    setMessages([...messages, newMessage]);
  };

  const velocityData = useMemo(
    () =>
      (velocity?.weekly ?? []).map((item) => ({
        week: item.week,
        thisMonth: item.this_month,
        lastMonth: item.last_month,
      })),
    [velocity?.weekly]
  );

  const categoryStats = velocity?.categories ?? [];
  const ouchCategory = useMemo(
    () =>
      [...categoryStats]
        .filter((s) => s.this_month > s.last_month && s.category !== 'Income')
        .sort((a, b) => b.this_month - a.this_month)[0],
    [categoryStats]
  );

  const subscriptions = subscriptionsData?.subscriptions ?? [];
  const totalSubs = subscriptionsData?.total_monthly_commitment ?? 0;
  const dueSoonCount = subscriptions.filter((s) => s.next_due_in_days <= 5).length;

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
      assistantPlaceholder="Ask about spending patterns..."
    >
      <Header
        title="Leakage Hunter"
        subtitle="Find where your money silently disappears"
      />

      {/* ------------------------------------------------------------------ */}
      {/* Subscription Radar                                                 */}
      {/* Highlights recurring payments so they don't go unnoticed           */}
      {/* ------------------------------------------------------------------ */}
      <div className="glass-card mb-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-sm font-semibold text-text-primary">
              📡 Subscription Radar
            </h3>
            <p className="text-xs text-text-muted mt-0.5">
              {formatCurrency(totalSubs)}/mo across {subscriptions.length} services
            </p>
          </div>
          <span className="text-xs text-status-warning bg-status-warning/10 px-2 py-1 rounded-full">
            {dueSoonCount} due soon
          </span>
        </div>

        {subscriptionsLoading ? (
          <p className="text-sm text-text-muted py-4">Loading subscriptions...</p>
        ) : subscriptions.length === 0 ? (
          <p className="text-sm text-text-muted py-4">No recurring payments detected yet.</p>
        ) : (
          <div className="space-y-3">
            {subscriptions.map((sub) => {
              const isDueSoon = sub.next_due_in_days <= 5;
              return (
                <div
                  key={`${sub.merchant_name}-${sub.amount}`}
                  className="flex items-center gap-3 p-3 rounded-lg bg-background-secondary border border-border-primary"
                >
                  <span className="text-xl">{subscriptionIcon(sub.merchant_name)}</span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-text-primary">{sub.merchant_name}</p>
                    <p className="text-xs text-text-muted">
                      {formatCurrency(sub.amount)} · {sub.frequency}
                    </p>
                  </div>
                  <span
                    className={`text-xs px-2 py-1 rounded-full font-medium ${
                      isDueSoon
                        ? 'bg-status-warning/15 text-status-warning'
                        : 'bg-background-hover text-text-muted'
                    }`}
                  >
                    Due in {sub.next_due_in_days} day{sub.next_due_in_days === 1 ? '' : 's'}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Spending Velocity — line chart comparing this vs last month        */}
      {/* ------------------------------------------------------------------ */}
      <div className="glass-card mb-6">
        <div className="mb-4">
          <h3 className="text-sm font-semibold text-text-primary">
            ⚡ Spending Velocity
          </h3>
          <p className="text-xs text-text-muted mt-0.5">
            This month vs last month (cumulative weekly spend)
          </p>
        </div>

        <div className="h-48 sm:h-56 md:h-64">
          <VelocityChart data={velocityData} />
        </div>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* The "Ouch" Metric — biggest unnecessary expense                    */}
      {/* ------------------------------------------------------------------ */}
      {ouchCategory && (
        <div className="glass-card border-status-warning/30 mb-6">
          <div className="flex items-start gap-4">
            <div className="p-3 rounded-xl bg-status-warning/10 text-2xl">
              <AlertTriangle className="w-6 h-6 text-status-warning" />
            </div>
            <div className="flex-1">
              <h3 className="text-sm font-semibold text-status-warning mb-1">
                💸 The &quot;Ouch&quot; of the Month
              </h3>
              <p className="text-lg font-bold text-text-primary">
                You spent {formatCurrency(ouchCategory.this_month)} on {ouchCategory.category}
              </p>
              <p className="text-sm text-text-muted mt-1">
                That&apos;s{' '}
                <span className="text-status-warning font-semibold">
                  {formatCurrency(ouchCategory.this_month - ouchCategory.last_month)} more
                </span>{' '}
                than last month ({formatCurrency(ouchCategory.last_month)})
              </p>
            </div>
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* Category Breakdown — spend comparison cards                        */}
      {/* ------------------------------------------------------------------ */}
      <div className="glass-card">
        <h3 className="text-sm font-semibold text-text-primary mb-4">
          Category Breakdown
        </h3>
        {velocityLoading ? (
          <p className="text-sm text-text-muted py-2">Loading spending breakdown...</p>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {categoryStats.map((stat) => {
            const diff = stat.this_month - stat.last_month;
            const isUp = diff > 0;
            return (
              <div
                key={stat.category}
                className="flex items-center gap-3 p-3 rounded-lg bg-background-secondary border border-border-primary"
              >
                <span className="text-xl">{isUp ? '📈' : '📉'}</span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-text-primary">{stat.category}</p>
                  <p className="text-xs text-text-muted">
                    {formatCurrency(stat.this_month)} this month
                  </p>
                </div>
                <div className={`flex items-center gap-1 text-xs font-medium ${isUp ? 'text-status-error' : 'text-semantic-success'}`}>
                  {isUp ? <TrendingUp className="w-3.5 h-3.5" /> : <TrendingDown className="w-3.5 h-3.5" />}
                  {isUp ? '+' : ''}{formatCurrency(Math.abs(diff))}
                </div>
              </div>
            );
          })}
        </div>
        )}
      </div>
    </MainLayout>
  );
}
