import React from 'react';
import { CheckCircle2, Info, X, XCircle } from 'lucide-react';
import type { ToastMessage } from '../types';

export const ToastContainer: React.FC<{
  toasts: ToastMessage[];
  onDismiss: (id: string) => void;
}> = ({ toasts, onDismiss }) => {
  if (!toasts.length) return null;
  return (
    <div
      aria-live="polite"
      className="fixed bottom-4 right-4 z-50 flex w-full max-w-sm flex-col gap-2"
    >
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className="flex items-start gap-2.5 rounded-lg border border-slate-200 bg-white p-3.5 shadow-md dark:border-slate-700 dark:bg-slate-900"
        >
          {toast.type === 'success' && <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />}
          {toast.type === 'error' && <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-red-600" />}
          {toast.type === 'info' && <Info className="mt-0.5 h-4 w-4 shrink-0 text-brand-600" />}
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium text-slate-900 dark:text-slate-100">{toast.title}</p>
            {toast.detail && (
              <p className="mt-0.5 text-xs text-slate-600 dark:text-slate-400">{toast.detail}</p>
            )}
          </div>
          <button
            type="button"
            onClick={() => onDismiss(toast.id)}
            aria-label="Dismiss notification"
            className="rounded p-0.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      ))}
    </div>
  );
};
