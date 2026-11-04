
import { useCallback, useState } from 'react'
import {
  Activity,
  AlertCircle,
  BarChart3,
  BrainCircuit,
  RefreshCw,
  ShieldCheck,
} from 'lucide-react'
import { analysisAPI } from '../service/api'

const SYMBOLS = [
  'EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF',
  'AUDUSD', 'USDCAD', 'NZDUSD', 'EURJPY',
  'GBPJPY', 'XAUUSD',
]

const TIMEFRAMES = ['M5', 'M15', 'M30', 'H1', 'H4', 'D1']

type AnalysisResult = {
  indicators: unknown
  unified: unknown
}

function formatLabel(value: string) {
  return value
    .replace(/_/g, ' ')
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function ValueDisplay({ value }: { value: unknown }) {
  if (value === null || value === undefined) {
    return <span className="text-slate-400">Not available</span>
  }

  if (typeof value === 'boolean') {
    return <span>{value ? 'Yes' : 'No'}</span>
  }

  if (typeof value === 'number') {
    return <span>{Number.isFinite(value) ? value.toLocaleString() : '—'}</span>
  }

  if (typeof value === 'string') {
    return <span className="break-words">{value}</span>
  }

  if (Array.isArray(value)) {
    if (value.length === 0) {
      return <span className="text-slate-400">No data</span>
    }

    return (
      <div className="space-y-2">
        {value.map((item, index) => (
          <div
            key={index}
            className="rounded-lg bg-slate-50 p-3 dark:bg-slate-900"
          >
            <ValueDisplay value={item} />
          </div>
        ))}
      </div>
    )
  }

  if (typeof value === 'object') {
    return (
      <div className="space-y-3">
        {Object.entries(value as Record<string, unknown>).map(([key, item]) => (
          <div
            key={key}
            className="grid gap-1 border-b border-slate-100 pb-2 last:border-0 dark:border-slate-800 sm:grid-cols-[160px_minmax(0,1fr)]"
          >
            <span className="text-xs font-medium text-slate-500">
              {formatLabel(key)}
            </span>
            <div className="min-w-0 text-sm">
              <ValueDisplay value={item} />
            </div>
          </div>
        ))}
      </div>
    )
  }

  return <span>{String(value)}</span>
}

function ResultCard({
  title,
  icon,
  data,
}: {
  title: string
  icon: React.ReactNode
  data: unknown
}) {
  const hasData =
    data !== null &&
    data !== undefined &&
    (typeof data !== 'object' || Object.keys(data).length > 0)

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-[#0d1728]">
      <div className="mb-5 flex items-center gap-3">
        <span className="rounded-lg bg-blue-50 p-2 text-blue-600 dark:bg-blue-950/50 dark:text-blue-400">
          {icon}
        </span>
        <h3 className="font-semibold">{title}</h3>
      </div>

      {hasData ? (
        <ValueDisplay value={data} />
      ) : (
        <p className="text-sm text-slate-500">
          No analysis data has been returned yet.
        </p>
      )}
    </section>
  )
}

export default function Analysis() {
  const [symbol, setSymbol] = useState('EURUSD')
  const [timeframe, setTimeframe] = useState('H1')
  const [limit, setLimit] = useState(200)

  const [results, setResults] = useState<AnalysisResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)

  const runAnalysis = useCallback(async () => {
    setLoading(true)
    setError('')
    setResults(null)

    try {
      const [indicators, unified] = await Promise.all([
        analysisAPI.indicators(symbol, timeframe, limit),
        analysisAPI.unified(symbol, timeframe, limit),
      ])

      setResults({ indicators, unified })
      setLastUpdated(new Date())
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Unable to complete market analysis.',
      )
    } finally {
      setLoading(false)
    }
  }, [symbol, timeframe, limit])

  return (
    <div className="min-h-screen bg-slate-50 p-4 text-slate-900 dark:bg-[#080f1c] dark:text-slate-100 md:p-8">
      <div className="mx-auto max-w-7xl space-y-6">
        <header>
          <div className="flex items-center gap-3">
            <div className="rounded-xl bg-blue-600 p-3 text-white">
              <Activity size={24} />
            </div>
            <div>
              <h1 className="text-2xl font-bold">Technical Analysis</h1>
              <p className="text-sm text-slate-500">
                Analyze market conditions using your existing analysis engine.
              </p>
            </div>
          </div>
        </header>

        <section className="rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-[#0d1728]">
          <h2 className="mb-4 font-semibold">Analysis configuration</h2>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
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
              <span className="text-slate-500">Timeframe</span>
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
              <span className="text-slate-500">Candle history</span>
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

            <div className="flex items-end">
              <button
                onClick={() => void runAnalysis()}
                disabled={loading}
                className="flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-3 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-60"
              >
                {loading ? (
                  <RefreshCw size={17} className="animate-spin" />
                ) : (
                  <BarChart3 size={17} />
                )}
                {loading ? 'Analyzing...' : 'Run analysis'}
              </button>
            </div>
          </div>
        </section>

        {error && (
          <div className="flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-900 dark:bg-red-950/30 dark:text-red-300">
            <AlertCircle size={19} className="mt-0.5 shrink-0" />
            <div>
              <p className="font-semibold">Analysis failed</p>
              <p className="mt-1">{error}</p>
            </div>
          </div>
        )}

        {loading && (
          <div className="flex items-center justify-center gap-3 rounded-xl border border-slate-200 bg-white p-12 text-sm text-slate-500 dark:border-slate-800 dark:bg-[#0d1728]">
            <RefreshCw size={20} className="animate-spin" />
            Retrieving indicators and unified market analysis...
          </div>
        )}

        {!loading && results && (
          <>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="text-xl font-bold">
                  {symbol} · {timeframe}
                </h2>
                <p className="text-sm text-slate-500">
                  Analysis results returned by the backend
                </p>
              </div>
              <span className="text-xs text-slate-500">
                Updated {lastUpdated?.toLocaleTimeString()}
              </span>
            </div>

            <ResultCard
              title="Technical indicators"
              icon={<BarChart3 size={20} />}
              data={results.indicators}
            />

            <ResultCard
              title="Unified market analysis"
              icon={<Activity size={20} />}
              data={results.unified}
            />
          </>
        )}

        {!loading && !results && !error && (
          <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-12 text-center dark:border-slate-700 dark:bg-[#0d1728]">
            <BrainCircuit size={36} className="mx-auto mb-3 text-blue-500" />
            <h3 className="font-semibold">Ready to analyze the market</h3>
            <p className="mx-auto mt-2 max-w-md text-sm text-slate-500">
              Select a currency pair and timeframe, then run analysis to
              retrieve real technical indicators and market insights.
            </p>
          </div>
        )}

        <div className="flex items-start gap-3 rounded-xl border border-blue-100 bg-blue-50 p-4 text-sm text-blue-800 dark:border-blue-900/50 dark:bg-blue-950/30 dark:text-blue-300">
          <ShieldCheck size={19} className="mt-0.5 shrink-0" />
          <p>
            This application provides market analysis, not automatic trade
            execution. Review results independently before making trading
            decisions.
          </p>
        </div>
      </div>
    </div>
  )
}
