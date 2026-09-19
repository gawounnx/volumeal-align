import { create } from 'zustand';
import type { FoodItemEstimation, NutritionSummary } from '../types/vision';
const keys = ['caloriesKcal','carbsG','proteinG','fatG','sodiumMg'] as const;
export function correctFoodItemWeight(item: FoodItemEstimation, weightG: number): FoodItemEstimation {
  if (!Number.isFinite(weightG) || weightG <= 0 || item.weightG <= 0) return item;
  const ratio=weightG/item.weightG; const next={...item,weightG};
  for (const key of keys) next[key]=Number((item[key]*ratio).toFixed(2));
  return next;
}
export function sumNutrition(items: FoodItemEstimation[]): NutritionSummary { return keys.reduce((t,k)=>{t[k]=Number(items.reduce((s,i)=>s+i[k],0).toFixed(2));return t;},{caloriesKcal:0,carbsG:0,proteinG:0,fatG:0,sodiumMg:0}); }
interface State { items:FoodItemEstimation[]; totalNutrition:NutritionSummary; setItems:(v:FoodItemEstimation[])=>void; correctWeight:(id:string,w:number)=>void; reset:()=>void }
const empty={caloriesKcal:0,carbsG:0,proteinG:0,fatG:0,sodiumMg:0};
// Ref: FR-007. Optimistic client preview; /confirm remains the SSOT.
export const useMealCorrectionStore=create<State>(set=>({items:[],totalNutrition:empty,setItems:items=>set({items,totalNutrition:sumNutrition(items)}),correctWeight:(id,w)=>set(s=>{const items=s.items.map(i=>i.id===id?correctFoodItemWeight(i,w):i);return {items,totalNutrition:sumNutrition(items)}}),reset:()=>set({items:[],totalNutrition:empty})}));
