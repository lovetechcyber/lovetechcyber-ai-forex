
import { useState } from 'react'
import {
  Activity,
  AlertTriangle,
  BrainCircuit,
  CheckCircle2,
  Clock,
  Lightbulb,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  TrendingDown,
  TrendingUp,
} from 'lucide-react'

import { analysisAPI } from '../service/api'

const SYMBOLS = [
  'EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF',
  'AUDUSD', 'USDCAD', 'NZDUSD', 'EURJPY',
  'GBPJPY', 'XAUUSD',
]

const TIMEFRAMES = ['M5', 'M15', 'M30', 'H1', 'H4', 'D1']

type RecordData = Record<string, unknown>

function asRecord(value: unknown): RecordData | null {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) {
    return null
  }
  return value as RecordData
}

function findValue(
  data: unknown,
  keys: string[],
  fallback = 'Not provided by AI',
): unknown {
  const record = asRecord(data)
  if (!record) return fallback

  for (const key of keys) {
    if (record[key] !== undefined && record[key] !== null) {
      return record[key]
    }
  }

  return fallback
}

function formatLabel(value: string) {
  return value
    .replace(/_/g, ' ')
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function DisplayValue({ value }: { value: unknown }) {
  if (value === null || value === undefined) {
    return <span className="text-slate-400">Not provided</span>
  }

  if (typeof value === 'boolean' || typeof value === 'number') {
    return <span>{String(value)}</span>
  }

  if (typeof value === 'string') {
    return <span className="whitespace-pre-wrap break-words">{value}</span>
  }

  if (Array.isArray(value)) {
    if (value.length === 0) {
      return <span className="text-slate-400">No items returned</span>
    }

    return (
      <ul className="space-y-2">
        {value.map((item, index) => (
          <li
            key={index}
            className="flex items-start gap-2 rounded-lg bg-slate-50 p-3 text-sm dark:bg-slate-900"
          >
            <span className="mt-1 text-blue-500">•</span>
            <DisplayValue value={item} />
          </li>
        ))}
      </ul>
    )
  }

  if (typeof value === 'object') {
    return (
      <div className="space-y-3">
        {Object.entries(value as RecordData).map(([key, item]) => (
          <div
            key={key}
            className="border-b border-slate-100 pb-3 last:border-0 dark:border-slate-800"
          >
            <p className="mb-1 text-xs font-semibold text-slate-500">
              {formatLabel(key)}
            </p>
            <div className="text-sm">
              <DisplayValue value={item} />
            </div>
          </div>
        ))}
      </div>
    )
  }

  return <span>{String(value)}</span>
}

function InsightCard({
  title,
  icon,
  value,
}: {
  title: string
  icon: React.ReactNode
  value: unknown
}) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-[#0d1728]">
      <div className="mb-4 flex items-center gap-3">
        <span className="rounded-lg bg-blue-50 p-2 text-blue-600 dark:bg-blue-950/50 dark:text-blue-400">
          {icon}
        </span>
        <h3 className="font-semibold">{title}</h3>
      </div>
      <DisplayValue value={value} />
    </section>
  )
}

function getBiasColor(bias: string) {
  const value = bias.toLowerCase()

  if (value.includes('bull') || value.includes('buy')) {
    return 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-400'
  }

  if (value.includes('bear') || value.includes('sell')) {
    return 'bg-red-50 text-red-700 dark:bg-red-950/30 dark:text-red-400'
  }

  return 'bg-amber-50 text-amber-700 dark:bg-amber-950/30 dark:text-amber-400'
}

export default function AIAnalyst() {
  const [symbol, setSymbol] = useState('EURUSD')
  const [timeframe, setTimeframe] = useState('H1')
  const [limit, setLimit] = useState(200)
  const [includeMultiTimeframe, setIncludeMultiTimeframe] = useState(true)

  const [analysis, setAnalysis] = useState<unknown>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)

  const runAIAnalysis = async () => {
    setLoading(true)
    setError('')
    setAnalysis(null)

    try {
      const unified = await analysisAPI.unified(
        symbol,
        timeframe,
        limit,
      )

      let multiTimeframe: unknown = null

      if (includeMultiTimeframe) {
        multiTimeframe = await analysisAPI.multiTimeframe(
          symbol,
          limit,
        )
      }

      const response = await analysisAPI.ai({
        market_analysis: asRecord(unified) ?? { result: unified },
        multi_timeframe_analysis: includeMultiTimeframe
          ? asRecord(multiTimeframe) ?? { result: multiTimeframe }
          : null,
      })

      setAnalysis(response)
      setLastUpdated(new Date())
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'AI analysis could not be completed.',
      )
    } finally {
      setLoading(false)
    }
  }

  const bias = String(
    findValue(
      analysis,
      ['bias', 'market_bias', 'directional_bias', 'direction'],
      'Not determined',
    ),
  )

  const confidence = findValue(
    analysis,
    ['confidence', 'confidence_score', 'confidence_level'],
    undefined,
  )

  const summary = findValue(
    analysis,
    ['summary', 'market_summary', 'analysis', 'overview', 'interpretation'],
  )

  const evidence = findValue(
    analysis,
    ['evidence', 'supporting_evidence', 'reasons', 'key_factors'],
  )

  const risks = findValue(
    analysis,
    ['risks', 'risk_factors', 'warnings', 'cautions'],
  )

  const recommendations = findValue(
    analysis,
    ['recommendations', 'suggestions', 'action_plan', 'next_steps'],
  )

  return (
    <div className="min-h-screen bg-slate-50 p-4 text-slate-900 dark:bg-[#080f1c] dark:text-slate-100 md:p-8">
      <div className="mx-auto max-w-7xl space-y-6">
        <header className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div className="flex items-center gap-3">
            <div className="rounded-xl bg-blue-600 p-3 text-white">
              <BrainCircuit size={25} />
            </div>
            <div>
              <h1 className="text-2xl font-bold">AI Forex Analyst</h1>
              <p className="text-sm text-slate-500">
                AI-assisted market interpretation and decision support.
              </p>
            </div>
          </div>
          <span className="inline-flex w-fit items-center gap-2 rounded-full bg-blue-50 px-3 py-2 text-xs font-semibold text-blue-700 dark:bg-blue-950/40 dark:text-blue-300">
            <Sparkles size={15} />
            AI intelligence
          </span>
        </header>

        <section className="rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-[#0d1728]">
          <h2 className="mb-4 font-semibold">Analysis configuration</h2>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <label className="space-y-2 text-sm">
              <span className="text-slate-500">Currency pair</span>
              <select
                value={symbol}
                onChange={(event) => setSymbol(event.target.value)}
                className="w-full rounded-lg border border-slate-200 bg-white px-3 py-3 dark:border-slate-700 dark:bg-slate-900"
              >
                {SYMBOLS.map((item) => (
                  <option key={item} value={item}>{item}</option>
                ))}
              </select>
            </label>

            <label className="space-y-2 text-sm">
              <span className="text-slate-500">Primary timeframe</span>
              <select
                value={timeframe}
                onChange={(event) => setTimeframe(event.target.value)}
                className="w-full rounded-lg border border-slate-200 bg-white px-3 py-3 dark:border-slate-700 dark:bg-slate-900"
              >
                {TIMEFRAMES.map((item) => (
                  <option key={item} value={item}>{item}</option>
                ))}
              </select>
            </label>

            <label className="space-y-2 text-sm">
              <span className="text-slate-500">Market history</span>
              <select
                value={limit}
                onChange={(event) => setLimit(Number(event.target.value))}
                className="w-full rounded-lg border border-slate-200 bg-white px-3 py-3 dark:border-slate-700 dark:bg-slate-900"
              >
                <option value={100}>100 candles</option>
                <option value={200}>200 candles</option>
                <option value={300}>300 candles</option>
                <option value={500}>500 candles</option>
              </select>
            </label>
          </div>

          <label className="mt-5 flex cursor-pointer items-start gap-3 text-sm">
            <input
              type="checkbox"
              checked={includeMultiTimeframe}
              onChange={(event) => setIncludeMultiTimeframe(event.target.checked)}
              className="mt-1 h-4 w-4 accent-blue-600"
            />
            <span>
              <span className="font-medium">Include multi-timeframe context</span>
              <span className="mt-1 block text-xs text-slate-500">
                Provide the AI with the multi-timeframe analysis alongside
                unified market analysis.
              </span>
            </span>
          </label>

          <button
            onClick={() => void runAIAnalysis()}
            disabled={loading}
            className="mt-6 flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-5 py-3 font-semibold text-white hover:bg-blue-700 disabled:opacity-60 sm:w-auto"
          >
            {loading ? (
              <RefreshCw size={18} className="animate-spin" />
            ) : (
              <BrainCircuit size={18} />
            )}
            {loading ? 'AI is analyzing...' : 'Generate AI analysis'}
          </button>
        </section>

        {error && (
          <div className="flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-900 dark:bg-red-950/30 dark:text-red-300">
            <AlertTriangle size={19} className="mt-0.5 shrink-0" />
            <div>
              <p className="font-semibold">AI analysis failed</p>
              <p className="mt-1">{error}</p>
            </div>
          </div>
        )}

        {loading && (
          <div className="rounded-2xl border border-slate-200 bg-white p-12 text-center dark:border-slate-800 dark:bg-[#0d1728]">
            <BrainCircuit size={36} className="mx-auto mb-4 animate-pulse text-blue-500" />
            <h3 className="font-semibold">Analyzing market conditions</h3>
            <p className="mt-2 text-sm text-slate-500">
              Collecting analysis context and generating AI insights.
            </p>
          </div>
        )}

        {!loading && analysis !== null && (
          <>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="text-xl font-bold">{symbol} AI assessment</h2>
                <p className="text-sm text-slate-500">
                  Primary timeframe: {timeframe}
                </p>
              </div>
              <span className="flex items-center gap-2 text-xs text-slate-500">
                <Clock size={14} />
                {lastUpdated?.toLocaleTimeString()}
              </span>
            </div>

            <section className="grid gap-4 sm:grid-cols-2">
              <div className="rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-[#0d1728]">
                <p className="text-sm text-slate-500">AI directional bias</p>
                <div className="mt-3 flex items-center gap-3">
                  <span className={`rounded-xl p-3 ${getBiasColor(bias)}`}>
                    {bias.toLowerCase().includes('bear')
                      ? <TrendingDown size={24} />
                      : <TrendingUp size={24} />}
                  </span>
                  <h3 className="text-xl font-bold">{bias}</h3>
                </div>
              </div>

              <div className="rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-[#0d1728]">
                <p className="text-sm text-slate-500">AI confidence</p>
                <p className="mt-3 text-2xl font-bold">
                  {confidence === null
                    ? 'Not provided'
                    : typeof confidence === 'number'
                      ? `${confidence}${confidence <= 1 ? '%' : ''}`
                      : String(confidence)}
                </p>
                <p className="mt-2 text-xs text-slate-500">
                  Confidence is shown as returned by the AI service.
                </p>
              </div>
            </section>

            <InsightCard
              title="AI market interpretation"
              icon={<Lightbulb size={20} />}
              value={summary}
            />

            <div className="grid gap-4 xl:grid-cols-2">
              <InsightCard
                title="Supporting evidence"
                icon={<CheckCircle2 size={20} />}
                value={evidence}
              />

              <InsightCard
                title="Risk factors and warnings"
                icon={<AlertTriangle size={20} />}
                value={risks}
              />
            </div>

            <InsightCard
              title="AI suggestions"
              icon={<BrainCircuit size={20} />}
              value={recommendations}
            />

            <InsightCard
              title="Complete AI response"
              icon={<Activity size={20} />}
              value={analysis}
            />
          </>
        )}

        {!loading && analysis === null && !error && (
          <section className="rounded-2xl border border-dashed border-slate-300 bg-white p-12 text-center dark:border-slate-700 dark:bg-[#0d1728]">
            <BrainCircuit size={38} className="mx-auto mb-4 text-blue-500" />
            <h3 className="font-semibold">Your AI analyst is ready</h3>
            <p className="mx-auto mt-2 max-w-md text-sm text-slate-500">
              Select your market and generate an AI assessment using the
              existing backend analysis engine.
            </p>
          </section>
        )}

        <section className="rounded-2xl border border-amber-200 bg-amber-50 p-5 dark:border-amber-900/50 dark:bg-amber-950/20">
          <div className="flex items-center gap-3">
            <ShieldCheck size={21} className="text-amber-600" />
            <h3 className="font-semibold text-amber-800 dark:text-amber-300">
              Human review required
            </h3>
          </div>
          <p className="mt-2 text-sm leading-6 text-amber-800 dark:text-amber-200">
            AI analysis is decision support, not a trading instruction.
            Review the evidence, verify market conditions and independently
            assess risk before taking any action. This application does not
            execute trades automatically.
          </p>
        </section>
      </div>
    </div>
  )
}
