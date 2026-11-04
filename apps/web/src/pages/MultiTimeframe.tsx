
import { useCallback, useState } from 'react'
import {
  Activity,
  AlertCircle,
  ArrowDown,
  ArrowUp,
  BarChart3,
  CheckCircle2,
  Clock,
  Layers3,
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

type DataRecord = Record<string, unknown>

function asRecord(value: unknown): DataRecord | null {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) {
    return null
  }
  return value as DataRecord
}

function findTimeframeData(data: unknown): DataRecord[] {
  if (Array.isArray(data)) {
    return data.map(asRecord).filter((item): item is DataRecord => item !== null)
  }

  const record = asRecord(data)
  if (!record) return []

  for (const key of [
    'timeframes',
    'results',
    'analysis',
    'data',
    'timeframe_analysis',
  ]) {
    const value = record[key]

    if (Array.isArray(value)) {
      return value
        .map(asRecord)
        .filter((item): item is DataRecord => item !== null)
    }

    const nested = asRecord(value)
    if (nested) {
      return Object.entries(nested).map(([timeframe, result]) => ({
        timeframe,
        ...(asRecord(result) ?? { result }),
      }))
    }
  }

  return []
}

function getText(
  record: DataRecord,
  keys: string[],
  fallback = 'Not available',
): string {
  for (const key of keys) {
    const value = record[key]
    if (typeof value === 'string' || typeof value === 'number') {
      return String(value)
    }
  }
  return fallback
}

function getSignalColor(signal: string) {
  const value = signal.toLowerCase()

  if (
    value.includes('bull') ||
    value.includes('buy') ||
    value.includes('uptrend')
  ) {
    return 'text-emerald-600 bg-emerald-50 dark:bg-emerald-950/30 dark:text-emerald-400'
  }

  if (
    value.includes('bear') ||
    value.includes('sell') ||
    value.includes('downtrend')
  ) {
    return 'text-red-600 bg-red-50 dark:bg-red-950/30 dark:text-red-400'
  }

  return 'text-amber-600 bg-amber-50 dark:bg-amber-950/30 dark:text-amber-400'
}

function ResultValue({ value }: { value: unknown }) {
  if (value === null || value === undefined) {
    return <span className="text-slate-400">Not available</span>
  }

  if (typeof value === 'object') {
    if (Array.isArray(value)) {
      return (
        <div className="space-y-2">
          {value.map((item, index) => (
            <div key={index}>
              <ResultValue value={item} />
            </div>
          ))}
        </div>
      )
    }

    return (
      <div className="space-y-2">
        {Object.entries(value as DataRecord).map(([key, item]) => (
          <div
            key={key}
            className="flex flex-col justify-between gap-1 border-b border-slate-100 pb-2 last:border-0 dark:border-slate-800 sm:flex-row"
          >
            <span className="text-xs text-slate-500">
              {key.replace(/_/g, ' ')}
            </span>
            <span className="text-sm font-medium sm:text-right">
              <ResultValue value={item} />
            </span>
          </div>
        ))}
      </div>
    )
  }

  return <span>{String(value)}</span>
}

export default function MultiTimeframe() {
  const [symbol, setSymbol] = useState('EURUSD')
  const [limit, setLimit] = useState(200)
  const [minimumCandles, setMinimumCandles] = useState(50)
  const [selectedFrames, setSelectedFrames] = useState<string[]>([
    ...TIMEFRAMES,
  ])

  const [result, setResult] = useState<unknown>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)

  const runAnalysis = useCallback(async () => {
    setLoading(true)
    setError('')
    setResult(null)

    try {
      const response = await analysisAPI.multiTimeframe(
        symbol,
        limit,
      )

      setResult(response)
      setLastUpdated(new Date())
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Unable to retrieve multi-timeframe analysis.',
      )
    } finally {
      setLoading(false)
    }
  }, [symbol, limit])

  const timeframeResults = findTimeframeData(result)

  const toggleTimeframe = (timeframe: string) => {
    setSelectedFrames((current) =>
      current.includes(timeframe)
        ? current.filter((item) => item !== timeframe)
        : [...current, timeframe],
    )
  }

  const displayedResults = timeframeResults.filter((item) => {
    const frame = getText(item, ['timeframe', 'interval', 'period'], '')
    return !frame || selectedFrames.includes(frame.toUpperCase())
  })

  return (
    <div className="min-h-screen bg-slate-50 p-4 text-slate-900 dark:bg-[#080f1c] dark:text-slate-100 md:p-8">
      <div className="mx-auto max-w-7xl space-y-6">
        <header>
          <div className="flex items-center gap-3">
            <div className="rounded-xl bg-blue-600 p-3 text-white">
              <Layers3 size={24} />
            </div>
            <div>
              <h1 className="text-2xl font-bold">Multi-Timeframe Analysis</h1>
              <p className="text-sm text-slate-500">
                Compare market conditions across multiple timeframes.
              </p>
            </div>
          </div>
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
              <span className="text-slate-500">Candle history limit</span>
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

            <label className="space-y-2 text-sm">
              <span className="text-slate-500">Minimum candles required</span>
              <select
                value={minimumCandles}
                onChange={(event) => setMinimumCandles(Number(event.target.value))}
                className="w-full rounded-lg border border-slate-200 bg-white px-3 py-3 dark:border-slate-700 dark:bg-slate-900"
              >
                <option value={30}>30 candles</option>
                <option value={50}>50 candles</option>
                <option value={100}>100 candles</option>
              </select>
            </label>
          </div>

          <div className="mt-5">
            <p className="mb-3 text-sm font-medium">Display timeframes</p>
            <div className="flex flex-wrap gap-2">
              {TIMEFRAMES.map((frame) => (
                <button
                  key={frame}
                  type="button"
                  onClick={() => toggleTimeframe(frame)}
                  className={`rounded-lg border px-4 py-2 text-sm font-medium ${
                    selectedFrames.includes(frame)
                      ? 'border-blue-600 bg-blue-600 text-white'
                      : 'border-slate-200 text-slate-500 dark:border-slate-700'
                  }`}
                >
                  {frame}
                </button>
              ))}
            </div>
          </div>

          <button
            onClick={() => void runAnalysis()}
            disabled={loading || selectedFrames.length === 0}
            className="mt-6 flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-5 py-3 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50 sm:w-auto"
          >
            {loading ? (
              <RefreshCw size={17} className="animate-spin" />
            ) : (
              <Activity size={17} />
            )}
            {loading ? 'Analyzing timeframes...' : 'Run multi-timeframe analysis'}
          </button>
        </section>

        {error && (
          <div className="flex gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-900 dark:bg-red-950/30 dark:text-red-300">
            <AlertCircle size={19} className="shrink-0" />
            {error}
          </div>
        )}

        {loading && (
          <div className="flex items-center justify-center gap-3 rounded-xl border border-slate-200 bg-white p-12 text-sm text-slate-500 dark:border-slate-800 dark:bg-[#0d1728]">
            <RefreshCw size={20} className="animate-spin" />
            Comparing market conditions across timeframes...
          </div>
        )}

        {!loading && result !== null && (
          <>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="text-xl font-bold">{symbol} timeframe results</h2>
                <p className="text-sm text-slate-500">
                  Backend analysis response
                </p>
              </div>
              <span className="text-xs text-slate-500">
                {lastUpdated?.toLocaleTimeString()}
              </span>
            </div>

            {displayedResults.length > 0 ? (
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                {displayedResults.map((item, index) => {
                  const frame = getText(
                    item,
                    ['timeframe', 'interval', 'period'],
                    `Result ${index + 1}`,
                  )

                  const signal = getText(
                    item,
                    ['signal', 'trend', 'direction', 'bias'],
                  )

                  return (
                    <section
                      key={`${frame}-${index}`}
                      className="rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-[#0d1728]"
                    >
                      <div className="mb-4 flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Clock size={18} className="text-blue-500" />
                          <h3 className="font-bold">{frame}</h3>
                        </div>
                        <span className={`rounded-full px-3 py-1 text-xs font-semibold ${getSignalColor(signal)}`}>
                          {signal}
                        </span>
                      </div>

                      <ResultValue value={item} />
                    </section>
                  )
                })}
              </div>
            ) : (
              <section className="rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-[#0d1728]">
                <h3 className="mb-3 font-semibold">Complete backend response</h3>
                <ResultValue value={result} />
                <p className="mt-4 text-xs text-slate-500">
                  The response structure will be mapped into individual
                  timeframe cards once the exact backend schema is confirmed.
                </p>
              </section>
            )}

            <section className="rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-[#0d1728]">
              <div className="mb-4 flex items-center gap-2">
                <CheckCircle2 size={20} className="text-blue-500" />
                <h3 className="font-semibold">Raw analysis summary</h3>
              </div>
              <ResultValue value={result} />
            </section>
          </>
        )}

        {!loading && result === null && !error && (
          <section className="rounded-2xl border border-dashed border-slate-300 bg-white p-12 text-center dark:border-slate-700 dark:bg-[#0d1728]">
            <BarChart3 size={36} className="mx-auto mb-3 text-blue-500" />
            <h3 className="font-semibold">Multi-timeframe workspace ready</h3>
            <p className="mx-auto mt-2 max-w-md text-sm text-slate-500">
              Choose a pair and configure your analysis. Your backend will
              evaluate the available timeframe data.
            </p>
          </section>
        )}

        <div className="flex gap-3 rounded-xl border border-blue-100 bg-blue-50 p-4 text-sm text-blue-800 dark:border-blue-900/50 dark:bg-blue-950/30 dark:text-blue-300">
          <ShieldCheck size={19} className="shrink-0" />
          <p>
            Multi-timeframe confirmation is analytical information, not a
            guarantee of future market direction. Review all results before
            making trading decisions.
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs text-slate-500">
          <ArrowUp size={14} />
          <ArrowDown size={14} />
          Trend direction and confirmation will be interpreted from actual
          backend results.
        </div>
      </div>
    </div>
  )
}
