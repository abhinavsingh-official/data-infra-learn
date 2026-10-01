"use client";

import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";

interface Example {
  label: string;
  query: string;
  before: { note: string; rows: string[][] };
  after: { note: string; rows: string[][] };
}

const EXAMPLES: Example[] = [
  {
    label: "SQL - Postgres",
    query: "SELECT event_id, amount, merchant\nFROM raw_transaction_events\nWHERE amount IS NOT NULL;",
    before: {
      note: "Raw: duplicate delivery, one missing amount",
      rows: [
        ["100000249073", "null", "—"],
        ["100000647435", "1786.53", "Rogers and Sons"],
        ["100000647435", "1786.53", "Rogers and Sons"],
      ],
    },
    after: {
      note: "Cleaned: deduped, invalid row dropped",
      rows: [["100000647435", "1786.53", "Rogers and Sons"]],
    },
  },
  {
    label: "NoSQL - MongoDB",
    query: 'db.accounts.aggregate([\n  { $match: { reward_events: { $exists: true } } },\n  { $limit: 20 }\n]);',
    before: {
      note: "Raw: reward_events embedded as an unbounded array",
      rows: [["acct_4471", "reward_events: [1240 items]", "—"]],
    },
    after: {
      note: "Cleaned: aggregated into a bounded summary",
      rows: [["acct_4471", "reward_summary: { total: 1240.5 }", "✓"]],
    },
  },
  {
    label: "PySpark",
    query: "df = spark.read.parquet(\"events/\")\ndf.groupBy(\"event_id\")\n  .agg(F.first(\"amount\")).show()",
    before: {
      note: "Raw: 3 partitioned files, one late arrival",
      rows: [
        ["part-2025-08", "18,204 rows", "—"],
        ["part-2025-09", "19,110 rows", "—"],
      ],
    },
    after: {
      note: "Cleaned: one deduped DataFrame, watermark applied",
      rows: [["clean_df", "36,842 rows", "✓"]],
    },
  },
];

type Phase = "typing" | "running" | "before" | "after" | "pause";

const PHASE_DURATIONS: Record<Phase, number> = {
  typing: 24,
  running: 500,
  before: 1400,
  after: 2200,
  pause: 900,
};

const NEXT_PHASE: Record<Phase, Phase> = {
  typing: "running",
  running: "before",
  before: "after",
  after: "pause",
  pause: "typing",
};

/** A looping, self-contained animation cycling through the platform's three
 * query shapes (SQL, NoSQL, PySpark) - types each one out, "runs" it, shows
 * the dirty input, then the cleaned output. A real preview of what the
 * product does across its actual breadth, not a Postgres-only demo. */
export function QueryDemo() {
  const [exampleIndex, setExampleIndex] = useState(0);
  const [phase, setPhase] = useState<Phase>("typing");
  const [typedChars, setTypedChars] = useState(0);
  const example = EXAMPLES[exampleIndex];

  useEffect(() => {
    const duration = phase === "typing" ? example.query.length * PHASE_DURATIONS.typing : PHASE_DURATIONS[phase];
    const timer = setTimeout(() => {
      if (phase === "pause") setExampleIndex((i) => (i + 1) % EXAMPLES.length);
      setPhase(NEXT_PHASE[phase]);
    }, duration);
    return () => clearTimeout(timer);
  }, [phase, example.query.length]);

  useEffect(() => {
    if (phase !== "typing") {
      setTypedChars(phase === "running" || phase === "before" || phase === "after" ? example.query.length : 0);
      return;
    }
    setTypedChars(0);
    const interval = setInterval(() => {
      setTypedChars((count) => (count < example.query.length ? count + 1 : count));
    }, PHASE_DURATIONS.typing);
    return () => clearInterval(interval);
  }, [phase, example.query]);

  const showing = phase === "before" ? example.before : phase === "after" ? example.after : null;

  return (
    <div className="overflow-hidden rounded-2xl bg-card text-left shadow-lg">
      <div className="flex items-center gap-1.5 bg-muted/50 px-4 py-2.5">
        <span className="size-2.5 rounded-full bg-destructive/40" />
        <span className="size-2.5 rounded-full bg-warning/50" />
        <span className="size-2.5 rounded-full bg-success/50" />
        <span className="ml-2 text-xs font-medium text-muted-foreground">{example.label}</span>
      </div>
      <div className="min-h-36 space-y-3 p-4 font-mono text-sm">
        <p className="whitespace-pre-wrap">
          {example.query.slice(0, typedChars)}
          {phase === "typing" && <span className="animate-pulse">▍</span>}
        </p>
        {showing && (
          <div className="space-y-1.5 border-t pt-3">
            <p className={cn("text-xs font-sans", phase === "before" ? "text-destructive" : "text-success")}>
              {showing.note}
            </p>
            {showing.rows.map((row, i) => (
              <div key={i} className="flex gap-3 text-xs text-muted-foreground">
                {row.map((cell, j) => (
                  <span key={j} className={cn(j === 0 && "text-foreground")}>{cell}</span>
                ))}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
