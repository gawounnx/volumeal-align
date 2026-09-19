"use client";
import React, { useEffect, useState } from 'react';
import { listMeals, getMeal, AuthenticationError } from '../services/api';
import type { MealListItem, MealDetail } from '../services/api';
export default function MealHistory({ refreshKey, onSessionExpired }: { refreshKey?: string; onSessionExpired: () => void }) {
  const [meals, setMeals] = useState<MealListItem[]>([]);
  const [detail, setDetail] = useState<MealDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    let active = true;
    setLoading(true); setError(null);
    listMeals().then(items => { if (active) setMeals(items); })
      .catch(err => { if (active) { setError(err instanceof Error ? err.message : '기록 조회 실패'); if (err instanceof AuthenticationError) onSessionExpired(); } })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [refreshKey, revision, onSessionExpired]);
  useEffect(() => {
    if (!selectedId) return;
    let active = true;
    setDetail(null); setError(null);
    getMeal(selectedId).then(item => { if (active) setDetail(item); })
      .catch(err => { if (active) { setError(err instanceof Error ? err.message : '상세 조회 실패'); if (err instanceof AuthenticationError) onSessionExpired(); } });
    return () => { active = false; };
  }, [selectedId, onSessionExpired]);
  return <section className="bg-slate-900 border border-slate-800 rounded-xl p-5">
    <div className="flex justify-between"><h2 className="font-semibold">저장된 식단 기록</h2><button type="button" disabled={loading} onClick={() => setRevision(v => v + 1)} className="text-sm text-cyan-300">새로고침</button></div>
    {error && <p role="alert" className="mt-2 text-sm text-rose-300">{error}</p>}
    {loading ? <p className="mt-2 text-sm">기록 불러오는 중...</p> : meals.length === 0 ? <p className="mt-2 text-sm text-slate-400">저장된 식단이 없습니다.</p> :
      <ul className="mt-3 space-y-2">{meals.map(meal => <li key={meal.id}><button type="button" className="text-left text-sm text-cyan-300" onClick={() => setSelectedId(meal.id)}>
        {new Date(meal.createdAt).toLocaleString('ko-KR')} · {meal.totalCaloriesKcal} kcal · 음식 {meal.foodItemCount}개
      </button></li>)}</ul>}
    {detail && <div className="mt-4 border-t border-slate-700 pt-3" aria-label="식단 상세">
      <h3 className="font-semibold">식단 상세</h3>
      <ul>{detail.foodItems.map(food => <li key={food.id} className="mt-2 text-sm">{food.foodName} · {food.volumeCm3} cm³ · {food.weightG} g · {food.caloriesKcal} kcal</li>)}</ul>
      {detail.drugWarnings.map(warning => <p key={warning.id} className="mt-2 text-sm text-amber-300">{warning.warningTitle}: {warning.warningMessage}</p>)}
    </div>}
  </section>;
}
