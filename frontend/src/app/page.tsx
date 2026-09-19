'use client';

import React, { useState, useRef, useEffect, useCallback } from 'react';
import dynamic from 'next/dynamic';
import MealHistory from '../components/MealHistory';
import { estimateMealVision, confirmMealVision, login, register, logout, getServiceStatus, AuthenticationError, listMeals } from '../services/api';
import type { FoodCandidate, FoodItemEstimation, MealEstimateResponse } from '../types/vision';
import { correctFoodItemWeight } from '../stores/useMealCorrectionStore';
import { validateImageFile } from '../utils/fileValidator';
import MealCorrectionModal from '../components/modals/MealCorrectionModal';
import Toast from '../components/ui/Toast';

const EMPTY_ITEMS: MealEstimateResponse['foodItems'] = [];
const NUTRIENT_KEYS = ['caloriesKcal', 'carbsG', 'proteinG', 'fatG', 'sodiumMg'] as const;

function updateTotals(items: FoodItemEstimation[]): MealEstimateResponse['totalNutrition'] {
  return NUTRIENT_KEYS.reduce((totals, key) => {
    totals[key] = Number(items.reduce((sum, item) => sum + item[key], 0).toFixed(2));
    return totals;
  }, { caloriesKcal: 0, carbsG: 0, proteinG: 0, fatG: 0, sodiumMg: 0 });
}

function applyCandidate(item: FoodItemEstimation, candidate: FoodCandidate): FoodItemEstimation {
  if (candidate.weightG == null || candidate.densityGCm3 == null) return item;
  return {
    ...item,
    foodId: candidate.foodId,
    foodName: candidate.foodName,
    densityGCm3: candidate.densityGCm3,
    weightG: candidate.weightG,
    caloriesKcal: candidate.caloriesKcal ?? item.caloriesKcal,
    carbsG: candidate.carbsG ?? item.carbsG,
    proteinG: candidate.proteinG ?? item.proteinG,
    fatG: candidate.fatG ?? item.fatG,
    sodiumMg: candidate.sodiumMg ?? item.sodiumMg,
    requiresConfirmation: false,
  };
}

function applyWeight(item: FoodItemEstimation, weightG: number): FoodItemEstimation {
  return correctFoodItemWeight(item, weightG);
}

const ThreeViewer = dynamic(() => import('../components/viewer3d/ThreeCanvas'), {
  ssr: false,
  loading: () => (
    <div className="w-full h-[420px] rounded-xl border border-slate-800 bg-slate-900 flex items-center justify-center text-slate-500 font-mono text-sm">
      3D 뷰어 엔진 초기화 중...
    </div>
  ),
});

export default function MealAnalysisPage() {
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [result, setResult] = useState<MealEstimateResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [unmatchedItemIds, setUnmatchedItemIds] = useState<Set<string>>(new Set());
  const [saving, setSaving] = useState(false);
  const [correctionItemId, setCorrectionItemId] = useState<string | null>(null);
  const savingRef = useRef(false);

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login');
  const [signedIn, setSignedIn] = useState(false);
  const [authLoading, setAuthLoading] = useState(false);
  const [serviceStatus, setServiceStatus] = useState('서버 상태 확인 중');
  useEffect(() => {
    let active = true;
    getServiceStatus().then(status => { if (active) setServiceStatus(status); })
      .catch(() => { if (active) setServiceStatus('서버 연결 확인 필요'); });
    listMeals().then(() => { if (active) setSignedIn(true); }).catch(() => { /* not authenticated yet */ });
    return () => { active = false; };
  }, []);
  const handleSessionExpired = useCallback(() => { logout(); setSignedIn(false); setResult(null); setError('로그인이 만료되었습니다. 다시 로그인해 주세요.'); }, []);
  const handleLogin = async (event: React.FormEvent) => {
    event.preventDefault();
    setAuthLoading(true); setError(null);
    try { await login(email, password); setSignedIn(true); setPassword(''); }
    catch (err) {
      const msg = err instanceof Error ? err.message : '로그인 실패';
      if (msg.includes('ALREADY_AUTHENTICATED') || msg.includes('403')) {
        setSignedIn(true);
        setPassword('');
      } else {
        setError(msg);
      }
    }
    finally { setAuthLoading(false); }
  };
  const handleRegister = async (event: React.FormEvent) => {
    event.preventDefault();
    setAuthLoading(true); setError(null);
    try {
      // Ref: signup already sets the auth cookies (Section 9.1); a follow-up /login call
      // hits the already-authenticated guard (Section 9.3) and 403s.
      await register(email, password, name);
      setSignedIn(true); setPassword(''); setName('');
    } catch (err) { setError(err instanceof Error ? err.message : '회원가입 실패'); }
    finally { setAuthLoading(false); }
  };

  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selected = e.target.files[0];
      setFile(selected);
      setResult(null);
      setUnmatchedItemIds(new Set());
      setError(null);
      const validation = await validateImageFile(selected);
      if (!validation.valid) {
        setFile(null); setPreviewUrl(null); setResult(null);
        e.target.value = '';
        setError(validation.message);
        setToastMessage(validation.message);
        return;
      }
    }
  };

  const handleAnalyze = async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    setResult(null);
    setUnmatchedItemIds(new Set());

    try {
      const data = await estimateMealVision(file);
      setResult(data.data);
      getServiceStatus().then(setServiceStatus).catch(() => setServiceStatus('서버 연결 확인 필요'));
    } catch (err: unknown) {
      if (err instanceof AuthenticationError) { handleSessionExpired(); return; }
      const message = err instanceof Error ? err.message : '';
      setError(message.includes('유효한 음식 또는 약제가 검출되지 않았습니다')
        ? '현재 모델이 지원하는 음식(백미밥, 시금치나물, 김치찌개, 된장찌개, 불고기, 연어구이, 바나나, 사과, 삶은 달걀)이 검출되지 않았습니다. 이 사진의 식재료를 분석하려면 실사진 학습 데이터 추가가 필요합니다.'
        : message || '분석 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const handleCandidateSelect = (itemId: string, candidate: FoodCandidate) => {
    if (savingRef.current) return;
    setUnmatchedItemIds(current => {
      const next = new Set(current);
      next.delete(itemId);
      return next;
    });
    setResult(current => {
      if (!current) return current;
      const foodItems = current.foodItems.map(item => item.id === itemId ? applyCandidate(item, candidate) : item);
      return { ...current, isPersisted: false, foodItems, totalNutrition: updateTotals(foodItems), requiresConfirmation: foodItems.some(item => item.requiresConfirmation) };
    });
  };

  const handleNoCandidate = (itemId: string) => {
    if (savingRef.current) return;
    setUnmatchedItemIds(current => new Set(current).add(itemId));
  };

  const handleWeightChange = (itemId: string, value: string) => {
    if (savingRef.current) return;
    const weightG = Number(value);
    if (!Number.isFinite(weightG) || weightG <= 0) return;
    setResult(current => {
      if (!current) return current;
      const foodItems = current.foodItems.map(item => item.id === itemId ? applyWeight(item, weightG) : item);
      return { ...current, isPersisted: false, foodItems, totalNutrition: updateTotals(foodItems) };
    });
  };

  const handleConfirm = async () => {
    if (!result || result.requiresConfirmation || unmatchedItemIds.size > 0 || savingRef.current) return;
    savingRef.current = true;
    setSaving(true); setError(null);
    try {
      const saved = await confirmMealVision(result);
      setResult(current => current === result ? saved : current);
    } catch (err) {
      if (err instanceof AuthenticationError) handleSessionExpired();
      setError(err instanceof Error ? err.message : '저장하지 못했습니다. 다시 시도해 주세요.');
    } finally {
      savingRef.current = false;
      setSaving(false);
    }
  };

  useEffect(() => {
    if (!file) return;
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  useEffect(() => {
    if (!previewUrl || !canvasRef.current) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const img = new Image();
    img.onload = () => {
      canvas.width = img.naturalWidth;
      canvas.height = img.naturalHeight;
      ctx.drawImage(img, 0, 0);

      result?.foodItems.forEach((item) => {
        const x1 = item.bbox2d.xmin * canvas.width;
        const y1 = item.bbox2d.ymin * canvas.height;
        const x2 = item.bbox2d.xmax * canvas.width;
        const y2 = item.bbox2d.ymax * canvas.height;
        ctx.strokeStyle = '#38bdf8';
        ctx.lineWidth = 4;
        ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);

        ctx.fillStyle = 'rgba(56, 189, 248, 0.85)';
        ctx.fillRect(x1, Math.max(0, y1 - 28), 190, 28);
        ctx.fillStyle = '#0f172a';
        ctx.font = 'bold 16px sans-serif';
        ctx.fillText(
          `${item.requiresConfirmation ? '확인 필요' : item.foodName} (${(item.confidenceScore * 100).toFixed(1)}%)`,
          x1 + 6,
          Math.max(0, y1 - 8)
        );
      });
    };
    img.src = previewUrl;
    return () => { img.onload = null; };
  }, [previewUrl, result]);

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 p-4 sm:p-6 md:p-10 font-sans relative">
      <Toast message={toastMessage} onClose={() => setToastMessage(null)} />
      <header className="max-w-7xl mx-auto mb-8 border-b border-slate-800 pb-5 flex flex-wrap gap-3 justify-between items-center">
        <div>
          <h1 className="text-2xl md:text-3xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-teal-300">
            VoluMeal-Align
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            식단 체적·영양 추정 및 등록된 복약 정보 기반 상호작용 확인
          </p>
        </div>
        <span className="bg-emerald-950 text-emerald-400 text-xs px-3 py-1 rounded-full border border-emerald-700 font-mono">
          {serviceStatus}
        </span>
      </header>

      <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* 좌측: 파일 업로드 및 2D 검출 오버레이 */}
        <section className="lg:col-span-5 min-w-0 flex flex-col gap-5">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
            {signedIn ? <button disabled={loading} onClick={() => { logout(); setSignedIn(false); setResult(null); }}>로그아웃</button> :
              <form onSubmit={authMode === 'login' ? handleLogin : handleRegister} className="flex flex-col gap-3">
                {authMode === 'register' && <label>이름<input className="block w-full bg-slate-800 p-2 rounded" type="text" autoComplete="name" value={name} onChange={e => setName(e.target.value)} required /></label>}
                <label>이메일<input className="block w-full bg-slate-800 p-2 rounded" type="email" autoComplete="username" value={email} onChange={e => setEmail(e.target.value)} required /></label>
                <label>비밀번호<input className="block w-full bg-slate-800 p-2 rounded" type="password" autoComplete={authMode === 'register' ? 'new-password' : 'current-password'} value={password} onChange={e => setPassword(e.target.value)} minLength={authMode === 'register' ? 8 : 1} required /></label>
                <button disabled={authLoading} type="submit" className="rounded bg-cyan-700 p-2">{authLoading ? (authMode === 'login' ? '로그인 중...' : '회원가입 중...') : (authMode === 'login' ? '로그인' : '회원가입')}</button>
                <button type="button" className="text-sm text-cyan-300 underline" onClick={() => { setAuthMode(authMode === 'login' ? 'register' : 'login'); setError(null); }}>
                  {authMode === 'login' ? '회원가입하기' : '로그인으로 돌아가기'}
                </button>
              </form>}
          </div>
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg">
            <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-3">
              식단 이미지 업로드
            </h2>
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp"
              disabled={loading || saving}
              onChange={handleFileChange}
              className="block w-full text-sm text-slate-400 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-cyan-600 file:text-white hover:file:bg-cyan-500 cursor-pointer"
            />

            {previewUrl && (
              <div className="mt-4 rounded-lg overflow-hidden border border-slate-800 bg-slate-950">
                <canvas ref={canvasRef} className="w-full h-auto object-contain block" />
              </div>
            )}

            <button
              onClick={handleAnalyze}
              disabled={!file || loading || saving}
              className="mt-4 w-full py-2.5 px-4 rounded-lg font-semibold text-sm bg-gradient-to-r from-cyan-500 to-teal-500 text-slate-950 hover:from-cyan-400 hover:to-teal-400 disabled:opacity-50 disabled:cursor-not-allowed transition shadow-lg"
            >
              {loading ? '이미지 분석 중...' : '식단 분석'}
            </button>
            {error && <p role="alert" className="text-xs text-rose-400 mt-2">{error}</p>}
          </div>

          {/* KFDA 의약품 상호작용 경고창 */}
          {result && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg">
              <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-3 flex items-center gap-2">
                <span>등록 복약과 식품 상호작용</span>
                <span className="text-xs bg-slate-800 px-2 py-0.5 rounded text-slate-400 font-mono">
                  {result.drugWarnings.length}건
                </span>
              </h2>

              {!result.isPersisted ? (
                <p className="text-xs text-amber-300">후보 선택·중량 보정 후 저장하면 복약 경고를 다시 확인합니다.</p>
              ) : result.drugWarnings.length === 0 ? (
                <div className="p-3 bg-emerald-950/40 border border-emerald-800 rounded-lg text-xs text-emerald-300">
                  이번 분석에서 반환된 상호작용 경고가 없습니다.
                </div>
              ) : (
                <div className="space-y-3">
                  {result.drugWarnings.map((alert, idx) => (
                    <div
                      key={idx}
                      className={`p-3.5 rounded-lg border text-xs space-y-1.5 ${
                        alert.riskLevel === 'DANGER'
                          ? 'bg-rose-950/50 border-rose-800 text-rose-200'
                          : 'bg-amber-950/50 border-amber-800 text-amber-200'
                      }`}
                    >
                      <div className="flex justify-between items-center font-bold">
                        <span className="text-sm">{alert.warningTitle}</span>
                        <span className="px-2 py-0.5 rounded font-mono text-[10px] bg-black/40 border border-current">
                          {alert.riskLevel}
                        </span>
                      </div>
                      <p className="leading-relaxed opacity-90">{alert.warningMessage}</p>
                      <div className="pt-1.5 border-t border-white/10 text-[11px] text-slate-300">
                        <span className="font-semibold text-white">임상 권고: </span>
                        {alert.actionGuide}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </section>

        {/* 우측: Three.js 3D 체적 복원 및 지표 카드 */}
        <section className="lg:col-span-7 min-w-0 flex flex-col gap-5">
          {signedIn && <MealHistory refreshKey={result?.isPersisted ? result.mealId : undefined} onSessionExpired={handleSessionExpired} />}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg">
            <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-3">
              3D 점군 및 경계 상자
            </h2>
            <ThreeViewer items={result?.foodItems || EMPTY_ITEMS} pointCloud={result?.visualization3d.pointCloud} height={420} />
            {result && !result.isCalibrated && <p className="mt-2 text-xs text-amber-300">카메라 미보정 추정값입니다. 원본 이미지는 서버에 보관하지 않습니다.</p>}
          </div>

          <section aria-label="영양소 요약" className="grid grid-cols-2 sm:grid-cols-5 gap-3">
            {([
              ['열량', 'caloriesKcal', 'kcal'],
              ['탄수화물', 'carbsG', 'g'],
              ['단백질', 'proteinG', 'g'],
              ['지방', 'fatG', 'g'],
              ['나트륨', 'sodiumMg', 'mg'],
            ] as const).map(([label, key, unit]) => (
              <div key={key} className="bg-slate-900 border border-slate-800 p-3.5 rounded-xl">
                <span className="text-[11px] text-slate-400 uppercase">{label}</span>
                <p data-testid={`total-${key}`} className="text-base font-bold text-slate-100 mt-0.5 font-mono">
                  {(result?.totalNutrition[key] ?? 0).toLocaleString()} {unit}
                </p>
              </div>
            ))}
          </section>

          {result && (
            <div className="rounded-xl border border-slate-800 p-4">
              <p role="status" className="text-sm text-slate-300">
                {result.isPersisted ? '저장되었습니다.' : unmatchedItemIds.size > 0 ? '지원 음식에 없는 항목은 저장할 수 없습니다. 다른 사진으로 다시 촬영해 주세요.' : result.requiresConfirmation ? '음식 후보를 모두 선택한 후 저장해 주세요.' : '변경 내용이 아직 저장되지 않았습니다.'}
              </p>
              <button type="button" onClick={handleConfirm}
                disabled={saving || result.isPersisted || result.requiresConfirmation || unmatchedItemIds.size > 0 || result.foodItems.length === 0}
                className="mt-2 rounded-lg bg-cyan-500 px-4 py-2 text-slate-950 disabled:opacity-50">
                {saving ? '저장 중...' : '확정하고 저장'}
              </button>
            </div>
          )}
          {result && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {result.foodItems.map((item, idx) => (
                <React.Fragment key={idx}>
                  <div className="bg-slate-900 border border-slate-800 p-3.5 rounded-xl">
                    <span className="text-[11px] text-slate-400 uppercase">식품명</span>
                    <p className="text-base font-bold text-cyan-400 capitalize mt-0.5">{item.requiresConfirmation ? '음식 확인 필요' : item.foodName}</p>
                  </div>
                  <div className="bg-slate-900 border border-slate-800 p-3.5 rounded-xl">
                    <span className="text-[11px] text-slate-400 uppercase">추정 체적</span>
                    <p className="text-base font-bold text-slate-100 mt-0.5">{item.volumeCm3} cm³</p>
                  </div>
                  <div className="bg-slate-900 border border-slate-800 p-3.5 rounded-xl">
                    <span className="text-[11px] text-slate-400 uppercase">추정 질량</span>
                    <label className="block mt-0.5">
                      <span className="sr-only">{item.foodName} 중량</span>
                      <input
                        aria-label={`${item.foodName} 중량`}
                        type="number"
                        min="0.01"
                        step="0.01"
                        value={item.weightG}
                        onChange={event => handleWeightChange(item.id, event.target.value)}
                        disabled={saving}
                        className="w-24 bg-transparent text-base font-bold text-emerald-400 outline-none"
                      />
                      <span className="text-base font-bold text-emerald-400"> g</span>
                    </label>
                    <button type="button" data-testid="open-correction-modal-btn" disabled={saving} onClick={() => setCorrectionItemId(item.id)} className="mt-1 text-xs text-cyan-300 underline">보정 모달 열기</button>
                  </div>
                  <div className="bg-slate-900 border border-slate-800 p-3.5 rounded-xl">
                    <span className="text-[11px] text-slate-400 uppercase">추정 열량</span>
                    <p className="text-base font-bold text-slate-300 mt-0.5 font-mono">
                      {item.caloriesKcal.toLocaleString()} kcal
                    </p>
                  </div>
                  {item.requiresConfirmation && (
                    <div className="col-span-2 sm:col-span-4 border border-amber-700 bg-amber-950/40 p-3.5 rounded-xl">
                      <p className="text-sm font-semibold text-amber-200">음식 확인이 필요합니다. 후보를 선택해 주세요.</p>
                      <div className="mt-2 flex flex-wrap gap-2">
                        {item.topCandidates.map(candidate => (
                          <button
                            key={candidate.foodId}
                            type="button"
                            onClick={() => handleCandidateSelect(item.id, candidate)}
                            disabled={saving}
                            className="rounded border border-amber-600 bg-amber-900/50 px-3 py-2 text-left text-xs text-amber-100 hover:bg-amber-800"
                          >
                            <span className="block font-semibold">{candidate.foodName}</span>
                            <span className="text-amber-300">유사도 {(candidate.score * 100).toFixed(0)}%</span>
                          </button>
                        ))}
                        <button
                          type="button"
                          onClick={() => handleNoCandidate(item.id)}
                          disabled={saving}
                          className="rounded border border-slate-500 bg-slate-800 px-3 py-2 text-left text-xs text-slate-100 hover:bg-slate-700"
                        >
                          후보에 정답 없음
                        </button>
                      </div>
                      {unmatchedItemIds.has(item.id) && (
                        <p role="alert" className="mt-2 text-xs text-rose-300">
                          현재 식품 카탈로그에서 일치하는 음식을 찾지 못했습니다. 이 결과는 저장되지 않습니다.
                        </p>
                      )}
                    </div>
                  )}
                </React.Fragment>
              ))}
            </div>
          )}
        </section>
      </div>
      {result && correctionItemId && (() => { const item = result.foodItems.find(current => current.id === correctionItemId); return item ? <MealCorrectionModal item={item} open disabled={saving} onChange={weight => handleWeightChange(item.id, String(weight))} onClose={() => setCorrectionItemId(null)} /> : null; })()}
    </main>
  );
}
