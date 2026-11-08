import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  Activity,
  AlertTriangle,
  ArrowLeft,
  Calendar,
  CheckCircle2,
  Clock,
  Loader2,
  ShieldCheck,
  TrendingDown,
  TrendingUp,
  Minus,
} from "lucide-react";

import {
  analysisHistoryAPI,
  type AnalysisHistoryRecord,
} from "../service/api";

function formatDate(value: string) {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) return "Unknown date";

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "full",
    timeStyle: "short",
  }).format(date);
}

function ValueList({
  title,
  items,
}: {
  title: string;
  items: unknown[];
}) {
  return (
    <div>
      <h4 className="mb-2 text-sm font-semibold text-slate-800 dark:text-slate-200">
        {title}
      </h4>

      {items.length === 0 ? (
        <p className="text-sm text-slate-400">No information supplied.</p>
      ) : (
        <ul className="space-y-2">
          {items.map((item, index) => (
            <li
              key={index}
              className="flex gap-2 text-sm leading-6 text-slate-600 dark:text-slate-300"
            >
              <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-blue-500" />
              <span>
                {typeof item === "string"
                  ? item
                  : JSON.stringify(item)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function ScenarioCard({
  title,
  scenario,
  bullish,
}: {
  title: string;
  scenario: {
    conditions: unknown[];
    supporting_evidence: unknown[];
    invalidation: unknown[];
  };
  bullish: boolean;
}) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
      <div className="mb-5 flex items-center gap-3">
        <div
          className={`flex h-10 w-10 items-center justify-center rounded-xl ${
            bullish
              ? "bg-emerald-500/10 text-emerald-500"
              : "bg-red-500/10 text-red-500"
          }`}
        >
          {bullish ? <TrendingUp size={20} /> : <TrendingDown size={20} />}
        </div>

        <h3 className="font-bold">{title}</h3>
      </div>

      <div className="space-y-5">
        <ValueList title="Conditions" items={scenario.conditions} />
        <ValueList
          title="Supporting evidence"
          items={scenario.supporting_evidence}
        />
        <ValueList title="Invalidation" items={scenario.invalidation} />
      </div>
    </section>
  );
}

export default function AnalysisHistoryDetail() {
  const { id } = useParams<{ id: string }>();

  const [record, setRecord] = useState<AnalysisHistoryRecord | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    async function loadRecord() {
      if (!id) {
        setError("Analysis history ID is missing.");
        setLoading(false);
        return;
      }

      setLoading(true);
      setError("");

      try {
        const response = await analysisHistoryAPI.detail(id);

        if (active) {
          setRecord(response.record);
        }
      } catch (err) {
        if (active) {
          setError(
            err instanceof Error
              ? err.message
              : "Unable to retrieve this analysis."
          );
        }
      } finally {
        if (active) setLoading(false);
      }
    }

    void loadRecord();

    return () => {
      active = false;
    };
  }, [id]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center gap-3 bg-slate-50 text-sm text-slate-500 dark:bg-[#080f1d] dark:text-slate-400">
        <Loader2 className="animate-spin" size={20} />
        Loading saved analysis...
      </div>
    );
  }

  if (error || !record) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-slate-50 px-5 text-center dark:bg-[#080f1d]">
        <AlertTriangle className="mb-4 text-amber-500" size={34} />
        <h2 className="text-xl font-bold text-slate-900 dark:text-white">
          Analysis not available
        </h2>
        <p className="mt-2 max-w-md text-sm text-slate-500 dark:text-slate-400">
          {error || "This saved analysis could not be found."}
        </p>
        <Link
          to="/analysis-history"
          className="mt-5 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-700"
        >
          Return to history
        </Link>
      </div>
    );
  }

  const interpretation = record.ai_result?.interpretation;

  if (!interpretation) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-slate-50 px-5 text-center dark:bg-[#080f1d]">
        <AlertTriangle className="mb-4 text-amber-500" size={34} />
        <h2 className="text-xl font-bold text-slate-900 dark:text-white">
          Incomplete saved analysis
        </h2>
        <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
          The saved record does not contain a readable AI interpretation.
        </p>
        <Link
          to="/analysis-history"
          className="mt-5 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white"
        >
          Return to history
        </Link>
      </div>
    );
  }

  const bias = interpretation.market_bias;
  const BiasIcon =
    bias === "bullish"
      ? TrendingUp
      : bias === "bearish"
        ? TrendingDown
        : Minus;

  const biasColor =
    bias === "bullish"
      ? "text-emerald-500"
      : bias === "bearish"
        ? "text-red-500"
        : "text-amber-500";

  return (
    <div className="min-h-screen bg-slate-50 px-4 py-6 text-slate-900 dark:bg-[#080f1d] dark:text-white sm:px-6 lg:px-8">
      <div className="mx-auto max-w-6xl">
        <Link
          to="/analysis-history"
          className="mb-6 inline-flex items-center gap-2 text-sm text-slate-500 hover:text-blue-500 dark:text-slate-400"
        >
          <ArrowLeft size={16} />
          Back to Analysis History
        </Link>

        <header className="mb-6 flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-blue-600 dark:text-blue-400">
              <Activity size={15} />
              Saved AI market analysis
            </div>

            <h1 className="text-3xl font-bold tracking-tight">
              {record.symbol}
            </h1>

            <div className="mt-2 flex flex-wrap items-center gap-3 text-sm text-slate-500 dark:text-slate-400">
              <span className="rounded-lg bg-slate-200 px-2.5 py-1 font-semibold text-slate-700 dark:bg-slate-800 dark:text-slate-200">
                {record.timeframe}
              </span>
              <span className="inline-flex items-center gap-1.5">
                <Calendar size={14} />
                {formatDate(record.analyzed_at)}
              </span>
            </div>
          </div>

          <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 px-4 py-3">
            <div className="flex items-center gap-2 text-sm font-semibold text-emerald-600 dark:text-emerald-400">
              <ShieldCheck size={17} />
              Analysis saved
            </div>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
              Historical record
            </p>
          </div>
        </header>

        <section className="mb-6 grid gap-4 sm:grid-cols-3">
          <div className="rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
            <p className="text-sm text-slate-500 dark:text-slate-400">
              AI market bias
            </p>
            <div className={`mt-3 flex items-center gap-2 text-2xl font-bold capitalize ${biasColor}`}>
              <BiasIcon size={24} />
              {bias}
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
            <p className="text-sm text-slate-500 dark:text-slate-400">
              AI confidence
            </p>
            <p className="mt-3 text-2xl font-bold capitalize">
              {interpretation.confidence}
            </p>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
              Qualitative confidence level
            </p>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
            <p className="text-sm text-slate-500 dark:text-slate-400">
              Human review
            </p>
            <div className="mt-3 flex items-center gap-2 text-lg font-bold text-amber-500">
              <CheckCircle2 size={21} />
              Required
            </div>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
              No automated trade execution
            </p>
          </div>
        </section>

        <section className="mb-6 rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
          <h2 className="mb-3 text-lg font-bold">AI market summary</h2>
          <p className="text-sm leading-7 text-slate-600 dark:text-slate-300">
            {interpretation.summary}
          </p>
        </section>

        <div className="mb-6 grid gap-5 lg:grid-cols-2">
          <ScenarioCard
            title="Bullish scenario"
            scenario={interpretation.bullish_scenario}
            bullish
          />

          <ScenarioCard
            title="Bearish scenario"
            scenario={interpretation.bearish_scenario}
            bullish={false}
          />
        </div>

        <div className="grid gap-5 lg:grid-cols-2">
          <section className="rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
            <h3 className="mb-4 font-bold">Key levels and zones</h3>
            <ValueList
              title="Identified levels and zones"
              items={interpretation.key_levels_and_zones}
            />
          </section>

          <section className="rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
            <h3 className="mb-4 flex items-center gap-2 font-bold">
              <AlertTriangle className="text-amber-500" size={18} />
              Risk factors
            </h3>
            <ValueList
              title="Identified risks"
              items={interpretation.risk_factors}
            />
          </section>

          <section className="rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
            <h3 className="mb-4 font-bold">Conflicting evidence</h3>
            <ValueList
              title="Conflicting signals"
              items={interpretation.conflicting_evidence}
            />
          </section>

          <section className="rounded-2xl border border-blue-500/20 bg-blue-500/5 p-5">
            <h3 className="mb-3 font-bold">Analyst recommendation</h3>
            <p className="text-sm leading-7 text-slate-600 dark:text-slate-300">
              {interpretation.analyst_recommendation}
            </p>
          </section>
        </div>

        <section className="mt-6 rounded-2xl border border-amber-500/20 bg-amber-500/5 p-5">
          <div className="flex items-start gap-3">
            <ShieldCheck className="mt-0.5 shrink-0 text-amber-500" size={21} />
            <div>
              <h3 className="font-semibold">Human confirmation required</h3>
              <p className="mt-1 text-sm leading-6 text-slate-600 dark:text-slate-300">
                This saved result is an AI interpretation of market data, not
                a guaranteed prediction or trade instruction. Review the
                supplied market evidence and independently confirm any
                trading decision. This application does not execute trades.
              </p>
            </div>
          </div>
        </section>

        <div className="mt-6 flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
          <Clock size={14} />
          Record ID: {record.id}
        </div>
      </div>
    </div>
  );
}