import clsx, { type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

const INR = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 0,
});

export function formatCurrency(value: number | string | null | undefined): string {
  const n = typeof value === 'string' ? Number(value) : value;
  if (n == null || Number.isNaN(n)) return '₹0';
  return INR.format(n);
}

export function formatPercent(value: number, fractionDigits = 0): string {
  if (Number.isNaN(value)) return '0%';
  return `${value.toFixed(fractionDigits)}%`;
}

type DatePreset = 'short' | 'medium' | 'long' | 'full';

const DATE_PRESETS: Record<DatePreset, Intl.DateTimeFormatOptions> = {
  short: { day: '2-digit', month: 'short' },
  medium: { day: '2-digit', month: 'short', year: 'numeric' },
  long: { day: 'numeric', month: 'long', year: 'numeric' },
  full: { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' },
};

export function formatDate(
  value: string | number | Date,
  opts: DatePreset | Intl.DateTimeFormatOptions = 'short',
): string {
  const resolved = typeof opts === 'string' ? DATE_PRESETS[opts] : opts;
  try {
    return new Date(value).toLocaleDateString('en-IN', resolved);
  } catch {
    return String(value);
  }
}

export function getGaugeColor(amount: number): string {
  if (!Number.isFinite(amount) || amount <= 0) return '#94a3b8';
  if (amount < 200) return '#ef4444';   // Red — critical
  if (amount < 800) return '#f59e0b';   // Yellow — caution
  return '#22c55e';                     // Green — safe
}

const CATEGORY_COLORS: Record<string, string> = {
  food: '#f59e0b',
  groceries: '#f59e0b',
  coffee: '#f59e0b',
  transport: '#22c55e',
  travel: '#22c55e',
  shopping: '#ec4899',
  entertainment: '#8b5cf6',
  utilities: '#f97316',
  housing: '#ef4444',
  income: '#22c55e',
  savings: '#3b82f6',
  other: '#64748b',
};

export function getCategoryColor(category: string | null | undefined): string {
  if (!category) return CATEGORY_COLORS.other;
  return CATEGORY_COLORS[category.toLowerCase()] ?? CATEGORY_COLORS.other;
}

export function getCategoryLabel(category: string | null | undefined): string {
  if (!category) return 'Other';
  return category.charAt(0).toUpperCase() + category.slice(1).toLowerCase();
}
