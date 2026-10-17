"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowRight, Lightbulb, Scale, Wrench } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { PageHero } from "@/components/shared/page-hero";
import { getLearnPage } from "@/lib/api";
import { PHASE_THEME, type PhaseSlug } from "@/lib/phase-theme";
import { cn } from "@/lib/utils";
import type { LearnPage } from "@/lib/types";

const PATHS: { match: string; slug: PhaseSlug; href: string }[] = [
  { match: "Postgres", slug: "postgres", href: "/sql" },
  { match: "NoSQL", slug: "nosql", href: "/nosql" },
  { match: "Data Warehouse", slug: "warehouse", href: "/warehouse" },
  { match: "Data Lake", slug: "lake", href: "/lake" },
  { match: "Lakehouse", slug: "lakehouse", href: "/lakehouse" },
];

export default function EdgeCasesPage() {
  const [data, setData] = useState<LearnPage | null>(null);
  const [failed, setFailed] = useState(false);
  const [phaseIndex, setPhaseIndex] = useState(0);

  useEffect(() => {
    getLearnPage()
      .then(setData)
      .catch(() => setFailed(true));
  }, []);

  if (failed) {
    return (
      <Alert variant="destructive">
        <AlertTitle>Backend unreachable</AlertTitle>
        <AlertDescription>
          Could not load the learn page from the API. Make sure the backend is running and
          reachable at the configured API base URL.
        </AlertDescription>
      </Alert>
    );
  }

  if (!data) {
    return <p className="text-sm text-muted-foreground">Loading...</p>;
  }

  const phases = data.phases.map((phase) => {
    const path = PATHS.find((p) => phase.phase.startsWith(p.match));
    return { phase, slug: path?.slug ?? ("postgres" as PhaseSlug), href: path?.href };
  });
  const active = phases[phaseIndex];
  const theme = PHASE_THEME[active.slug];

  return (
    <div className="space-y-8">
      <PageHero
        title="Edge Cases"
        description="Every real fault this platform injects, and how to actually fix it - pick an approach."
        showBack
        backHref="/learn"
      />

      <div className="flex flex-wrap gap-2">
        {phases.map((p, i) => {
          const isActive = i === phaseIndex;
          const t = PHASE_THEME[p.slug];
          return (
            <Button
              key={p.phase.phase}
              size="sm"
              variant={isActive ? "default" : "outline"}
              onClick={() => setPhaseIndex(i)}
              className={cn(!isActive && t.text, isActive && "retro-box")}
            >
              <span className={cn("mr-1.5 size-2 rounded-full", t.bgSolid)} />
              {p.phase.phase}
            </Button>
          );
        })}
      </div>

      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">{active.phase.one_liner}</p>
        {active.href && (
          <Link
            href={active.href}
            className="flex shrink-0 items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
          >
            Open track <ArrowRight className="size-3" />
          </Link>
        )}
      </div>

      <div className="space-y-8">
        {active.phase.entries.map((entry) => (
          <Card key={entry.error_code} className={cn("border-l-4 overflow-hidden", theme.border)}>
            <CardHeader>
              <Badge variant="destructive">{entry.error_code}</Badge>
            </CardHeader>
            <CardContent className="grid gap-6 md:grid-cols-2">
              <div className="space-y-4 border-r-0 pr-0 md:border-r md:pr-6">
                <div className="flex gap-3">
                  <Lightbulb className="mt-1 size-5 shrink-0 text-warning" />
                  <p className="text-sm leading-relaxed">{entry.why}</p>
                </div>
                <div className="flex gap-3">
                  <Scale className="mt-1 size-5 shrink-0 text-primary" />
                  <p className="text-sm leading-relaxed">{entry.tradeoffs}</p>
                </div>
              </div>
              <div className="space-y-3">
                <div className="flex gap-3">
                  <Wrench className="mt-1 size-5 shrink-0 text-success" />
                  <p className="text-sm leading-relaxed">{entry.fix}</p>
                </div>
                <pre className="overflow-x-auto whitespace-pre-wrap break-words border-2 border-panel-edge/50 bg-muted/40 p-3 font-mono text-sm">
                  <code>{entry.fix_sql}</code>
                </pre>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
