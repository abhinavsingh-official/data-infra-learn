"use client";

import { useEffect, useRef, useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { PHASE_THEME, type PhaseSlug } from "@/lib/phase-theme";
import { cn } from "@/lib/utils";
import type { ComparisonEntry } from "@/lib/types";

/** A fixed, non-draggable wheel (not a pannable/zoomable graph canvas).
 * It spins into place once on load, and clicking a node spins the wheel
 * to bring that node to the front before its query popup opens - there's
 * no separate manual spin control, the rotation IS the response to your
 * click, not something you drive yourself. */

const RADIUS = 150;
const STEP_DEG = 360 / 5;
const SETTLE_MS = 1100;
const TURN_MS = 700;

const APPROACHES: { slug: PhaseSlug; name: string }[] = [
  { slug: "postgres", name: "SQL (Postgres)" },
  { slug: "nosql", name: "NoSQL (MongoDB)" },
  { slug: "warehouse", name: "Data Warehouse" },
  { slug: "lake", name: "Data Lake" },
  { slug: "lakehouse", name: "Lakehouse" },
];

export function ComparisonDiagram({ entries }: { entries: ComparisonEntry[] }) {
  const [rotation, setRotation] = useState(-360);
  const [settled, setSettled] = useState(false);
  const [openIndex, setOpenIndex] = useState<number | null>(null);
  const pendingOpen = useRef<ReturnType<typeof setTimeout> | null>(null);
  const active = openIndex !== null ? entries[openIndex] : null;

  useEffect(() => {
    const id = requestAnimationFrame(() => setRotation(0));
    const done = setTimeout(() => setSettled(true), SETTLE_MS + 50);
    return () => {
      cancelAnimationFrame(id);
      clearTimeout(done);
    };
  }, []);

  function selectNode(i: number) {
    // Spin so node i lands at the top (front) position, then reveal its
    // query once the spin has actually finished playing.
    setRotation(-i * STEP_DEG);
    if (pendingOpen.current) clearTimeout(pendingOpen.current);
    pendingOpen.current = setTimeout(() => setOpenIndex(i), TURN_MS);
  }

  return (
    <>
      <div className="flex justify-center pt-4 pb-2">
        <div className="relative size-[20rem] shrink-0">
          <div className="pixel-box retro-box absolute top-1/2 left-1/2 flex size-28 -translate-x-1/2 -translate-y-1/2 items-center justify-center bg-primary p-3 text-center text-xs font-medium text-primary-foreground">
            One fintech dataset
          </div>
          {APPROACHES.map((approach, i) => {
            const angleDeg = i * STEP_DEG + rotation - 90;
            const angleRad = (angleDeg * Math.PI) / 180;
            const x = RADIUS * Math.cos(angleRad);
            const y = RADIUS * Math.sin(angleRad);
            return (
              <button
                key={approach.slug}
                type="button"
                onClick={() => selectNode(i)}
                style={{
                  transform: `translate(-50%, -50%) translate(${x}px, ${y}px)`,
                  transitionDuration: `${settled ? TURN_MS : SETTLE_MS}ms`,
                }}
                className={cn(
                  "pixel-box retro-box absolute top-1/2 left-1/2 flex size-24 cursor-pointer items-center justify-center bg-card p-2 text-center text-xs font-medium transition-transform ease-out",
                  PHASE_THEME[approach.slug].border,
                )}
              >
                {approach.name}
              </button>
            );
          })}
        </div>
      </div>

      <Dialog open={active !== null} onOpenChange={(open) => !open && setOpenIndex(null)}>
        <DialogContent className="sm:max-w-xl">
          {active && (
            <>
              <DialogHeader>
                <DialogTitle>{active.paradigm}</DialogTitle>
                <DialogDescription>{active.explanation}</DialogDescription>
              </DialogHeader>
              <pre className="max-h-64 overflow-y-auto whitespace-pre-wrap break-words border-2 border-panel-edge/50 bg-muted/40 p-3 font-mono text-xs">
                <code>{active.code}</code>
              </pre>
            </>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
