import type { Metadata } from "next";
import "./globals.css";
import MockProvider from "../components/providers/MockProvider";
import ApiErrorNotifier from "../components/providers/ApiErrorNotifier";

export const metadata: Metadata = {
  title: "VoluMeal-Align | 3D 식단 체적 & 복약 간섭 분석 엔진",
  description: "Monocular 3D Meal Volume Estimation & Drug-Food Interaction Engine",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko">
      <body className="min-h-screen bg-slate-50 text-slate-900 antialiased">
        <header className="border-b border-slate-200 bg-white/80 backdrop-blur sticky top-0 z-50">
          <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-xl font-black bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
                VoluMeal-Align
              </span>
              <span className="text-xs px-2 py-0.5 rounded bg-blue-100 text-blue-800 font-semibold">
                AI 3D Vision
              </span>
            </div>
            <div className="text-xs text-slate-500">
              KFDA Food-Drug Safety Engine Active
            </div>
          </div>
        </header>
        <main className="max-w-7xl mx-auto px-4 py-8"><MockProvider><ApiErrorNotifier />{children}</MockProvider></main>
      </body>
    </html>
  );
}