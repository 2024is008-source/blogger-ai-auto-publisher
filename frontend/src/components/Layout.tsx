import React, { useState } from 'react';
import {
  Activity,
  CalendarClock,
  FileEdit,
  Globe,
  History,
  Image as ImageIcon,
  LayoutDashboard,
  ListTodo,
  Menu,
  Moon,
  RefreshCw,
  Settings,
  Sparkles,
  Sun,
  X,
} from 'lucide-react';
import type { NavSection } from '../types';

interface LayoutProps {
  active: NavSection;
  onNavigate: (section: NavSection) => void;
  dark: boolean;
  onToggleTheme: () => void;
  onRefresh: () => void;
  loading: boolean;
  repoLabel: string;
  children: React.ReactNode;
}

const NAV_ITEMS: Array<{ id: NavSection; label: string; icon: React.ComponentType<{ className?: string }> }> = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard },
  { id: 'generator', label: 'Article Generator', icon: Sparkles },
  { id: 'editor', label: 'Article Editor', icon: FileEdit },
  { id: 'images', label: 'Image Finder', icon: ImageIcon },
  { id: 'accounts', label: 'Blogger Accounts', icon: Globe },
  { id: 'queue', label: 'Publishing Queue', icon: ListTodo },
  { id: 'history', label: 'Publishing History', icon: History },
  { id: 'scheduler', label: 'Automation Scheduler', icon: CalendarClock },
  { id: 'settings', label: 'Settings', icon: Settings },
  { id: 'logs', label: 'Logs & Diagnostics', icon: Activity },
];

export const Layout: React.FC<LayoutProps> = ({
  active,
  onNavigate,
  dark,
  onToggleTheme,
  onRefresh,
  loading,
  repoLabel,
  children,
}) => {
  const [mobileOpen, setMobileOpen] = useState(false);

  const navList = (
    <nav aria-label="Main navigation" className="flex-1 space-y-1 px-3 py-4">
      {NAV_ITEMS.map((item) => {
        const Icon = item.icon;
        const isActive = active === item.id;
        return (
          <button
            key={item.id}
            type="button"
            onClick={() => {
              onNavigate(item.id);
              setMobileOpen(false);
            }}
            aria-current={isActive ? 'page' : undefined}
            className={`flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
              isActive
                ? 'bg-brand-600 text-white'
                : 'text-slate-300 hover:bg-slate-800 hover:text-white'
            }`}
          >
            <Icon className="h-4 w-4 shrink-0" />
            <span className="truncate">{item.label}</span>
          </button>
        );
      })}
    </nav>
  );

  return (
    <div className="flex min-h-screen bg-slate-50 dark:bg-slate-950">
      {/* Desktop Sidebar */}
      <aside className="hidden w-64 shrink-0 flex-col bg-navy-900 text-white lg:flex">
        <div className="flex h-16 items-center gap-2.5 border-b border-slate-800 px-5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600 text-white font-bold text-sm">
            BA
          </div>
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold tracking-tight">Blogger AI Publisher</p>
            <p className="truncate text-[11px] text-slate-400">Serverless GitHub Edition</p>
          </div>
        </div>
        {navList}
        <div className="border-t border-slate-800 p-4 text-xs text-slate-400">
          <p className="truncate font-medium text-slate-300">{repoLabel}</p>
          <p className="mt-0.5">Secrets stay in GitHub Actions</p>
        </div>
      </aside>

      {/* Mobile Drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-40 flex lg:hidden">
          <div
            className="fixed inset-0 bg-slate-950/60"
            onClick={() => setMobileOpen(false)}
            aria-hidden="true"
          />
          <aside className="relative z-10 flex w-64 flex-col bg-navy-900 text-white">
            <div className="flex h-16 items-center justify-between border-b border-slate-800 px-4">
              <span className="text-sm font-semibold">Blogger AI Publisher</span>
              <button
                type="button"
                onClick={() => setMobileOpen(false)}
                aria-label="Close navigation menu"
                className="rounded-md p-1.5 text-slate-300 hover:bg-slate-800"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            {navList}
          </aside>
        </div>
      )}

      {/* Main Column */}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-slate-200 bg-white/95 px-4 backdrop-blur dark:border-slate-800 dark:bg-slate-900/95 sm:px-6">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setMobileOpen(true)}
              aria-label="Open navigation menu"
              className="rounded-lg border border-slate-200 p-2 text-slate-600 hover:bg-slate-100 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800 lg:hidden"
            >
              <Menu className="h-5 w-5" />
            </button>
            <h1 className="text-base font-semibold text-slate-900 dark:text-slate-100 sm:text-lg">
              {NAV_ITEMS.find((i) => i.id === active)?.label}
            </h1>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onRefresh}
              disabled={loading}
              aria-label="Refresh repository data"
              className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
              <span className="hidden sm:inline">Sync Data</span>
            </button>
            <button
              type="button"
              onClick={onToggleTheme}
              aria-label={dark ? 'Switch to light mode' : 'Switch to dark mode'}
              className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
            >
              {dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            </button>
          </div>
        </header>

        <main className="mx-auto w-full max-w-7xl flex-1 p-4 sm:p-6">{children}</main>
      </div>
    </div>
  );
};
