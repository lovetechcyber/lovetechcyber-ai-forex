import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Activity,
  ArrowLeft,
  ArrowRight,
  BarChart3,
  Calendar,
  ChevronDown,
  Clock,
  Eye,
  Filter,
  Loader2,
  Search,
  ShieldCheck,
  TrendingDown,
  TrendingUp,
  Minus,
  RefreshCw,
  X,
} from "lucide-react";

import {
  analysisHistoryAPI,
  type AnalysisHistoryItem,
} from "../service/api";

// eslint-disable-next-line @typescript-eslint/no-unused-vars
type Bias = "bullish" | "bearish" | "neutral" | "uncertain";

const timeframeOptions = ["M5", "M15", "M30", "H1", "H4", "D1"];

function formatDate(value: string) {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) return "Unknown date";

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function BiasBadge({ bias }: { bias: string }) {
  const normalized = bias.toLowerCase();

  const styles: Record<string, string> = {
    bullish:
      "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20",
    bearish:
      "bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/20",
    neutral:
      "bg-slate-500/10 text-slate-600 dark:text-slate-300 border-slate-500/20",
    uncertain:
      "bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/20",
  };

  const Icon =
    normalized === "bullish"
      ? TrendingUp
      : normalized === "bearish"
        ? TrendingDown
        : Minus;

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-semibold capitalize ${
        styles[normalized] ?? styles.neutral
      }`}
    >
      <Icon size={13} />
      {bias}
    </span>
  );
}

function ConfidenceBadge({ confidence }: { confidence: string }) {
  const styles: Record<string, string> = {
    low: "bg-slate-500/10 text-slate-600 dark:text-slate-300",
    medium: "bg-blue-500/10 text-blue-600 dark:text-blue-400",
    high: "bg-violet-500/10 text-violet-600 dark:text-violet-400",
  };

  return (
    <span
      className={`rounded-full px-2.5 py-1 text-xs font-semibold capitalize ${
        styles[confidence.toLowerCase()] ?? styles.low
      }`}
    >
      {confidence}
    </span>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center px-6 py-16 text-center">
      <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-blue-500/10">
        <BarChart3 className="text-blue-500" size={30} />
      </div>

      <h3 className="text-lg font-semibold text-slate-900 dark:text-white">
        No saved analysis yet
      </h3>

      <p className="mt-2 max-w-md text-sm leading-6 text-slate-500 dark:text-slate-400">
        Your completed AI market analyses will appear here automatically.
        Run an analysis to start building your history.
      </p>

      <Link
        to="/ai-analyst"
        className="mt-5 inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-700"
      >
        Run AI Analysis
        <ArrowRight size={16} />
      </Link>
    </div>
  );
}

export default function AnalysisHistory() {
  const [items, setItems] = useState<AnalysisHistoryItem[]>([]);
  const [search, setSearch] = useState("");
  const [symbol, setSymbol] = useState("");
  const [timeframe, setTimeframe] = useState("");
  const [bias, setBias] = useState("");

  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [pages, setPages] = useState(0);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadHistory = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const response = await analysisHistoryAPI.list({
        search: search.trim() || undefined,
        symbol: symbol.trim() || undefined,
        timeframe: timeframe || undefined,
        bias: bias || undefined,
        page,
        limit: 15,
      });

      setItems(response.items);
      setTotal(response.pagination.total);
      setPages(response.pagination.pages);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to load analysis history."
      );
    } finally {
      setLoading(false);
    }
  }, [search, symbol, timeframe, bias, page]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadHistory();
    }, 300);

    return () => window.clearTimeout(timer);
  }, [loadHistory]);

  function clearFilters() {
    setSearch("");
    setSymbol("");
    setTimeframe("");
    setBias("");
    setPage(1);
  }

  const hasFilters = Boolean(search || symbol || timeframe || bias);

  return (
    <div className="min-h-screen bg-slate-50 px-4 py-6 text-slate-900 dark:bg-[#080f1d] dark:text-white sm:px-6 lg:px-8">
      <div className="mx-auto max-w-7xl">
        <header className="mb-8 flex flex-wrap items-center justify-between gap-4">
          <div>
            <Link
              to="/dashboard"
              className="mb-4 inline-flex items-center gap-2 text-sm text-slate-500 transition hover:text-blue-500 dark:text-slate-400"
            >
              <ArrowLeft size={16} />
              Back to dashboard
            </Link>

            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-blue-600/10 text-blue-600 dark:text-blue-400">
                <Activity size={23} />
              </div>

              <div>
                <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">
                  Analysis History
                </h1>
                <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                  Review your previously completed AI market analyses.
                </p>
              </div>
            </div>
          </div>

          <button
            type="button"
            onClick={() => void loadHistory()}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 transition hover:bg-slate-100 disabled:opacity-50 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800"
          >
            <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
            Refresh
          </button>
        </header>

        <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <div className="rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
            <div className="flex items-center justify-between">
              <p className="text-sm text-slate-500 dark:text-slate-400">
                Saved analyses
              </p>
              <BarChart3 className="text-blue-500" size={19} />
            </div>
            <p className="mt-3 text-3xl font-bold tabular-nums">{total}</p>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
              Total records in your history
            </p>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
            <div className="flex items-center justify-between">
              <p className="text-sm text-slate-500 dark:text-slate-400">
                Current page
              </p>
              <Calendar className="text-violet-500" size={19} />
            </div>
            <p className="mt-3 text-3xl font-bold tabular-nums">
              {pages ? `${page} / ${pages}` : "0"}
            </p>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
              15 records per page
            </p>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900 sm:col-span-2 lg:col-span-1">
            <div className="flex items-center justify-between">
              <p className="text-sm text-slate-500 dark:text-slate-400">
                Review policy
              </p>
              <ShieldCheck className="text-emerald-500" size={19} />
            </div>
            <p className="mt-3 text-lg font-bold">Human confirmation</p>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
              AI analysis does not execute trades.
            </p>
          </div>
        </div>

        <section className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900 sm:p-5">
          <div className="mb-4 flex items-center gap-2">
            <Filter size={17} className="text-blue-500" />
            <h2 className="font-semibold">Search and filters</h2>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <div className="relative sm:col-span-2 lg:col-span-1">
              <Search
                size={17}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
              />
              <input
                value={search}
                onChange={(event) => {
                  setSearch(event.target.value);
                  setPage(1);
                }}
                placeholder="Search pair or summary..."
                className="w-full rounded-xl border border-slate-200 bg-slate-50 py-2.5 pl-10 pr-3 text-sm outline-none transition focus:border-blue-500 dark:border-slate-700 dark:bg-slate-950"
              />
            </div>

            <input
              value={symbol}
              onChange={(event) => {
                setSymbol(event.target.value.toUpperCase());
                setPage(1);
              }}
              placeholder="Currency pair (e.g. EURUSD)"
              className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm uppercase outline-none transition focus:border-blue-500 dark:border-slate-700 dark:bg-slate-950"
            />

            <div className="relative">
              <select
                value={timeframe}
                onChange={(event) => {
                  setTimeframe(event.target.value);
                  setPage(1);
                }}
                className="w-full appearance-none rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 pr-9 text-sm outline-none transition focus:border-blue-500 dark:border-slate-700 dark:bg-slate-950"
              >
                <option value="">All timeframes</option>
                {timeframeOptions.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
              <ChevronDown
                size={16}
                className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-slate-400"
              />
            </div>

            <div className="relative">
              <select
                value={bias}
                onChange={(event) => {
                  setBias(event.target.value);
                  setPage(1);
                }}
                className="w-full appearance-none rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 pr-9 text-sm capitalize outline-none transition focus:border-blue-500 dark:border-slate-700 dark:bg-slate-950"
              >
                <option value="">All market biases</option>
                <option value="bullish">Bullish</option>
                <option value="bearish">Bearish</option>
                <option value="neutral">Neutral</option>
                <option value="uncertain">Uncertain</option>
              </select>
              <ChevronDown
                size={16}
                className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-slate-400"
              />
            </div>
          </div>

          {hasFilters && (
            <button
              type="button"
              onClick={clearFilters}
              className="mt-3 inline-flex items-center gap-1.5 text-xs font-semibold text-blue-600 hover:text-blue-700 dark:text-blue-400"
            >
              <X size={14} />
              Clear filters
            </button>
          )}
        </section>

        <section className="mt-6 overflow-hidden rounded-2xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 px-5 py-4 dark:border-slate-800">
            <div>
              <h2 className="font-semibold">Saved analysis records</h2>
              <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                {total} matching {total === 1 ? "record" : "records"}
              </p>
            </div>

            <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
              <Clock size={14} />
              Newest first
            </div>
          </div>

          {loading ? (
            <div className="flex min-h-64 items-center justify-center gap-3 text-sm text-slate-500 dark:text-slate-400">
              <Loader2 className="animate-spin" size={20} />
              Loading analysis history...
            </div>
          ) : error ? (
            <div className="flex min-h-64 flex-col items-center justify-center px-6 text-center">
              <p className="font-semibold text-red-600 dark:text-red-400">
                Could not load history
              </p>
              <p className="mt-2 max-w-lg text-sm text-slate-500 dark:text-slate-400">
                {error}
              </p>
              <button
                type="button"
                onClick={() => void loadHistory()}
                className="mt-4 rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700"
              >
                Try again
              </button>
            </div>
          ) : items.length === 0 ? (
            <EmptyState />
          ) : (
            <>
              <div className="hidden overflow-x-auto md:block">
                <table className="w-full text-left text-sm">
                  <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500 dark:bg-slate-950/60 dark:text-slate-400">
                    <tr>
                      <th className="px-5 py-4 font-semibold">Currency pair</th>
                      <th className="px-5 py-4 font-semibold">Timeframe</th>
                      <th className="px-5 py-4 font-semibold">Market bias</th>
                      <th className="px-5 py-4 font-semibold">Confidence</th>
                      <th className="px-5 py-4 font-semibold">Date</th>
                      <th className="px-5 py-4 text-right font-semibold">
                        Details
                      </th>
                    </tr>
                  </thead>

                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                    {items.map((item) => (
                      <tr
                        key={item.id}
                        className="transition hover:bg-slate-50 dark:hover:bg-slate-800/40"
                      >
                        <td className="px-5 py-4">
                          <span className="font-bold">{item.symbol}</span>
                        </td>
                        <td className="px-5 py-4">
                          <span className="rounded-lg bg-slate-100 px-2.5 py-1 text-xs font-semibold dark:bg-slate-800">
                            {item.timeframe}
                          </span>
                        </td>
                        <td className="px-5 py-4">
                          <BiasBadge bias={item.directional_bias} />
                        </td>
                        <td className="px-5 py-4">
                          <ConfidenceBadge confidence={item.confidence} />
                        </td>
                        <td className="px-5 py-4 text-slate-500 dark:text-slate-400">
                          {formatDate(item.analyzed_at)}
                        </td>
                        <td className="px-5 py-4 text-right">
                          <Link
                            to={`/analysis-history/${item.id}`}
                            className="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold transition hover:border-blue-500 hover:text-blue-600 dark:border-slate-700 dark:hover:text-blue-400"
                          >
                            <Eye size={14} />
                            View
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="grid gap-3 p-4 md:hidden">
                {items.map((item) => (
                  <article
                    key={item.id}
                    className="rounded-xl border border-slate-200 p-4 dark:border-slate-800"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-lg font-bold">{item.symbol}</p>
                        <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                          {item.timeframe} · {formatDate(item.analyzed_at)}
                        </p>
                      </div>
                      <BiasBadge bias={item.directional_bias} />
                    </div>

                    <div className="mt-4 flex items-center justify-between gap-3">
                      <ConfidenceBadge confidence={item.confidence} />
                      <Link
                        to={`/analysis-history/${item.id}`}
                        className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-3 py-2 text-xs font-semibold text-white hover:bg-blue-700"
                      >
                        View details
                        <ArrowRight size={14} />
                      </Link>
                    </div>
                  </article>
                ))}
              </div>

              <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 px-5 py-4 dark:border-slate-800">
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Page {page} of {pages || 1}
                </p>

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    disabled={page <= 1}
                    onClick={() => setPage((current) => current - 1)}
                    className="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40 dark:border-slate-700 dark:hover:bg-slate-800"
                  >
                    <ArrowLeft size={14} />
                    Previous
                  </button>

                  <button
                    type="button"
                    disabled={page >= pages}
                    onClick={() => setPage((current) => current + 1)}
                    className="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40 dark:border-slate-700 dark:hover:bg-slate-800"
                  >
                    Next
                    <ArrowRight size={14} />
                  </button>
                </div>
              </div>
            </>
          )}
        </section>
      </div>
    </div>
  );
}