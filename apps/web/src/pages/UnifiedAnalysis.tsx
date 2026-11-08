import { useCallback, useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import { Link } from "react-router-dom";
import {
  Activity,
  AlertCircle,
  ArrowLeft,
  BarChart3,
  CheckCircle2,
  Clock3,
  Play,
  RefreshCw,
  Search,
  ShieldCheck,
  TrendingDown,
  TrendingUp,
  Wifi,
  WifiOff,
} from "lucide-react";

import { marketAPI, analysisAPI } from "../service/api";
import ThemeToggle from "../components/ThemeToggle";

type Candle = {
  timestamp: string;
  timeLabel: string;
  open: number;
  high: number;
  low: number;
  close: number;
};

type AnalysisObject = Record<string, unknown>;

const TIMEFRAMES = ["M5", "M15", "M30", "H1", "H4", "D1"] as const;

const POPULAR_PAIRS = [
  "EURUSD",
  "GBPUSD",
  "USDJPY",
  "USDCHF",
  "USDCAD",
  "AUDUSD",
  "NZDUSD",
  "EURGBP",
  "EURJPY",
  "GBPJPY",
  "XAUUSD",
];

const CHART_WIDTH = 1000;
const CHART_HEIGHT = 360;
const CHART_PADDING = {
  top: 20,
  right: 75,
  bottom: 35,
  left: 15,
};

function toRecord(value: unknown): AnalysisObject | null {
  if (typeof value === "object" && value !== null && !Array.isArray(value)) {
    return value as AnalysisObject;
  }

  return null;
}

function toNumber(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }

  if (typeof value === "string" && value.trim() !== "") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }

  return null;
}

function getFirstValue(
  record: AnalysisObject,
  keys: string[],
): unknown {
  for (const key of keys) {
    if (record[key] !== undefined && record[key] !== null) {
      return record[key];
    }
  }

  return undefined;
}

function formatCandleTime(value: unknown): {
  timestamp: string;
  label: string;
} {
  let date: Date;

  if (typeof value === "number") {
    // Support Unix seconds and Unix milliseconds.
    date = new Date(value < 10_000_000_000 ? value * 1000 : value);
  } else if (typeof value === "string") {
    const numeric = Number(value);

    if (value.trim() !== "" && Number.isFinite(numeric)) {
      date = new Date(
        numeric < 10_000_000_000 ? numeric * 1000 : numeric,
      );
    } else {
      date = new Date(value);
    }
  } else {
    date = new Date();
  }

  if (Number.isNaN(date.getTime())) {
    date = new Date();
  }

  return {
    timestamp: date.toISOString(),
    label: date.toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }),
  };
}

function extractCandleArray(
  value: unknown,
  depth = 0,
): unknown[] {
  if (depth > 4 || value === null || value === undefined) {
    return [];
  }

  if (Array.isArray(value)) {
    return value;
  }

  const record = toRecord(value);

  if (!record) {
    return [];
  }

  const possibleKeys = [
    "candles",
    "data",
    "market_data",
    "results",
    "items",
    "records",
  ];

  for (const key of possibleKeys) {
    const nested = record[key];

    if (Array.isArray(nested)) {
      return nested;
    }

    if (nested && typeof nested === "object") {
      const result = extractCandleArray(nested, depth + 1);

      if (result.length > 0) {
        return result;
      }
    }
  }

  return [];
}

function normalizeCandles(response: unknown): Candle[] {
  const rawCandles = extractCandleArray(response);

  const normalized: Candle[] = [];

  for (const raw of rawCandles) {
    const record = toRecord(raw);

    if (!record) continue;

    const open = toNumber(getFirstValue(record, ["open", "Open", "o"]));
    const high = toNumber(getFirstValue(record, ["high", "High", "h"]));
    const low = toNumber(getFirstValue(record, ["low", "Low", "l"]));
    const close = toNumber(getFirstValue(record, ["close", "Close", "c"]));

    if (
      open === null ||
      high === null ||
      low === null ||
      close === null
    ) {
      continue;
    }

    const rawTime = getFirstValue(record, [
      "timestamp",
      "time",
      "datetime",
      "date",
      "Time",
    ]);

    const formattedTime = formatCandleTime(rawTime);

    normalized.push({
      timestamp: formattedTime.timestamp,
      timeLabel: formattedTime.label,
      open,
      high,
      low,
      close,
    });
  }

  return normalized.sort(
    (a, b) =>
      new Date(a.timestamp).getTime() -
      new Date(b.timestamp).getTime(),
  );
}

function formatPrice(value: number): string {
  return value.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 5,
  });
}

function formatAnalysisLabel(value: string): string {
  return value
    .replace(/[_-]/g, " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function displayValue(value: unknown): string {
  if (value === null || value === undefined) {
    return "Not available";
  }

  if (typeof value === "string") {
    return value;
  }

  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }

  return JSON.stringify(value, null, 2);
}

function CandleChart({
  candles,
}: {
  candles: Candle[];
}) {
  const visibleCandles = useMemo(
    () => candles.slice(-100),
    [candles],
  );

  if (visibleCandles.length === 0) {
    return (
      <div className="flex h-[320px] flex-col items-center justify-center text-center">
        <BarChart3 className="mb-3 text-slate-400" size={34} />
        <p className="font-semibold text-slate-700 dark:text-slate-200">
          Waiting for market candles
        </p>
        <p className="mt-2 max-w-sm text-sm text-slate-500 dark:text-slate-400">
          Your MT5 integration must send OHLC data for this pair and
          timeframe before the chart can display candles.
        </p>
      </div>
    );
  }

  const minPrice = Math.min(...visibleCandles.map((candle) => candle.low));
  const maxPrice = Math.max(...visibleCandles.map((candle) => candle.high));
  const range = maxPrice - minPrice || Math.abs(maxPrice) * 0.001 || 1;

  const chartTop = CHART_PADDING.top;
  const chartBottom = CHART_HEIGHT - CHART_PADDING.bottom;
  const chartLeft = CHART_PADDING.left;
  const chartRight = CHART_WIDTH - CHART_PADDING.right;
  const chartHeight = chartBottom - chartTop;
  const chartWidth = chartRight - chartLeft;

  const pricePadding = range * 0.08;
  const scaleMin = minPrice - pricePadding;
  const scaleMax = maxPrice + pricePadding;
  const scaleRange = scaleMax - scaleMin;

  const yPosition = (price: number) =>
    chartBottom - ((price - scaleMin) / scaleRange) * chartHeight;

  const slotWidth = chartWidth / visibleCandles.length;
  const candleWidth = Math.max(
    2,
    Math.min(12, slotWidth * 0.58),
  );

  const gridLines = Array.from({ length: 5 }, (_, index) => {
    const ratio = index / 4;
    const price = scaleMax - ratio * scaleRange;

    return {
      y: chartTop + ratio * chartHeight,
      price,
    };
  });

  const lastCandle = visibleCandles[visibleCandles.length - 1];

  return (
    <div className="w-full overflow-hidden">
      <svg
        viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`}
        className="h-auto max-h-[420px] w-full"
        role="img"
        aria-label="OHLC candlestick chart"
        preserveAspectRatio="none"
      >
        {gridLines.map((line, index) => (
          <g key={index}>
            <line
              x1={chartLeft}
              y1={line.y}
              x2={chartRight}
              y2={line.y}
              stroke="currentColor"
              strokeOpacity="0.10"
              strokeDasharray="4 6"
            />
            <text
              x={chartRight + 10}
              y={line.y + 4}
              fill="currentColor"
              fillOpacity="0.6"
              fontSize="12"
            >
              {formatPrice(line.price)}
            </text>
          </g>
        ))}

        {visibleCandles.map((candle, index) => {
          const centerX = chartLeft + slotWidth * index + slotWidth / 2;
          const bullish = candle.close >= candle.open;

          const openY = yPosition(candle.open);
          const closeY = yPosition(candle.close);
          const highY = yPosition(candle.high);
          const lowY = yPosition(candle.low);

          const bodyTop = Math.min(openY, closeY);
          const bodyHeight = Math.max(1.5, Math.abs(closeY - openY));
          const candleColor = bullish ? "#10b981" : "#ef4444";

          return (
            <g key={`${candle.timestamp}-${index}`}>
              <title>
                {`${candle.timeLabel} | O: ${candle.open} H: ${candle.high} L: ${candle.low} C: ${candle.close}`}
              </title>

              <line
                x1={centerX}
                y1={highY}
                x2={centerX}
                y2={lowY}
                stroke={candleColor}
                strokeWidth="1.5"
              />

              <rect
                x={centerX - candleWidth / 2}
                y={bodyTop}
                width={candleWidth}
                height={bodyHeight}
                rx="1"
                fill={candleColor}
              />
            </g>
          );
        })}

        <line
          x1={chartLeft}
          y1={chartBottom}
          x2={chartRight}
          y2={chartBottom}
          stroke="currentColor"
          strokeOpacity="0.2"
        />

        <text
          x={chartLeft}
          y={CHART_HEIGHT - 10}
          fill="currentColor"
          fillOpacity="0.6"
          fontSize="12"
        >
          {visibleCandles[0]?.timeLabel}
        </text>

        <text
          x={chartRight}
          y={CHART_HEIGHT - 10}
          fill="currentColor"
          fillOpacity="0.6"
          fontSize="12"
          textAnchor="end"
        >
          {lastCandle?.timeLabel}
        </text>
      </svg>
    </div>
  );
}

function AnalysisResult({
  result,
}: {
  result: AnalysisObject;
}) {
  const entries = Object.entries(result);

  if (entries.length === 0) {
    return (
      <p className="text-sm text-slate-500 dark:text-slate-400">
        The analysis engine returned no displayable fields.
      </p>
    );
  }

  return (
    <div className="grid gap-4 md:grid-cols-2">
      {entries.map(([key, value]) => {
        const isLongValue =
          typeof value === "object" && value !== null;

        return (
          <article
            key={key}
            className="min-w-0 rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-950/60"
          >
            <h3 className="mb-3 text-sm font-semibold text-blue-600 dark:text-blue-400">
              {formatAnalysisLabel(key)}
            </h3>

            {isLongValue ? (
              <pre className="max-h-[360px] overflow-auto whitespace-pre-wrap break-words text-xs leading-6 text-slate-600 dark:text-slate-300">
                {displayValue(value)}
              </pre>
            ) : (
              <p className="whitespace-pre-wrap break-words text-sm leading-6 text-slate-700 dark:text-slate-300">
                {displayValue(value)}
              </p>
            )}
          </article>
        );
      })}
    </div>
  );
}

export default function UnifiedAnalysis() {
  const [symbol, setSymbol] = useState("EURUSD");
  const [customSymbol, setCustomSymbol] = useState("");
  const [timeframe, setTimeframe] =
    useState<(typeof TIMEFRAMES)[number]>("H1");
  const [limit, setLimit] = useState(500);

  const [candles, setCandles] = useState<Candle[]>([]);
  const [marketLoading, setMarketLoading] = useState(true);
  const [marketError, setMarketError] = useState("");
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const [analysis, setAnalysis] = useState<AnalysisObject | null>(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [analysisError, setAnalysisError] = useState("");
  const [analysisCompletedAt, setAnalysisCompletedAt] =
    useState<Date | null>(null);

  const selectedSymbol = symbol.trim().toUpperCase();

  const loadMarketData = useCallback(
    async (showLoading = false) => {
      if (showLoading) setMarketLoading(true);

      setMarketError("");

      try {
        const response = await marketAPI.latest(
          selectedSymbol,
          timeframe,
          limit,
        );

        const normalized = normalizeCandles(response);

        setCandles(normalized);
        setLastUpdated(new Date());

        if (normalized.length === 0) {
          setMarketError(
            "No valid OHLC candles were returned for this pair and timeframe.",
          );
        }
      } catch (error) {
        setMarketError(
          error instanceof Error
            ? error.message
            : "Unable to retrieve market data.",
        );
      } finally {
        if (showLoading) setMarketLoading(false);
      }
    },
    [selectedSymbol, timeframe, limit],
  );

  useEffect(() => {
    let active = true;

    async function initialLoad() {
      setMarketLoading(true);
      setMarketError("");

      try {
        const response = await marketAPI.latest(
          selectedSymbol,
          timeframe,
          limit,
        );

        if (!active) return;

        const normalized = normalizeCandles(response);
        setCandles(normalized);
        setLastUpdated(new Date());

        if (normalized.length === 0) {
          setMarketError(
            "No valid OHLC candles were returned for this pair and timeframe.",
          );
        }
      } catch (error) {
        if (!active) return;

        setMarketError(
          error instanceof Error
            ? error.message
            : "Unable to retrieve market data.",
        );
      } finally {
        if (active) setMarketLoading(false);
      }
    }

    void initialLoad();

    const interval = window.setInterval(() => {
      if (active) {
        void loadMarketData(false);
      }
    }, 10_000);

    return () => {
      active = false;
      window.clearInterval(interval);
    };
  }, [selectedSymbol, timeframe, limit, loadMarketData]);

  const runUnifiedAnalysis = async () => {
    setAnalysisLoading(true);
    setAnalysisError("");
    setAnalysis(null);

    try {
      const response = await analysisAPI.unified(
        selectedSymbol,
        timeframe,
        limit,
      );

      const responseRecord = toRecord(response);
      const analysisResult = responseRecord
        ? toRecord(responseRecord.analysis) ?? responseRecord
        : null;

      if (!analysisResult) {
        throw new Error("The analysis endpoint returned an invalid result.");
      }

      setAnalysis(analysisResult);
      setAnalysisCompletedAt(new Date());
    } catch (error) {
      setAnalysisError(
        error instanceof Error
          ? error.message
          : "Unified analysis could not be completed.",
      );
    } finally {
      setAnalysisLoading(false);
    }
  };

  const handlePairSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const nextSymbol = customSymbol.trim().toUpperCase();

    if (!/^[A-Z0-9._-]{3,30}$/.test(nextSymbol)) {
      setMarketError("Enter a valid broker-supported symbol.");
      return;
    }

    setSymbol(nextSymbol);
    setCustomSymbol("");
    setAnalysis(null);
    setAnalysisError("");
  };

  const lastCandle = candles[candles.length - 1];
  const previousCandle = candles[candles.length - 2];

  const priceChange =
    lastCandle && previousCandle
      ? lastCandle.close - previousCandle.close
      : null;

  const isPriceUp = priceChange !== null && priceChange >= 0;

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 transition-colors dark:bg-[#080f1d] dark:text-white">
      <div className="mx-auto max-w-[1600px] px-4 py-5 sm:px-6 lg:px-8">
        <header className="mb-7 flex flex-wrap items-center justify-between gap-4">
          <div>
            <Link
              to="/dashboard"
              className="mb-4 inline-flex items-center gap-2 text-sm text-slate-500 transition hover:text-blue-600 dark:text-slate-400 dark:hover:text-blue-400"
            >
              <ArrowLeft size={16} />
              Back to dashboard
            </Link>

            <div className="flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-blue-600/10 text-blue-600 dark:text-blue-400">
                <Activity size={25} />
              </div>

              <div>
                <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">
                  Unified Market Analysis
                </h1>
                <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                  Market data, technical indicators and market structure in
                  one workspace.
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="hidden items-center gap-2 rounded-xl border border-emerald-500/20 bg-emerald-500/5 px-3 py-2 text-xs font-semibold text-emerald-600 dark:text-emerald-400 sm:flex">
              <ShieldCheck size={15} />
              Analysis only
            </div>
            <ThemeToggle />
          </div>
        </header>

        <section className="mb-6 rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900 sm:p-5">
          <div className="mb-4 flex items-center gap-2">
            <Search size={17} className="text-blue-500" />
            <h2 className="font-semibold">Market selection</h2>
          </div>

          <div className="grid gap-4 lg:grid-cols-[1.2fr_1fr_1fr_auto] lg:items-end">
            <div>
              <label
                htmlFor="pair"
                className="mb-2 block text-xs font-semibold text-slate-500 dark:text-slate-400"
              >
                Currency pair / symbol
              </label>

              <select
                id="pair"
                value={POPULAR_PAIRS.includes(symbol) ? symbol : "CUSTOM"}
                onChange={(event) => {
                  if (event.target.value !== "CUSTOM") {
                    setSymbol(event.target.value);
                    setAnalysis(null);
                    setAnalysisError("");
                  }
                }}
                className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-3 text-sm font-semibold outline-none transition focus:border-blue-500 dark:border-slate-700 dark:bg-slate-950"
              >
                {POPULAR_PAIRS.map((pair) => (
                  <option key={pair} value={pair}>
                    {pair}
                  </option>
                ))}
                {!POPULAR_PAIRS.includes(symbol) && (
                  <option value="CUSTOM">{symbol}</option>
                )}
              </select>
            </div>

            <div>
              <label
                htmlFor="custom-symbol"
                className="mb-2 block text-xs font-semibold text-slate-500 dark:text-slate-400"
              >
                Enter another broker symbol
              </label>

              <form onSubmit={handlePairSubmit} className="flex gap-2">
                <input
                  id="custom-symbol"
                  value={customSymbol}
                  onChange={(event) => setCustomSymbol(event.target.value)}
                  placeholder="e.g. EURUSD.a"
                  maxLength={30}
                  className="min-w-0 flex-1 rounded-xl border border-slate-200 bg-slate-50 px-3 py-3 text-sm uppercase outline-none transition focus:border-blue-500 dark:border-slate-700 dark:bg-slate-950"
                />
                <button
                  type="submit"
                  disabled={!customSymbol.trim()}
                  className="rounded-xl bg-slate-900 px-4 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:opacity-40 dark:bg-slate-700 dark:hover:bg-slate-600"
                >
                  Set
                </button>
              </form>
            </div>

            <div>
              <label
                htmlFor="timeframe"
                className="mb-2 block text-xs font-semibold text-slate-500 dark:text-slate-400"
              >
                Analysis timeframe
              </label>

              <select
                id="timeframe"
                value={timeframe}
                onChange={(event) => {
                  setTimeframe(
                    event.target.value as (typeof TIMEFRAMES)[number],
                  );
                  setAnalysis(null);
                }}
                className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-3 text-sm font-semibold outline-none transition focus:border-blue-500 dark:border-slate-700 dark:bg-slate-950"
              >
                {TIMEFRAMES.map((frame) => (
                  <option key={frame} value={frame}>
                    {frame}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label
                htmlFor="candle-limit"
                className="mb-2 block text-xs font-semibold text-slate-500 dark:text-slate-400"
              >
                Candle history
              </label>

              <select
                id="candle-limit"
                value={limit}
                onChange={(event) => {
                  setLimit(Number(event.target.value));
                  setAnalysis(null);
                }}
                className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-3 text-sm font-semibold outline-none transition focus:border-blue-500 dark:border-slate-700 dark:bg-slate-950"
              >
                <option value={100}>100 candles</option>
                <option value={200}>200 candles</option>
                <option value={300}>300 candles</option>
                <option value={500}>500 candles</option>
              </select>
            </div>
          </div>

          <div className="mt-4 flex flex-wrap items-center gap-2">
            {TIMEFRAMES.map((frame) => (
              <button
                key={frame}
                type="button"
                onClick={() => {
                  setTimeframe(frame);
                  setAnalysis(null);
                }}
                className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                  timeframe === frame
                    ? "bg-blue-600 text-white"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
                }`}
              >
                {frame}
              </button>
            ))}
          </div>
        </section>

        <section className="mb-6 overflow-hidden rounded-2xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 px-4 py-4 dark:border-slate-800 sm:px-5">
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-bold">{selectedSymbol}</h2>
                <span className="rounded-md bg-slate-100 px-2 py-1 text-xs font-semibold dark:bg-slate-800">
                  {timeframe}
                </span>
              </div>
              <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                MT5 stored market data · Latest 100 candles displayed
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <div className="flex items-center gap-1.5 text-xs text-emerald-600 dark:text-emerald-400">
                <span className="relative flex h-2 w-2">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-60" />
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
                </span>
                Auto refresh · 10s
              </div>

              <button
                type="button"
                onClick={() => void loadMarketData(true)}
                disabled={marketLoading}
                className="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold transition hover:bg-slate-100 disabled:opacity-50 dark:border-slate-700 dark:hover:bg-slate-800"
              >
                <RefreshCw
                  size={14}
                  className={marketLoading ? "animate-spin" : ""}
                />
                Refresh
              </button>
            </div>
          </div>

          <div className="grid gap-4 border-b border-slate-200 p-4 dark:border-slate-800 sm:grid-cols-3 sm:px-5">
            <div>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Latest close
              </p>
              <p className="mt-1 text-xl font-bold tabular-nums">
                {lastCandle ? formatPrice(lastCandle.close) : "—"}
              </p>
            </div>

            <div>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Previous candle change
              </p>
              <p
                className={`mt-1 flex items-center gap-1 text-xl font-bold tabular-nums ${
                  priceChange === null
                    ? "text-slate-500"
                    : isPriceUp
                      ? "text-emerald-500"
                      : "text-red-500"
                }`}
              >
                {priceChange === null ? (
                  "—"
                ) : (
                  <>
                    {isPriceUp ? (
                      <TrendingUp size={19} />
                    ) : (
                      <TrendingDown size={19} />
                    )}
                    {priceChange >= 0 ? "+" : ""}
                    {formatPrice(priceChange)}
                  </>
                )}
              </p>
            </div>

            <div>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Last data update
              </p>
              <p className="mt-1 flex items-center gap-2 text-sm font-semibold">
                <Clock3 size={15} className="text-blue-500" />
                {lastUpdated
                  ? lastUpdated.toLocaleTimeString()
                  : "Waiting for data"}
              </p>
            </div>
          </div>

          {marketError && (
            <div className="mx-4 mt-4 flex items-start gap-2 rounded-xl border border-amber-500/20 bg-amber-500/5 p-3 text-sm text-amber-700 dark:text-amber-400 sm:mx-5">
              <AlertCircle className="mt-0.5 shrink-0" size={17} />
              <span>{marketError}</span>
            </div>
          )}

          {marketLoading && candles.length === 0 ? (
            <div className="flex h-[320px] items-center justify-center gap-3 text-sm text-slate-500 dark:text-slate-400">
              <RefreshCw className="animate-spin" size={19} />
              Loading market candles...
            </div>
          ) : (
            <div className="px-2 py-4 sm:px-5">
              <CandleChart candles={candles} />
            </div>
          )}

          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 px-4 py-3 text-xs text-slate-500 dark:border-slate-800 dark:text-slate-400 sm:px-5">
            <div className="flex items-center gap-4">
              <span className="flex items-center gap-1.5">
                <span className="h-2.5 w-2.5 rounded-sm bg-emerald-500" />
                Bullish candle
              </span>
              <span className="flex items-center gap-1.5">
                <span className="h-2.5 w-2.5 rounded-sm bg-red-500" />
                Bearish candle
              </span>
            </div>

            <span>
              {candles.length} candles received
            </span>
          </div>
        </section>

        <section className="mb-6 rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900 sm:p-5">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <Activity className="text-blue-500" size={19} />
                <h2 className="text-lg font-bold">
                  Unified market analysis
                </h2>
              </div>
              <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                Run the existing analysis engine against {selectedSymbol} on{" "}
                {timeframe}.
              </p>
            </div>

            <button
              type="button"
              onClick={() => void runUnifiedAnalysis()}
              disabled={analysisLoading}
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-blue-600 px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {analysisLoading ? (
                <RefreshCw className="animate-spin" size={17} />
              ) : (
                <Play size={17} />
              )}
              {analysisLoading ? "Analyzing market..." : "Run unified analysis"}
            </button>
          </div>

          <div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
            {[
              "Technical indicators",
              "Market structure",
              "BOS and CHoCH",
              "Liquidity sweeps and zones",
              "Fair value gaps",
              "Order blocks",
              "Confluences",
              "Risk factors",
            ].map((feature) => (
              <div
                key={feature}
                className="flex items-center gap-2 rounded-lg bg-slate-50 px-3 py-2.5 text-xs font-medium text-slate-600 dark:bg-slate-950/60 dark:text-slate-300"
              >
                <CheckCircle2 size={14} className="shrink-0 text-emerald-500" />
                {feature}
              </div>
            ))}
          </div>

          {analysisError && (
            <div className="mt-5 flex items-start gap-2 rounded-xl border border-red-500/20 bg-red-500/5 p-3 text-sm text-red-600 dark:text-red-400">
              <AlertCircle className="mt-0.5 shrink-0" size={17} />
              {analysisError}
            </div>
          )}

          {analysisLoading && (
            <div className="mt-5 flex min-h-40 items-center justify-center gap-3 rounded-xl bg-slate-50 text-sm text-slate-500 dark:bg-slate-950/60 dark:text-slate-400">
              <RefreshCw className="animate-spin" size={20} />
              The analysis engine is processing the selected market data...
            </div>
          )}

          {analysis && !analysisLoading && (
            <div className="mt-6 border-t border-slate-200 pt-5 dark:border-slate-800">
              <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h3 className="font-bold">Analysis results</h3>
                  <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                    {selectedSymbol} · {timeframe}
                    {analysisCompletedAt
                      ? ` · ${analysisCompletedAt.toLocaleString()}`
                      : ""}
                  </p>
                </div>

                <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-3 py-1.5 text-xs font-semibold text-emerald-600 dark:text-emerald-400">
                  <CheckCircle2 size={14} />
                  Analysis completed
                </span>
              </div>

              <AnalysisResult result={analysis} />
            </div>
          )}
        </section>

        <footer className="flex flex-wrap items-center justify-between gap-3 pb-5 text-xs text-slate-500 dark:text-slate-400">
          <span className="flex items-center gap-2">
            <ShieldCheck size={15} />
            LovetechCyber AI Forex Analyst
          </span>

          <span className="flex items-center gap-2">
            {candles.length > 0 ? (
              <Wifi size={14} className="text-emerald-500" />
            ) : (
              <WifiOff size={14} />
            )}
            Market data depends on your MT5 connection.
          </span>
        </footer>
      </div>
    </div>
  );
}