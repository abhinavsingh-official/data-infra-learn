"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowLeft, ArrowRight, ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
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

/** A fixed, non-draggable wheel (not a pannable/zoomable graph canvas) -
 * it spins into place once on load like the looping demo on /start, then
 * only turns when you click the side arrows. Clicking a node on the
 * wheel itself opens the query popup (unchanged from before). */

const RADIUS = 160;
const STEP_DEG = 360 / 5;
const SETTLE_MS = 1100;
const TURN_MS = 450;

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
  const active = openIndex !== null ? entries[openIndex] : null;

  useEffect(() => {
    const id = requestAnimationFrame(() => setRotation(0));
    const done = setTimeout(() => setSettled(true), SETTLE_MS + 50);
    return () => {
      cancelAnimationFrame(id);
      clearTimeout(done);
    };
  }, []);

  function turn(direction: 1 | -1) {
    setRotation((r) => r + direction * STEP_DEG);
  }

  return (
    <>
      <div className="flex items-center justify-center gap-4 sm:gap-8">
        <Button variant="outline" size="icon" className="shrink-0" onClick={() => turn(-1)} aria-label="Rotate left">
          <ChevronLeft className="size-5" />
        </Button>

        <div className="relative size-[22rem] shrink-0">
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
                onClick={() => setOpenIndex(i)}
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

        <Button variant="outline" size="icon" className="shrink-0" onClick={() => turn(1)} aria-label="Rotate right">
          <ChevronRight className="size-5" />
        </Button>
      </div>

      <div className="flex justify-center">
        <Link
          href="/pipeline-architecture"
          className="text-sm text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
        >
          Pipeline Architecture (the discipline underneath all five) →
        </Link>
      </div>

      <Dialog open={active !== null} onOpenChange={(open) => !open && setOpenIndex(null)}>
        <DialogContent className="sm:max-w-xl">
          {active && (
            <>
              <DialogHeader>
                <DialogTitle>{active.paradigm}</DialogTitle>
                <DialogDescription>{active.explanation}</DialogDescription>
              </DialogHeader>
              <pre className="max-h-64 overflow-auto border-2 border-panel-edge/50 bg-muted/40 p-3 font-mono text-xs">
                <code>{active.code}</code>
              </pre>
              <div className="flex items-center justify-between pt-1">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setOpenIndex((i) => ((i ?? 0) - 1 + entries.length) % entries.length)}
                >
                  <ArrowLeft className="size-4" />
                  Prev
                </Button>
                <span className="text-xs text-muted-foreground">
                  {(openIndex ?? 0) + 1} / {entries.length}
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setOpenIndex((i) => ((i ?? 0) + 1) % entries.length)}
                >
                  Next
                  <ArrowRight className="size-4" />
                </Button>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
