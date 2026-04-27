'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Gauge,
  ArrowLeftRight,
  BarChart3,
  Settings,
  X,
  LogOut,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useUserStore } from '@/stores/userStore';
import { useLogout } from '@/hooks/useApi';

interface NavItem {
  label: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
}

const navItems: NavItem[] = [
  { label: 'Home', href: '/dashboard', icon: Gauge },
  { label: 'Transactions', href: '/transactions', icon: ArrowLeftRight },
  { label: 'Analytics', href: '/budgets', icon: BarChart3 },
  { label: 'Settings', href: '/settings', icon: Settings },
];

interface SidebarProps {
  user?: {
    name: string;
    plan: string;
    avatar?: string;
  };
}

export function Sidebar({ user }: SidebarProps) {
  const pathname = usePathname();
  const { sidebarOpen, setSidebarOpen } = useUserStore();
  const logout = useLogout();

  return (
    <>
      {/* Backdrop overlay — visible only on mobile/tablet when sidebar is open */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <aside
        className={cn(
          'fixed left-0 top-0 h-full w-64 bg-background-secondary/80 backdrop-blur-xl border-r border-white/[0.06] flex flex-col z-50 transition-transform duration-200',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        )}
      >
      {/* Logo */}
      <div className="p-6 flex items-center justify-between">
        <Link href="/dashboard" className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-full bg-brand-primary flex items-center justify-center">
            <span className="text-white font-bold text-sm">W</span>
          </div>
          <span className="text-xl font-semibold text-text-primary">WealthBot</span>
        </Link>
        <button
          onClick={() => setSidebarOpen(false)}
          className="lg:hidden p-1.5 rounded-lg hover:bg-background-hover text-text-muted"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-4 py-2" aria-label="Main navigation">
        <ul className="space-y-1">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            const Icon = item.icon;

            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  onClick={() => setSidebarOpen(false)}
                  aria-label={item.label}
                  aria-current={isActive ? 'page' : undefined}
                  className={cn(
                    'flex items-center gap-3 px-4 py-3 rounded-lg transition-colors duration-200',
                    isActive
                      ? 'bg-brand-primary/10 text-brand-primary'
                      : 'text-text-secondary hover:bg-background-hover hover:text-text-primary'
                  )}
                >
                  <Icon className="w-5 h-5" />
                  <span className="font-medium">{item.label}</span>
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* User Section */}
      <div className="p-4 border-t border-white/[0.06]">
        <div className="flex items-center gap-3 p-2">
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-brand-primary to-brand-primary-dark flex items-center justify-center">
            {user?.avatar ? (
              <img
                src={user.avatar}
                alt={user?.name || 'User'}
                className="w-full h-full rounded-full object-cover"
              />
            ) : (
              <span className="text-white font-semibold">
                {user?.name?.charAt(0) || 'A'}
              </span>
            )}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-text-primary truncate">
              {user?.name || 'Arjun'}
            </p>
            <p className="text-xs text-text-muted flex items-center gap-1">
              <Settings className="w-3 h-3" />
              {user?.plan || 'Student'}
            </p>
          </div>
          <button
            onClick={logout}
            aria-label="Log out"
            title="Log out"
            className="p-2 rounded-lg text-text-muted hover:text-text-primary hover:bg-background-hover transition-colors"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </aside>
    </>
  );
}
