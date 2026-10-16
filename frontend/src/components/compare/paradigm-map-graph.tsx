"use client";

import Link from "next/link";
import { useMemo } from "react";
import { Background, Controls, ReactFlow, type Edge, type Node } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import type { PhaseSlug } from "@/lib/phase-theme";

/** Each paradigm's own skill tree is a linear path (SkillTreePath); this
 * is the one genuinely graph-shaped view - how the paradigms relate to
 * each other and to the one shared dataset, not a sequence within any
 * single one of them. */

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

const PARADIGM_LAYOUT: { slug: PhaseSlug; href: string; name: string; x: number; y: number }[] = [
  { slug: "postgres", href: "/sql", name: "SQL (Postgres)", x: 20, y: 20 },
  { slug: "nosql", href: "/nosql", name: "NoSQL (MongoDB)", x: 560, y: 20 },
  { slug: "warehouse", href: "/warehouse", name: "Data Warehouse", x: 640, y: 260 },
  { slug: "lake", href: "/lake", name: "Data Lake", x: 400, y: 420 },
  { slug: "lakehouse", href: "/lakehouse", name: "Lakehouse", x: 80, y: 420 },
  { slug: "pipeline-architecture", href: "/pipeline-architecture", name: "Pipeline Architecture", x: 0, y: 260 },
];

export function ParadigmMapGraph() {
  const nodes = useMemo<Node[]>(() => {
    const paradigmNodes: Node[] = PARADIGM_LAYOUT.map(({ slug, href, name, x, y }) => ({
      id: slug,
      position: { x, y },
      data: {
        label: (
          <Link href={href} className="block px-1 py-0.5 text-sm font-medium">
            {name}
          </Link>
        ),
      },
      style: {
        borderColor: `var(--phase-${slug})`,
        borderWidth: 2,
        borderRadius: 12,
      },
    }));
    return [CENTER, ...paradigmNodes];
  }, []);

  const edges = useMemo<Edge[]>(
    () =>
      PARADIGM_LAYOUT.map(({ slug }) => ({
        id: `dataset-${slug}`,
        source: "dataset",
        target: slug,
        animated: slug === "pipeline-architecture",
      })),
    [],
  );

  return (
    <div style={{ height: 480 }} className="overflow-hidden rounded-lg border">
      <ReactFlow nodes={nodes} edges={edges} fitView nodesDraggable={false} proOptions={{ hideAttribution: true }}>
        <Background />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}
