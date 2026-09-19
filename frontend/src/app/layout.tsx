import type { Metadata } from "next";
import "./globals.css";
import MockProvider from "../components/providers/MockProvider";
import ApiErrorNotifier from "../components/providers/ApiErrorNotifier";

export const metadata: Metadata = {
  title: "VoluMeal-Align | 3D 식단 체적 & AI 영양 분석 엔진",
  description: "Monocular 3D Meal Volume Estimation & AI Nutrition Analysis Engine",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko">
      <body className="min-h-screen bg-slate-950 text-slate-100 antialiased">
        <MockProvider>
          <ApiErrorNotifier />
          {children}
        </MockProvider>
      </body>
    </html>
  );
}