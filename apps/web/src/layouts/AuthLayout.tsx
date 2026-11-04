
import type { ReactNode } from 'react'
import { Activity, ShieldCheck } from 'lucide-react'
import ThemeToggle from '../components/ThemeToggle'

interface AuthLayoutProps {
  children: ReactNode
  heading: string
  description: string
}

export default function AuthLayout({
  children,
  heading,
  description,
}: AuthLayoutProps) {
  return (
    <main className="min-h-screen bg-slate-50 text-slate-900 transition-colors dark:bg-[#080d19] dark:text-white">
      <header className="flex items-center justify-between px-5 py-5 sm:px-10">
        <a href="/login" className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-600 text-white">
            <Activity size={23} />
          </div>

          <div>
            <p className="font-bold tracking-tight">
              LovetechCyber
            </p>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              AI Forex Analyst
            </p>
          </div>
        </a>

        <ThemeToggle />
      </header>

      <section className="mx-auto grid min-h-[calc(100vh-85px)] max-w-6xl items-center gap-12 px-5 py-10 lg:grid-cols-2 lg:px-10">
        <div className="hidden lg:block">
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-blue-200 bg-blue-50 px-4 py-2 text-sm text-blue-700 dark:border-blue-900 dark:bg-blue-950/40 dark:text-blue-300">
            <ShieldCheck size={17} />
            Intelligent market analysis
          </div>

          <h1 className="max-w-xl text-5xl font-bold leading-tight tracking-tight">
            Understand the market.
            <span className="text-blue-600"> Trade with insight.</span>
          </h1>

          <p className="mt-6 max-w-lg text-lg leading-8 text-slate-600 dark:text-slate-400">
            Analyse forex market conditions, understand
            multi-timeframe trends and receive AI-assisted
            insights with human confirmation.
          </p>

          <div className="mt-10 grid max-w-lg grid-cols-2 gap-4">
            {[
              'Multi-timeframe analysis',
              'Technical indicators',
              'AI-assisted insights',
              'Risk-aware scenarios',
            ].map((item) => (
              <div
                key={item}
                className="rounded-xl border border-slate-200 bg-white p-4 text-sm dark:border-slate-800 dark:bg-slate-900"
              >
                <ShieldCheck
                  size={18}
                  className="mb-3 text-blue-600"
                />
                {item}
              </div>
            ))}
          </div>
        </div>

        <div className="mx-auto w-full max-w-md">
          <div className="mb-8">
            <h2 className="text-3xl font-bold tracking-tight">
              {heading}
            </h2>
            <p className="mt-2 text-sm leading-6 text-slate-500 dark:text-slate-400">
              {description}
            </p>
          </div>

          {children}

          <p className="mt-8 text-center text-xs text-slate-500 dark:text-slate-500">
            LovetechCyber AI Forex Analyst
            <span className="mx-2">·</span>
            Analysis only, not automated trading
          </p>
        </div>
      </section>
    </main>
  )
}
