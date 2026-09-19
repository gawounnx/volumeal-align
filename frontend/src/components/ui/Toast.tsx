'use client';

import React, { useEffect } from 'react';
import { AlertTriangle, X } from 'lucide-react';

interface ToastProps {
  message: string | null;
  onClose: () => void;
  durationMs?: number;
  type?: 'warning' | 'error' | 'info';
}

export default function Toast({ message, onClose, durationMs = 6000, type = 'warning' }: ToastProps) {
  useEffect(() => {
    if (!message) return;
    const timer = setTimeout(() => {
      onClose();
    }, durationMs);
    return () => clearTimeout(timer);
  }, [message, durationMs, onClose]);

  if (!message) return null;

  return (
    <div
      role="alert"
      aria-live="assertive"
      data-testid="toast-alert"
      className="fixed top-4 left-4 right-4 z-50 max-w-sm mx-auto flex items-start gap-3 p-4 rounded-xl bg-slate-900/95 border border-rose-500/50 text-slate-100 shadow-2xl backdrop-blur-md transition-all animate-in fade-in slide-in-from-top-4"
    >
      <div className="flex-shrink-0 mt-0.5 text-rose-400">
        <AlertTriangle className="w-5 h-5" />
      </div>
      <div className="flex-1 text-xs sm:text-sm font-medium leading-snug">
        {message}
      </div>
      <button
        type="button"
        onClick={onClose}
        aria-label="알림 닫기"
        data-testid="toast-close-btn"
        className="flex-shrink-0 -mr-1 -mt-1 p-1 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
}
