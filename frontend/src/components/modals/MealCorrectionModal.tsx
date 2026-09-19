'use client';

import React, { useState } from 'react';
import { X, Check, Scale } from 'lucide-react';
import type { FoodItemEstimation } from '../../types/vision';

interface Props {
  item: FoodItemEstimation;
  open: boolean;
  disabled?: boolean;
  onChange: (weight: number) => void;
  onClose: () => void;
}

export default function MealCorrectionModal({
  item,
  open,
  disabled,
  onChange,
  onClose,
}: Props) {
  const [currentWeight, setCurrentWeight] = useState<number>(item.weightG);

  if (!open) return null;

  const handleWeightChange = (newVal: number) => {
    if (Number.isFinite(newVal) && newVal > 0) {
      setCurrentWeight(newVal);
      onChange(newVal);
    }
  };

  const handleConfirm = () => {
    if (Number.isFinite(currentWeight) && currentWeight > 0) {
      onChange(currentWeight);
    }
    onClose();
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="중량 수동 보정"
      className="fixed inset-0 z-50 grid place-items-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in"
    >
      <div
        data-testid="correction-modal"
        className="w-full max-w-[calc(100vw-2rem)] sm:max-w-sm rounded-2xl bg-slate-900 border border-slate-700 p-5 shadow-2xl flex flex-col gap-4 text-slate-100"
      >
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2">
            <Scale className="w-5 h-5 text-cyan-400" />
            <h2 className="text-base font-bold text-slate-100">{item.foodName} 중량 보정</h2>
          </div>
          <button
            type="button"
            data-testid="modal-close-btn"
            onClick={onClose}
            aria-label="모달 닫기"
            className="p-1 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="space-y-3">
          <div className="text-xs text-slate-400 flex justify-between">
            <span>추정 체적</span>
            <span className="font-mono text-slate-200 font-semibold">{item.volumeCm3} cm³</span>
          </div>

          <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider">
            보정 중량 (g)
            <div className="mt-1.5 relative">
              <input
                data-testid="weight-input"
                aria-label={`${item.foodName} 보정 중량`}
                type="number"
                min="0.01"
                step="0.01"
                inputMode="decimal"
                value={currentWeight}
                disabled={disabled}
                onChange={e => {
                  const v = Number(e.target.value);
                  if (Number.isFinite(v)) handleWeightChange(v);
                }}
                className="w-full rounded-xl bg-slate-950 border border-slate-700 px-3.5 py-2.5 text-base font-bold text-emerald-400 focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
              />
              <span className="absolute right-3.5 top-1/2 -translate-y-1/2 text-sm font-semibold text-slate-400">
                g
              </span>
            </div>
          </label>

          <div className="flex gap-2 pt-1">
            {[-10, 10, 50].map(delta => (
              <button
                key={delta}
                type="button"
                disabled={disabled}
                onClick={() => handleWeightChange(Math.max(1, Math.round((currentWeight + delta) * 10) / 10))}
                className="flex-1 py-1.5 px-2 rounded-lg text-xs bg-slate-800 text-slate-300 hover:bg-slate-700 border border-slate-700 active:scale-95 transition"
              >
                {delta > 0 ? `+${delta}g` : `${delta}g`}
              </button>
            ))}
          </div>
        </div>

        <div className="pt-2 flex gap-2">
          <button
            type="button"
            data-testid="confirm-btn"
            onClick={handleConfirm}
            disabled={disabled}
            className="w-full flex items-center justify-center gap-1.5 py-2.5 px-4 rounded-xl font-semibold text-sm bg-gradient-to-r from-cyan-500 to-teal-500 text-slate-950 hover:from-cyan-400 hover:to-teal-400 disabled:opacity-50 transition shadow-lg"
          >
            <Check className="w-4 h-4" />
            <span>완료 및 확정</span>
          </button>
        </div>
      </div>
    </div>
  );
}
