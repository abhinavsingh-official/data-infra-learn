"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { Background, Controls, ReactFlow, type Edge, type Node } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { ArrowLeft, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type { PhaseSlug } from "@/lib/phase-theme";
import type { ComparisonEntry } from "@/lib/types";

/** The homepage's own version of the cross-approach map: the five
 * code-comparable storage approaches open an in-place query popup on
 * click (cycle through all five with the arrows, no page leaves);
 * Pipeline Architecture has no comparable query, so it stays a plain
 * link through to its own page instead. */

const CENTER: Node = {
  id: "dataset",
  position: { x: 320, y: 220 },
  data: { label: "One fintech dataset" },
  style: {
    background: "var(--primary)",
    color: "var(--primary-foreground)",
    borderRadius: 9999,
    fontWeight: 600,
    width: 160,
    textAlign: "center",
  },
};

const APPROACH_LAYOUT: { slug: PhaseSlug; name: string; x: number; y: number }[] = [
  { slug: "postgres", name: "SQL (Postgres)", x: 20, y: 20 },
  { slug: "nosql", name: "NoSQL (MongoDB)", x: 560, y: 20 },
  { slug: "warehouse", name: "Data Warehouse", x: 640, y: 260 },
  { slug: "lake", name: "Data Lake", x: 400, y: 420 },
  { slug: "lakehouse", name: "Lakehouse", x: 80, y: 420 },
];

const PIPELINE_NODE = {
  slug: "pipeline-architecture" as const,
  href: "/pipeline-architecture",
  name: "Pipeline Architecture",
  x: 0,
  y: 260,
};

export function ComparisonDiagram({ entries }: { entries: ComparisonEntry[] }) {
  const [openIndex, setOpenIndex] = useState<number | null>(null);
  const active = openIndex !== null ? entries[openIndex] : null;

  const nodes = useMemo<Node[]>(() => {
    const approachNodes: Node[] = APPROACH_LAYOUT.map(({ slug, name, x, y }, i) => ({
      id: slug,
      position: { x, y },
      data: {
        label: (
          <button
            type="button"
            onClick={() => setOpenIndex(i)}
            className="block w-full cursor-pointer px-1 py-0.5 text-left text-sm font-medium"
          >
            {name}
          </button>
        ),
      },
      style: {
        background: "var(--card)",
        color: "var(--card-foreground)",
        borderColor: `var(--phase-${slug})`,
        borderWidth: 2,
        borderRadius: 12,
      },
    }));
    const pipelineNode: Node = {
      id: PIPELINE_NODE.slug,
      position: { x: PIPELINE_NODE.x, y: PIPELINE_NODE.y },
      data: {
        label: (
          <Link href={PIPELINE_NODE.href} className="block px-1 py-0.5 text-sm font-medium">
            {PIPELINE_NODE.name}
          </Link>
        ),
      },
      style: {
        background: "var(--card)",
        color: "var(--card-foreground)",
        borderColor: `var(--phase-${PIPELINE_NODE.slug})`,
        borderWidth: 2,
        borderRadius: 12,
      },
    };
    return [CENTER, ...approachNodes, pipelineNode];
  }, []);

  const edges = useMemo<Edge[]>(
    () => [
      ...APPROACH_LAYOUT.map(({ slug }) => ({ id: `dataset-${slug}`, source: "dataset", target: slug })),
      { id: `dataset-${PIPELINE_NODE.slug}`, source: "dataset", target: PIPELINE_NODE.slug, animated: true },
    ],
    [],
  );

  return (
    <>
      <div style={{ height: 480 }} className="overflow-hidden rounded-lg border">
        <ReactFlow nodes={nodes} edges={edges} fitView nodesDraggable={false} proOptions={{ hideAttribution: true }}>
          <Background />
          <Controls showInteractive={false} />
        </ReactFlow>
      </div>

      <Dialog open={active !== null} onOpenChange={(open) => !open && setOpenIndex(null)}>
        <DialogContent className="sm:max-w-xl">
          {active && (
            <>
              <DialogHeader>
                <DialogTitle>{active.paradigm}</DialogTitle>
                <DialogDescription>{active.explanation}</DialogDescription>
              </DialogHeader>
              <pre className="max-h-64 overflow-auto rounded-md border bg-muted/40 p-3 font-mono text-xs">
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
