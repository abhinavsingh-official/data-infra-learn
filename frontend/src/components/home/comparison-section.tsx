"use client";

import { useEffect, useState } from "react";
import { getLearnPage } from "@/lib/api";
import type { ComparisonView } from "@/lib/types";
import { ComparisonDiagram } from "@/components/home/comparison-diagram";

/** Client-fetched so the homepage itself stays a plain server component;
 * fails silently (section just doesn't render) if the backend is down,
 * same tolerance the rest of the app already has for a missing API. */
export function ComparisonSection() {
  const [comparison, setComparison] = useState<ComparisonView | null>(null);

  useEffect(() => {
    getLearnPage()
      .then((page) => setComparison(page.comparison))
      .catch(() => {});
  }, []);

  if (!comparison) return null;

  return (
    <section id="compare" className="space-y-6">
      <div className="space-y-2 text-center">
        <h2 className="text-xl font-semibold tracking-tight">Click a node to see how it&apos;s actually solved</h2>
        <p className="mx-auto max-w-lg text-sm text-balance text-muted-foreground">{comparison.operation}</p>
      </div>
      <ComparisonDiagram entries={comparison.entries} />
    </section>
  );
}
