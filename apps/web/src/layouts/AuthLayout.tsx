
import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import {
  Activity,
  ShieldCheck,
  TrendingUp,
  Layers3,
  BrainCircuit,
  ChartNoAxesCombined,
} from "lucide-react";

import ThemeToggle from "../components/ThemeToggle";

interface AuthLayoutProps {
  children: ReactNode;
  heading: string;
  description: string;
}

const features = [
  {
    title: "Multi-timeframe analysis",
    description: "Understand market direction across multiple timeframes.",
    icon: Layers3,
  },
  {
    title: "Technical indicators",
    description: "Analyse price action and technical market conditions.",
    icon: ChartNoAxesCombined,
  },
  {
    title: "AI-assisted insights",
    description: "Get intelligent interpretations of market data.",
    icon: BrainCircuit,
  },
  {
    title: "Risk-aware scenarios",
    description: "Explore bullish and bearish scenarios with invalidation levels.",
    icon: ShieldCheck,
  },
];

export default function AuthLayout({
  children,
  heading,
  description,
}: AuthLayoutProps) {
  return (
    <main className="relative min-h-screen overflow-hidden bg-slate-50 text-slate-900 transition-colors duration-300 dark:bg-[#080d19] dark:text-white">

      {/* Background decoration */}
      <div className="pointer-events-none absolute -left-40 top-32 h-96 w-96 rounded-full bg-blue-500/5 blur-3xl" />
      <div className="pointer-events-none absolute -right-40 bottom-10 h-96 w-96 rounded-full bg-indigo-500/5 blur-3xl" />

      {/* Header */}
      <header className="relative z-10 flex items-center justify-between border-b border-slate-200/70 px-5 py-5 dark:border-slate-800/70 sm:px-10 lg:px-14">
        <Link
          to="/login"
          className="group flex items-center gap-3"
          aria-label="LovetechCyber AI Forex Analyst home"
        >
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-blue-600 text-white shadow-lg shadow-blue-600/20 transition group-hover:scale-105">
            <Activity size={24} />
          </div>

          <div>
            <p className="font-bold tracking-tight">
              LovetechCyber
            </p>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              AI Forex Analyst
            </p>
          </div>
        </Link>

        <ThemeToggle />
      </header>

      {/* Main content */}
      <section className="relative z-10 mx-auto grid min-h-[calc(100vh-81px)] max-w-7xl items-center gap-12 px-5 py-10 sm:px-10 lg:grid-cols-2 lg:gap-20 lg:px-14">

        {/* Branding and product information */}
        <div className="hidden lg:block">
          <div className="mb-7 inline-flex items-center gap-2 rounded-full border border-blue-200 bg-blue-50 px-4 py-2 text-sm font-medium text-blue-700 dark:border-blue-900/70 dark:bg-blue-950/40 dark:text-blue-300">
            <ShieldCheck size={17} />
            Intelligent market analysis
          </div>

          <h1 className="max-w-xl text-5xl font-bold leading-tight tracking-tight xl:text-6xl">
            Understand the market.
            <span className="mt-2 block text-blue-600">
              Trade with insight.
            </span>
          </h1>

          <p className="mt-6 max-w-lg text-base leading-8 text-slate-600 dark:text-slate-400 xl:text-lg">
            Analyse forex market conditions, understand
            multi-timeframe trends and receive AI-assisted
            insights with human confirmation.
          </p>

          {/* Feature list */}
          <div className="mt-10 grid max-w-xl grid-cols-2 gap-4">
            {features.map(({ title, description: detail, icon: Icon }) => (
              <div
                key={title}
                className="rounded-2xl border border-slate-200 bg-white/80 p-5 shadow-sm backdrop-blur transition hover:-translate-y-1 hover:border-blue-300 hover:shadow-md dark:border-slate-800 dark:bg-slate-900/70 dark:hover:border-blue-800"
              >
                <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-xl bg-blue-50 text-blue-600 dark:bg-blue-950/50 dark:text-blue-400">
                  <Icon size={20} />
                </div>

                <h3 className="text-sm font-semibold">
                  {title}
                </h3>

                <p className="mt-2 text-xs leading-5 text-slate-500 dark:text-slate-400">
                  {detail}
                </p>
              </div>
            ))}
          </div>

          {/* Analysis-only notice */}
          <div className="mt-8 flex items-center gap-3 text-sm text-slate-500 dark:text-slate-400">
            <TrendingUp size={18} className="text-blue-600" />
            <span>
              Market intelligence powered by LovetechCyber.
            </span>
          </div>
        </div>

        {/* Authentication form */}
        <div className="mx-auto w-full max-w-md">
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-xl shadow-slate-200/40 dark:border-slate-800 dark:bg-[#0d1728] dark:shadow-black/20 sm:p-8">

            {/* Mobile brand introduction */}
            <div className="mb-7 flex items-center gap-3 lg:hidden">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-600 text-white">
                <ShieldCheck size={22} />
              </div>

              <div>
                <p className="font-bold">LovetechCyber</p>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  AI Forex Analyst
                </p>
              </div>
            </div>

            <div className="mb-8">
              <h2 className="text-3xl font-bold tracking-tight">
                {heading}
              </h2>

              <p className="mt-3 text-sm leading-6 text-slate-500 dark:text-slate-400">
                {description}
              </p>
            </div>

            {children}

            <div className="mt-8 border-t border-slate-100 pt-5 dark:border-slate-800">
              <div className="flex items-center justify-center gap-2 text-xs text-slate-500 dark:text-slate-400">
                <ShieldCheck size={15} className="text-blue-600" />
                Secure authentication
              </div>

              <p className="mt-3 text-center text-xs leading-5 text-slate-500 dark:text-slate-500">
                LovetechCyber AI Forex Analyst
                <span className="mx-2">·</span>
                Analysis only, not automated trading
              </p>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
