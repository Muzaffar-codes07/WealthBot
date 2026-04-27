'use client';

import { Plus } from 'lucide-react';

interface HeaderProps {
  title: string;
  subtitle?: string;
  userName?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
}

export function Header({ title, subtitle, userName, action }: HeaderProps) {
  return (
    <header className="flex items-center justify-between mb-6 sm:mb-8">
      <div className="min-w-0 flex-1">
        <h1 className="text-xl sm:text-2xl font-bold text-text-primary truncate">
          {title}
          {userName && <span>, {userName}</span>}
        </h1>
        {subtitle && (
          <p className="text-text-secondary mt-1">{subtitle}</p>
        )}
      </div>

      {action && (
        <div className="flex items-center gap-4">
          <button
            onClick={action.onClick}
            className="btn-primary flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            {action.label}
          </button>
        </div>
      )}
    </header>
  );
}
