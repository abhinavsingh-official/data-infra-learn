"use client";

import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";

const QUERY = `SELECT event_id, amount, merchant
FROM raw_transaction_events
WHERE amount IS NOT NULL;`;

const BEFORE_ROWS = [
  ["100000249073", "null", "—"],
  ["100000647435", "1786.53", "Rogers and Sons"],
  ["100000647435", "1786.53", "Rogers and Sons"],
];

const AFTER_ROWS = [
  ["100000647435", "1786.53", "Rogers and Sons"],
];

type Phase = "typing" | "running" | "before" | "after" | "pause";

const PHASE_DURATIONS: Record<Phase, number> = {
  typing: QUERY.length * 28,
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

/** A looping, self-contained animation: types out a real query shape from
 * this project's own reference content, "runs" it, shows the dirty input,
 * then the deduped/cleaned output - a real preview of what the product
 * does, not generic motion for its own sake. */
export function QueryDemo() {
  const [phase, setPhase] = useState<Phase>("typing");
  const [typedChars, setTypedChars] = useState(0);

  useEffect(() => {
    const timer = setTimeout(() => setPhase(NEXT_PHASE[phase]), PHASE_DURATIONS[phase]);
    return () => clearTimeout(timer);
  }, [phase]);

  useEffect(() => {
    if (phase !== "typing") {
      setTypedChars(phase === "running" || phase === "before" || phase === "after" ? QUERY.length : 0);
      return;
    }
    setTypedChars(0);
    const interval = setInterval(() => {
      setTypedChars((count) => (count < QUERY.length ? count + 1 : count));
    }, 28);
    return () => clearInterval(interval);
  }, [phase]);

  const showingRows = phase === "before" ? BEFORE_ROWS : phase === "after" ? AFTER_ROWS : null;

  return (
    <div className="overflow-hidden rounded-2xl border-2 border-border bg-card text-left shadow-[0_4px_0_0] shadow-border">
      <div className="flex items-center gap-1.5 border-b-2 border-border bg-muted/50 px-4 py-2.5">
        <span className="size-2.5 rounded-full bg-destructive/40" />
        <span className="size-2.5 rounded-full bg-warning/50" />
        <span className="size-2.5 rounded-full bg-success/50" />
        <span className="ml-2 text-xs text-muted-foreground">raw_transaction_events</span>
      </div>
      <div className="min-h-32 space-y-3 p-4 font-mono text-sm">
        <p className="whitespace-pre-wrap">
          {QUERY.slice(0, typedChars)}
          {phase === "typing" && <span className="animate-pulse">▍</span>}
        </p>
        {showingRows && (
          <div className="space-y-1.5 border-t border-border pt-3">
            <p className={cn("text-xs font-sans", phase === "before" ? "text-destructive" : "text-success")}>
              {phase === "before" ? "Raw: duplicate delivery, one missing amount" : "Cleaned: deduped, invalid row dropped"}
            </p>
            {showingRows.map((row, i) => (
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
