import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Activity,
  BarChart3,
  Bell,
  CircleHelp,
  History,
  LayoutDashboard,
  LogOut,
  Menu,
  Moon,
  RefreshCw,
  Settings,
  ShieldCheck,
  Sun,
  TrendingUp,
  Wifi,
  WifiOff,
  X,
} from "lucide-react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { marketAPI } from "../service/api";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";

type Candle = {
  time: string;
  close: number;
  open?: number;
  high?: number;
  low?: number;
};

type MarketRecord = Record<string, unknown>;

const SYMBOLS = [
  "EURUSD",
  "GBPUSD",
  "USDJPY",
  "USDCHF",
  "AUDUSD",
  "USDCAD",
  "NZDUSD",
  "EURJPY",
  "GBPJPY",
  "XAUUSD",
];

const TIMEFRAMES = ["M5", "M15", "M30", "H1", "H4", "D1"];

const REFRESH_INTERVAL = 60_000;

function asRecord(value: unknown): MarketRecord | null {
  if (typeof value === "object" && value !== null && !Array.isArray(value)) {
    return value as MarketRecord;
  }

  return null;
}

function getNumber(value: unknown): number | undefined {
  if (value === null || value === undefined || value === "") {
    return undefined;
  }

  const number = typeof value === "number" ? value : Number(value);

  return Number.isFinite(number) ? number : undefined;
}

function getMarketRows(response: unknown): MarketRecord[] {
  if (Array.isArray(response)) {
    return response
      .map(asRecord)
      .filter((row): row is MarketRecord => row !== null);
  }

  const record = asRecord(response);

  if (!record) return [];

  const possibleArrays = [
    record.data,
    record.candles,
    record.market_data,
    record.items,
    record.results,
    record.records,
  ];

  for (const candidate of possibleArrays) {
    if (Array.isArray(candidate)) {
      return candidate
        .map(asRecord)
        .filter((row): row is MarketRecord => row !== null);
    }
  }

  return [];
}

function normalizeCandles(rows: MarketRecord[]): Candle[] {
  return rows
    .map((row, index): Candle | null => {
      const close = getNumber(row.close ?? row.Close ?? row.price);

      if (close === undefined) return null;

      const rawTime =
        row.time ?? row.timestamp ?? row.date ?? row.datetime ?? row.open_time;

      return {
        time: rawTime ? String(rawTime).slice(0, 16) : `Candle ${index + 1}`,
        close,
        open: getNumber(row.open ?? row.Open),
        high: getNumber(row.high ?? row.High),
        low: getNumber(row.low ?? row.Low),
      };
    })
    .filter((candle): candle is Candle => candle !== null);
}

function formatPrice(value: number | undefined): string {
  if (value === undefined) return "—";

  return value.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 5,
  });
}

export default function Dashboard() {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();

  const [symbol, setSymbol] = useState("EURUSD");
  const [timeframe, setTimeframe] = useState("H1");
  const [candles, setCandles] = useState<Candle[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const loadMarketData = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const response = await marketAPI.latest(symbol, timeframe, 100);

      const rows = getMarketRows(response);
      const normalized = normalizeCandles(rows);

      setCandles(normalized);
      setLastUpdated(new Date());

      if (normalized.length === 0) {
        setError(
          "No market candles are available for this pair and timeframe yet.",
        );
      }
    } catch (err) {
      setCandles([]);

      setError(
        err instanceof Error
          ? err.message
          : "Unable to retrieve market data. Check your API connection.",
      );
    } finally {
      setLoading(false);
    }
  }, [symbol, timeframe]);

  // Load data when the selected pair or timeframe changes.
  // Defer the fetch to a later task so React can finish rendering before
  // the async state updates begin.
  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      void loadMarketData();
    }, 0);

    return () => window.clearTimeout(timeoutId);
  }, [loadMarketData]);

  // Refresh market data periodically.
  useEffect(() => {
    const intervalId = window.setInterval(() => {
      void loadMarketData();
    }, REFRESH_INTERVAL);

    return () => window.clearInterval(intervalId);
  }, [loadMarketData]);

  const latest = candles[candles.length - 1];
  const previous = candles[candles.length - 2];

  const priceChange =
    latest && previous ? latest.close - previous.close : undefined;

  const changePercent =
    priceChange !== undefined && previous && previous.close !== 0
      ? (priceChange / previous.close) * 100
      : undefined;

  const connected = candles.length > 0;

  const closeMobileMenu = () => {
    setMobileMenuOpen(false);
  };

  const handleNavigation = (path: string) => {
    navigate(path);
    closeMobileMenu();
  };

  const handleLogout = async () => {
    closeMobileMenu();
    await logout();
    navigate("/login");
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 dark:bg-[#080f1c] dark:text-slate-100">
      <div className="flex min-h-screen">
        {/* Mobile sidebar overlay */}
        {mobileMenuOpen && (
          <button
            type="button"
            aria-label="Close navigation"
            onClick={closeMobileMenu}
            className="fixed inset-0 z-40 bg-slate-950/50 lg:hidden"
          />
        )}

        {/* Sidebar */}
        <aside
          className={`fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-slate-200 bg-white p-5 transition-transform duration-200 dark:border-slate-800 dark:bg-[#0d1728] lg:static lg:z-auto lg:translate-x-0 ${
            mobileMenuOpen ? "translate-x-0" : "-translate-x-full"
          }`}
        >
          <div className="mb-10 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="rounded-xl bg-blue-600 p-2 text-white">
                <ShieldCheck size={24} />
              </div>

              <div>
                <p className="font-bold">LovetechCyber</p>
                <p className="text-xs text-slate-500">AI Forex Analyst</p>
              </div>
            </div>

            <button
              type="button"
              onClick={closeMobileMenu}
              className="rounded-lg p-2 hover:bg-slate-100 dark:hover:bg-slate-800 lg:hidden"
              aria-label="Close menu"
            >
              <X size={19} />
            </button>
          </div>

          <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-400">
            Workspace
          </p>

          <nav className="space-y-2">
            <NavItem
              icon={<LayoutDashboard size={18} />}
              label="Dashboard"
              active
              onClick={() => handleNavigation("/dashboard")}
            />

            <NavItem
              icon={<Activity size={18} />}
              label="Market Analysis"
              onClick={() => handleNavigation("/analysis")}
            />

            <NavItem
              icon={<BarChart3 size={18} />}
              label="Multi-Timeframe"
              onClick={() => handleNavigation("/multi-timeframe")}
            />

            <NavItem
              icon={<Activity size={18} />}
              label="Unified Analysis"
              onClick={() => handleNavigation("/unified-analysis")}
            />
            <NavItem
              icon={<History size={18} />}
              label="AI Analysis History"
              onClick={() => handleNavigation("/analysis-history")}
            />

            <NavItem
              icon={<TrendingUp size={18} />}
              label="AI Analyst"
              onClick={() => handleNavigation("/ai-analyst")}
            />
          </nav>

          <div className="mb-3 mt-8">
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Preferences
            </p>
          </div>

          <nav className="space-y-2">
            <NavItem icon={<Settings size={18} />} label="Settings" disabled />

            <NavItem
              icon={<CircleHelp size={18} />}
              label="Help & Support"
              disabled
            />
          </nav>

          <div className="mt-auto">
            <div className="mb-4 rounded-xl border border-blue-100 bg-blue-50 p-3 dark:border-blue-900/50 dark:bg-blue-950/30">
              <div className="flex items-center gap-2 text-sm font-semibold text-blue-700 dark:text-blue-300">
                <ShieldCheck size={16} />
                Analysis mode
              </div>

              <p className="mt-1 text-xs leading-5 text-slate-600 dark:text-slate-400">
                Insights only. No automatic trade execution. All AI
                recommendations require human review.
              </p>
            </div>

            <button
              type="button"
              onClick={() => void handleLogout()}
              className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-slate-600 transition hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
            >
              <LogOut size={18} />
              Sign out
            </button>
          </div>
        </aside>

        {/* Main workspace */}
        <main className="min-w-0 flex-1">
          {/* Header */}
          <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-slate-200 bg-white/90 px-4 backdrop-blur dark:border-slate-800 dark:bg-[#0d1728]/90 md:px-8">
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={() => setMobileMenuOpen((previous) => !previous)}
                className="rounded-lg p-2 hover:bg-slate-100 dark:hover:bg-slate-800 lg:hidden"
                aria-label="Toggle navigation"
              >
                <Menu size={21} />
              </button>

              <div>
                <h1 className="font-semibold">Market Dashboard</h1>

                <p className="hidden text-xs text-slate-500 sm:block">
                  Forex market intelligence workspace
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2 md:gap-4">
              <button
                type="button"
                onClick={toggleTheme}
                className="rounded-lg p-2 hover:bg-slate-100 dark:hover:bg-slate-800"
                aria-label="Toggle theme"
                title="Toggle theme"
              >
                {theme === "dark" ? <Sun size={19} /> : <Moon size={19} />}
              </button>

              <button
                type="button"
                className="relative rounded-lg p-2 hover:bg-slate-100 dark:hover:bg-slate-800"
                aria-label="Notifications"
                title="Notifications"
              >
                <Bell size={19} />
              </button>

              <div className="hidden text-right sm:block">
                <p className="max-w-48 truncate text-sm font-medium">
                  {user?.email ?? "Analyst"}
                </p>

                <p className="text-xs text-slate-500">Analyst workspace</p>
              </div>
            </div>
          </header>

          <div className="space-y-6 p-4 md:p-8">
            {/* Page introduction */}
            <section className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
              <div>
                <h2 className="text-2xl font-bold">Market Overview</h2>

                <p className="mt-1 text-sm text-slate-500">
                  Monitor market data and prepare your next analysis.
                </p>
              </div>

              <button
                type="button"
                onClick={() => void loadMarketData()}
                disabled={loading}
                className="inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
              >
                <RefreshCw
                  size={16}
                  className={loading ? "animate-spin" : ""}
                />
                Refresh data
              </button>
            </section>

            {/* Market statistics */}
            <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              <StatCard
                label="Selected pair"
                value={symbol}
                detail="Market instrument"
                icon={<Activity size={19} />}
              />

              <StatCard
                label="Latest price"
                value={formatPrice(latest?.close)}
                detail={latest ? "Latest received candle" : "Waiting for data"}
                icon={<TrendingUp size={19} />}
              />

              <StatCard
                label="Price change"
                value={
                  changePercent === undefined
                    ? "—"
                    : `${changePercent >= 0 ? "+" : ""}${changePercent.toFixed(3)}%`
                }
                detail="Compared with previous candle"
                icon={<BarChart3 size={19} />}
                positive={
                  changePercent === undefined ? undefined : changePercent >= 0
                }
              />

              <StatCard
                label="Market feed"
                value={connected ? "Data available" : "No data"}
                detail={
                  connected ? "Market candles received" : "Waiting for MT5 data"
                }
                icon={connected ? <Wifi size={19} /> : <WifiOff size={19} />}
                positive={connected}
              />
            </section>

            {/* Chart and instrument information */}
            <section className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_300px]">
              {/* Market chart */}
              <div className="min-w-0 rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-[#0d1728] md:p-6">
                <div className="mb-6 flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
                  <div>
                    <h3 className="text-lg font-semibold">Market chart</h3>

                    <p className="text-xs text-slate-500">
                      Closing prices from received market candles
                    </p>
                  </div>

                  <div className="flex flex-wrap gap-2">
                    <select
                      aria-label="Select currency pair"
                      value={symbol}
                      onChange={(event) => setSymbol(event.target.value)}
                      className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-blue-500 dark:border-slate-700 dark:bg-slate-900"
                    >
                      {SYMBOLS.map((item) => (
                        <option key={item} value={item}>
                          {item}
                        </option>
                      ))}
                    </select>

                    <select
                      aria-label="Select timeframe"
                      value={timeframe}
                      onChange={(event) => setTimeframe(event.target.value)}
                      className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-blue-500 dark:border-slate-700 dark:bg-slate-900"
                    >
                      {TIMEFRAMES.map((item) => (
                        <option key={item} value={item}>
                          {item}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                {loading ? (
                  <div className="flex h-72 items-center justify-center text-sm text-slate-500">
                    <RefreshCw className="mr-2 animate-spin" size={18} />
                    Loading market data...
                  </div>
                ) : candles.length > 1 ? (
                  <div className="h-72 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={candles}>
                        <CartesianGrid
                          strokeDasharray="3 3"
                          stroke="currentColor"
                          opacity={0.1}
                        />

                        <XAxis
                          dataKey="time"
                          tick={{ fontSize: 10 }}
                          minTickGap={35}
                          stroke="currentColor"
                          opacity={0.55}
                        />

                        <YAxis
                          domain={["auto", "auto"]}
                          tick={{ fontSize: 10 }}
                          width={75}
                          stroke="currentColor"
                          opacity={0.55}
                        />

                        <Tooltip
                          contentStyle={{
                            background:
                              theme === "dark" ? "#101d32" : "#ffffff",
                            border: "1px solid #334155",
                            borderRadius: 10,
                          }}
                          formatter={(value) => [
                            formatPrice(Number(value)),
                            "Close",
                          ]}
                        />

                        <Line
                          type="monotone"
                          dataKey="close"
                          stroke="#3b82f6"
                          strokeWidth={2}
                          dot={false}
                          activeDot={{ r: 4 }}
                          isAnimationActive={false}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                ) : (
                  <div className="flex h-72 flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 px-5 text-center dark:border-slate-700">
                    <Activity size={30} className="mb-3 text-slate-400" />

                    <p className="font-medium">Market data not available</p>

                    <p className="mt-2 max-w-sm text-sm text-slate-500">
                      {error ||
                        "Waiting for your MT5 integration to send market candles."}
                    </p>

                    <button
                      type="button"
                      onClick={() => void loadMarketData()}
                      disabled={loading}
                      className="mt-4 text-sm font-semibold text-blue-600 hover:underline disabled:opacity-50"
                    >
                      Try again
                    </button>
                  </div>
                )}

                <div className="mt-4 flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500">
                  <span>{candles.length} candles loaded</span>

                  <span>
                    {lastUpdated
                      ? `Updated ${lastUpdated.toLocaleTimeString()}`
                      : "Not yet updated"}
                  </span>
                </div>
              </div>

              {/* Instrument details */}
              <div className="space-y-4">
                <div className="rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-[#0d1728]">
                  <h3 className="font-semibold">Market connection</h3>

                  <div className="mt-4 flex items-center gap-3">
                    <span
                      className={`rounded-full p-2 ${
                        connected
                          ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-400"
                          : "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-400"
                      }`}
                    >
                      {connected ? <Wifi size={20} /> : <WifiOff size={20} />}
                    </span>

                    <div>
                      <p className="text-sm font-semibold">
                        {connected
                          ? "Market data received"
                          : "Awaiting market data"}
                      </p>

                      <p className="text-xs text-slate-500">
                        {connected
                          ? "Latest API request returned candles"
                          : "No candles returned for this selection"}
                      </p>
                    </div>
                  </div>
                </div>

                <div className="rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-[#0d1728]">
                  <h3 className="font-semibold">Selected instrument</h3>

                  <p className="mt-4 text-2xl font-bold">{symbol}</p>

                  <p className="mt-1 text-sm text-slate-500">
                    {timeframe} timeframe
                  </p>

                  <div className="mt-5 border-t border-slate-100 pt-4 dark:border-slate-800">
                    <PriceRow
                      label="Latest close"
                      value={formatPrice(latest?.close)}
                    />

                    <PriceRow
                      label="Previous close"
                      value={formatPrice(previous?.close)}
                    />

                    <div className="mt-3 flex justify-between text-sm">
                      <span className="text-slate-500">Price movement</span>

                      <span
                        className={`font-semibold ${
                          priceChange === undefined
                            ? ""
                            : priceChange >= 0
                              ? "text-emerald-500"
                              : "text-red-500"
                        }`}
                      >
                        {priceChange === undefined
                          ? "—"
                          : `${priceChange >= 0 ? "+" : ""}${formatPrice(priceChange)}`}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </section>

            {/* AI analyst introduction */}
            <section className="rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-[#0d1728] md:p-6">
              <div className="flex items-center gap-2">
                <ShieldCheck size={20} className="text-blue-500" />

                <h3 className="font-semibold">AI Forex Analyst</h3>
              </div>

              <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">
                Combine technical indicators, market structure, liquidity zones,
                breakout analysis and multi-timeframe confirmation. AI insights
                are presented for human review. No trades are executed
                automatically.
              </p>

              <button
                type="button"
                onClick={() => navigate("/ai-analyst")}
                className="mt-4 inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-700"
              >
                <Activity size={16} />
                Open AI Analyst
              </button>
            </section>

            <footer className="pb-4 text-center text-xs text-slate-500">
              LovetechCyber AI Forex Analyst · Market analysis only
            </footer>
          </div>
        </main>
      </div>
    </div>
  );
}

function NavItem({
  icon,
  label,
  active = false,
  disabled = false,
  onClick,
}: {
  icon: React.ReactNode;
  label: string;
  active?: boolean;
  disabled?: boolean;
  onClick?: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm transition ${
        active
          ? "bg-blue-600 font-semibold text-white"
          : disabled
            ? "cursor-not-allowed text-slate-400 opacity-50"
            : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
      }`}
    >
      {icon}
      {label}

      {active && <span className="ml-auto h-2 w-2 rounded-full bg-white" />}
    </button>
  );
}

function StatCard({
  label,
  value,
  detail,
  icon,
  positive,
}: {
  label: string;
  value: string;
  detail: string;
  icon: React.ReactNode;
  positive?: boolean;
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-[#0d1728]">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-500">{label}</p>

        <span className="rounded-lg bg-blue-50 p-2 text-blue-600 dark:bg-blue-950/50 dark:text-blue-400">
          {icon}
        </span>
      </div>

      <p
        className={`mt-4 text-2xl font-bold ${
          positive === undefined
            ? ""
            : positive
              ? "text-emerald-500"
              : "text-amber-500"
        }`}
      >
        {value}
      </p>

      <p className="mt-1 text-xs text-slate-500">{detail}</p>
    </div>
  );
}

function PriceRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between text-sm">
      <span className="text-slate-500">{label}</span>
      <span className="font-semibold">{value}</span>
    </div>
  );
}
