'use client';

import { useState, useMemo, useEffect } from 'react';
import { MainLayout, Header } from '@/components/layout';
import { Search, Pencil, Check, ChevronLeft, ChevronRight, Loader2 } from 'lucide-react';
import { useRequireAuth, useTransactions, useUpdateTransactionCategory } from '@/hooks';
import { useUserStore } from '@/stores/userStore';
import { CATEGORY_CONFIG } from '@/constants/data';
import { formatCurrency } from '@/lib/utils';
import type { AssistantMessage } from '@/types';

const PAGE_SIZE = 20;

const initialMessages: AssistantMessage[] = [
  {
    id: '1',
    type: 'info',
    content: 'Tip: Tap the pencil icon to correct a category if the AI got it wrong — this helps improve predictions!',
    timestamp: new Date().toISOString(),
  },
];

export default function TransactionsPage() {
  const { isLoading: authLoading } = useRequireAuth();
  const { devMode } = useUserStore();
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [offset, setOffset] = useState(0);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [messages, setMessages] = useState<AssistantMessage[]>(initialMessages);

  const { data: txPage, isLoading: txLoading } = useTransactions({
    search: debouncedSearch || undefined,
    limit: PAGE_SIZE,
    offset,
  });
  const updateCategory = useUpdateTransactionCategory();

  const totalPages = txPage?.total_pages ?? 1;
  const currentPage = txPage?.page ?? 1;

  // Debounce search input
  useEffect(() => {
    const id = setTimeout(() => setDebouncedSearch(searchQuery), 300);
    return () => clearTimeout(id);
  }, [searchQuery]);

  const handleSearchChange = (value: string) => {
    setSearchQuery(value);
    setOffset(0);
  };

  // Group transactions by date for display
  const grouped = useMemo(() => {
    const txns = txPage?.data ?? [];
    if (!txns.length) return [];

    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(today.getTime() - 86400000);
    const weekAgo = new Date(today.getTime() - 7 * 86400000);

    const groups: Record<string, typeof txns> = {
      Today: [],
      Yesterday: [],
      'This Week': [],
      Older: [],
    };

    for (const tx of txns) {
      const d = new Date(tx.transaction_date);
      const day = new Date(d.getFullYear(), d.getMonth(), d.getDate());

      if (day.getTime() >= today.getTime()) groups['Today'].push(tx);
      else if (day.getTime() >= yesterday.getTime()) groups['Yesterday'].push(tx);
      else if (day.getTime() >= weekAgo.getTime()) groups['This Week'].push(tx);
      else groups['Older'].push(tx);
    }

    return Object.entries(groups)
      .filter(([, items]) => items.length > 0)
      .map(([label, items]) => ({ label, items }));
  }, [txPage?.data]);

  const categoryKeys = Object.keys(CATEGORY_CONFIG);

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
      assistantPlaceholder="Search 'Swiggy' or ask about spending..."
    >
      <Header title="Transactions" subtitle="Smart-grouped & AI-categorized" />

      {/* ------------------------------------------------------------------ */}
      {/* Search Bar                                                         */}
      {/* ------------------------------------------------------------------ */}
      <div className="relative mb-6">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted" />
        <input
          type="text"
          placeholder="Search 'Swiggy' or 'Last Week'..."
          value={searchQuery}
          onChange={(e) => handleSearchChange(e.target.value)}
          className="w-full pl-12 pr-4 py-3 bg-background-card border border-border-primary rounded-xl text-text-primary placeholder-text-muted focus:outline-none focus:border-accent-green transition-colors"
        />
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Loading state                                                      */}
      {/* ------------------------------------------------------------------ */}
      {txLoading && (
        <div className="space-y-4">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="flex items-center gap-3 px-4 py-3">
              <div className="w-10 h-10 rounded-full bg-background-hover animate-pulse shrink-0" />
              <div className="flex-1 space-y-2">
                <div className="w-32 h-4 rounded bg-background-hover animate-pulse" />
                <div className="w-20 h-3 rounded bg-background-hover animate-pulse" />
              </div>
              <div className="w-16 h-4 rounded bg-background-hover animate-pulse" />
            </div>
          ))}
        </div>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* Empty state                                                        */}
      {/* ------------------------------------------------------------------ */}
      {!txLoading && grouped.length === 0 && (
        <div className="glass-card text-center py-12 text-text-muted">
          {debouncedSearch ? 'No transactions match your search.' : 'No transactions yet.'}
        </div>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* Grouped Transaction List                                           */}
      {/* ------------------------------------------------------------------ */}
      {!txLoading &&
        grouped.map((group) => (
          <div key={group.label} className="mb-6">
            <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-3 px-1">
              {group.label}
            </h3>

            <div className="glass-card p-0 divide-y divide-border-primary overflow-hidden">
              {group.items.map((tx) => {
                const config = CATEGORY_CONFIG[tx.category] || CATEGORY_CONFIG.Other;
                const isEditing = editingId === tx.id;

                return (
                  <div
                    key={tx.id}
                    className="flex items-center gap-3 px-4 py-3 hover:bg-background-hover transition-colors"
                  >
                    {/* Category icon */}
                    <span
                      className="w-10 h-10 rounded-full flex items-center justify-center text-base shrink-0"
                      style={{ backgroundColor: `${config.color}20` }}
                    >
                      {config.icon}
                    </span>

                    {/* Merchant + meta */}
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-text-primary truncate">
                        {tx.merchant_name ?? tx.description ?? 'Unknown'}
                      </p>
                      <div className="flex items-center gap-2 mt-0.5">
                        {isEditing ? (
                          <div className="flex gap-1 flex-wrap">
                            {categoryKeys.map((cat) => (
                              <button
                                key={cat}
                                onClick={() => {
                                  updateCategory.mutate({ id: tx.id, category: cat });
                                  setEditingId(null);
                                }}
                                className="px-2 py-0.5 text-[10px] rounded-full border border-border-secondary text-text-secondary hover:bg-brand-primary/20 hover:text-brand-primary transition-colors"
                              >
                                #{cat}
                              </button>
                            ))}
                            <button
                              onClick={() => setEditingId(null)}
                              className="px-1.5 py-0.5 text-[10px] text-text-muted"
                            >
                              <Check className="w-3 h-3" />
                            </button>
                          </div>
                        ) : (
                          <span
                            className="px-2 py-0.5 text-[10px] rounded-full font-medium"
                            style={{
                              backgroundColor: `${config.color}20`,
                              color: config.color,
                            }}
                          >
                            #{tx.category}
                          </span>
                        )}

                        {/* ML confidence badge (dev mode only) */}
                        {devMode && tx.category_confidence != null && (
                          <span className="text-[10px] text-text-muted bg-background-secondary px-1.5 py-0.5 rounded">
                            {(tx.category_confidence * 100).toFixed(0)}% conf
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Amount */}
                    <span
                      className={`text-sm font-semibold shrink-0 ${
                        tx.transaction_type === 'credit' ? 'text-semantic-success' : 'text-text-primary'
                      }`}
                    >
                      {tx.transaction_type === 'credit' ? '+' : '-'}
                      {formatCurrency(tx.amount)}
                    </span>

                    {/* Edit pencil */}
                    <button
                      onClick={() => setEditingId(isEditing ? null : tx.id)}
                      className="p-2.5 min-h-[44px] min-w-[44px] flex items-center justify-center rounded-lg hover:bg-background-hover text-text-muted hover:text-brand-primary transition-colors shrink-0"
                      title="Edit category"
                    >
                      <Pencil className="w-3.5 h-3.5" />
                    </button>
                  </div>
                );
              })}
            </div>
          </div>
        ))}

      {/* ------------------------------------------------------------------ */}
      {/* Pagination                                                         */}
      {/* ------------------------------------------------------------------ */}
      {!txLoading && totalPages > 1 && (
        <div className="flex items-center justify-center gap-4 py-6">
          <button
            onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
            disabled={currentPage <= 1}
            className="p-2 rounded-lg bg-background-card border border-border-primary disabled:opacity-30 hover:border-brand-primary transition-colors"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <span className="text-sm text-text-secondary">
            Page {currentPage} of {totalPages}
          </span>
          <button
            onClick={() => setOffset(offset + PAGE_SIZE)}
            disabled={currentPage >= totalPages}
            className="p-2 rounded-lg bg-background-card border border-border-primary disabled:opacity-30 hover:border-brand-primary transition-colors"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      )}
    </MainLayout>
  );
}
