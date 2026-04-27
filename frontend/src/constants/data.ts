// =============================================================================
// WealthBot Mock Data — Indian Student Finance Context
// Realistic ₹ currency, UPI-heavy merchants, Gen Z spending patterns
// =============================================================================

export interface WBTransaction {
  id: string;
  merchant: string;
  amount: number;
  type: 'debit' | 'credit';
  category: string;
  categoryColor: string;
  date: string; // ISO string
  upiApp?: string;
  note?: string;
  aiConfidence?: number; // ML confidence score for category prediction
}

export interface Subscription {
  id: string;
  name: string;
  amount: number;
  icon: string;
  nextDue: string;
  frequency: 'monthly' | 'yearly';
  color: string;
}

export interface SpendingStat {
  category: string;
  thisMonth: number;
  lastMonth: number;
  color: string;
  icon: string;
}

export interface PrivacyLog {
  id: string;
  action: string;
  timestamp: string;
  status: 'encrypted' | 'accessed' | 'synced';
}

// ---------------------------------------------------------------------------
// Privacy / Access Logs
// ---------------------------------------------------------------------------
export const PRIVACY_LOGS: PrivacyLog[] = [
  { id: 'p1', action: 'ML Model accessed transaction data', timestamp: '10:42 AM', status: 'encrypted' },
  { id: 'p2', action: 'Statement parsed and tokenized', timestamp: '10:38 AM', status: 'synced' },
  { id: 'p3', action: 'Safe-to-Spend recalculated', timestamp: '10:35 AM', status: 'encrypted' },
  { id: 'p4', action: 'Category prediction model run', timestamp: '09:15 AM', status: 'accessed' },
  { id: 'p5', action: 'User session authenticated', timestamp: '09:00 AM', status: 'encrypted' },
  { id: 'p6', action: 'Data export requested (CSV)', timestamp: 'Yesterday', status: 'synced' },
];

// ---------------------------------------------------------------------------
// Quick Actions for Home
// ---------------------------------------------------------------------------
export const QUICK_ACTIONS = [
  { id: 'qa1', label: 'Scan QR', icon: '📷', color: '#3b82f6' },
  { id: 'qa2', label: 'Add Cash', icon: '💰', color: '#22c55e' },
  { id: 'qa3', label: 'Split Bill', icon: '🔀', color: '#a855f7' },
  { id: 'qa4', label: 'Pay Bills', icon: '📄', color: '#f59e0b' },
  { id: 'qa5', label: 'Invest', icon: '📈', color: '#ec4899' },
];

// ---------------------------------------------------------------------------
// Category config for consistent icon/color mapping
// ---------------------------------------------------------------------------
export const CATEGORY_CONFIG: Record<string, { icon: string; color: string }> = {
  Food: { icon: '🍕', color: '#f59e0b' },
  Travel: { icon: '🚗', color: '#3b82f6' },
  Shopping: { icon: '🛍️', color: '#ec4899' },
  Coffee: { icon: '☕', color: '#a855f7' },
  Groceries: { icon: '🥦', color: '#22c55e' },
  Entertainment: { icon: '🎮', color: '#8b5cf6' },
  Income: { icon: '💸', color: '#22c55e' },
  Housing: { icon: '🏠', color: '#6366f1' },
  Transportation: { icon: '🚌', color: '#0ea5e9' },
  Utilities: { icon: '💡', color: '#f97316' },
  Healthcare: { icon: '🏥', color: '#ef4444' },
  Insurance: { icon: '🛡️', color: '#14b8a6' },
  Education: { icon: '📚', color: '#8b5cf6' },
  Savings: { icon: '🏦', color: '#10b981' },
  Investments: { icon: '📈', color: '#06b6d4' },
  'Debt Payment': { icon: '💳', color: '#f43f5e' },
  Other: { icon: '📦', color: '#64748b' },
};
