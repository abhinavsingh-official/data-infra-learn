"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowRight } from "lucide-react";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { PageHero } from "@/components/shared/page-hero";
import { TypingCode } from "@/components/shared/typing-code";
import { ParadigmMapGraph } from "@/components/learn/paradigm-map-graph";
import { getLearnPage, getSkillTree } from "@/lib/api";
import { PHASE_THEME, type PhaseSlug } from "@/lib/phase-theme";
import { cn } from "@/lib/utils";
import type { LearnPage, SkillTreeDto } from "@/lib/types";

const PATHS: { match: string; slug: PhaseSlug; href: string }[] = [
  { match: "Postgres", slug: "postgres", href: "/sql" },
  { match: "NoSQL", slug: "nosql", href: "/nosql" },
  { match: "Data Warehouse", slug: "warehouse", href: "/warehouse" },
  { match: "Data Lake", slug: "lake", href: "/lake" },
  { match: "Lakehouse", slug: "lakehouse", href: "/lakehouse" },
];

// The fundamentals/phase tracks whose `teach` blocks are real, verified
// worked examples - surfaced here as a skimmable reference, the same
// material a learner would otherwise only see mid-exercise.
const REFERENCE_TRACKS: { routePrefix: string; label: string; slug: PhaseSlug }[] = [
  { routePrefix: "sql-databases-track", label: "SQL Databases", slug: "postgres" },
  { routePrefix: "postgres-phase", label: "Postgres", slug: "postgres" },
  { routePrefix: "mongo-databases-track", label: "MongoDB Databases", slug: "nosql" },
  { routePrefix: "warehouse-databases-track", label: "Warehouse Databases", slug: "warehouse" },
  { routePrefix: "pipeline-architecture-track", label: "Pipeline Architecture", slug: "pipeline-architecture" },
];

export default function LearnPagePage() {
  const [data, setData] = useState<LearnPage | null>(null);
  const [referenceTrees, setReferenceTrees] = useState<SkillTreeDto[] | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    getLearnPage()
      .then(setData)
      .catch(() => setFailed(true));
    Promise.all(REFERENCE_TRACKS.map((t) => getSkillTree(t.routePrefix)))
      .then(setReferenceTrees)
      .catch(() => setReferenceTrees([]));
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

  return (
    <div className="space-y-14">
      <PageHero title="Learn" description={data.overview} showBack backHref="/start" />

      <section className="space-y-4">
        <h2 className="text-xl font-semibold tracking-tight">Pick a path</h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {data.phases.map((phase) => {
            const path = PATHS.find((p) => phase.phase.startsWith(p.match));
            const theme = path ? PHASE_THEME[path.slug] : undefined;
            return (
              <Link key={phase.phase} href={path?.href ?? "/start"} className="block">
                <Card
                  className={cn(
                    "h-full border-l-4 transition-colors hover:border-foreground/30",
                    theme?.border,
                  )}
                >
                  <CardHeader>
                    <div className="flex items-center gap-2">
                      {theme && <span className={cn("size-2.5 rounded-full", theme.bgSolid)} />}
                      <CardTitle className="text-base">{phase.phase}</CardTitle>
                    </div>
                    <CardDescription>{phase.one_liner}</CardDescription>
                  </CardHeader>
                </Card>
              </Link>
            );
          })}
          <Link href="/pipeline-architecture" className="block">
            <Card className="h-full border-l-4 border-phase-pipeline-architecture/40 transition-colors hover:border-foreground/30">
              <CardHeader>
                <div className="flex items-center gap-2">
                  <span className="size-2.5 rounded-full bg-phase-pipeline-architecture" />
                  <CardTitle className="text-base">Pipeline Architecture</CardTitle>
                </div>
                <CardDescription>
                  The idempotency, schema-evolution, and monitoring discipline underneath every
                  paradigm above.
                </CardDescription>
              </CardHeader>
            </Card>
          </Link>
        </div>
      </section>

      <section className="space-y-4">
        <div>
          <h2 className="text-xl font-semibold tracking-tight">Same dataset, six lenses</h2>
          <p className="text-sm text-muted-foreground">Click a node to jump straight into that paradigm.</p>
        </div>
        <ParadigmMapGraph />
        <Card>
          <CardHeader>
            <CardTitle className="text-base">{data.comparison.operation}</CardTitle>
            <CardDescription>{data.comparison.why_this_operation}</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            {data.comparison.entries.map((entry) => (
              <div key={entry.paradigm} className="space-y-2 rounded-md border p-3">
                <p className="text-sm font-medium">{entry.paradigm}</p>
                <TypingCode code={entry.code} />
                <p className="text-sm text-muted-foreground">{entry.explanation}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      </section>

      {referenceTrees && referenceTrees.length > 0 && (
        <section className="space-y-6">
          <div>
            <h2 className="text-xl font-semibold tracking-tight">Quick reference</h2>
            <p className="text-sm text-muted-foreground">
              Every worked example from the fundamentals tracks, in one skimmable place - no need
              to start an exercise just to see the syntax again.
            </p>
          </div>
          {REFERENCE_TRACKS.map((track, i) => {
            const tree = referenceTrees[i];
            const theme = PHASE_THEME[track.slug];
            const teachNodes = tree?.nodes.filter((n) => n.type === "skill" && n.teach) ?? [];
            if (teachNodes.length === 0) return null;
            return (
              <div key={track.routePrefix} className="space-y-3">
                <div className="flex items-center gap-2">
                  <span className={cn("size-2.5 rounded-full", theme.bgSolid)} />
                  <h3 className="font-medium">{track.label}</h3>
                </div>
                <div className="grid gap-3 md:grid-cols-2">
                  {teachNodes.map((node) => (
                    <Card key={node.id} className={cn("border-l-4", theme.border)}>
                      <CardHeader>
                        <CardTitle className="text-sm">{node.title}</CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-2">
                        <pre className="overflow-x-auto rounded-md border bg-muted/30 p-3 text-xs">
                          <code>{node.teach!.sql}</code>
                        </pre>
                        <p className="text-sm text-muted-foreground">{node.teach!.note}</p>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </div>
            );
          })}
        </section>
      )}

      <section className="space-y-4">
        <h2 className="text-xl font-semibold tracking-tight">Every edge case, explained</h2>
        <div className="space-y-4">
          {data.phases.map((phase) => {
            const path = PATHS.find((p) => phase.phase.startsWith(p.match));
            const theme = path ? PHASE_THEME[path.slug] : undefined;
            return (
              <Card key={phase.phase} className={cn("border-l-4", theme?.border)}>
                <CardHeader>
                  <div className="flex items-center justify-between gap-2">
                    <CardTitle className="text-base">{phase.phase}</CardTitle>
                    {path && (
                      <Link
                        href={path.href}
                        className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
                      >
                        Open track <ArrowRight className="size-3" />
                      </Link>
                    )}
                  </div>
                  <CardDescription>{phase.one_liner}</CardDescription>
                </CardHeader>
                <CardContent>
                  <Accordion className="w-full">
                    {phase.entries.map((entry) => (
                      <AccordionItem key={entry.error_code} value={entry.error_code}>
                        <AccordionTrigger>
                          <Badge variant="destructive">{entry.error_code}</Badge>
                        </AccordionTrigger>
                        <AccordionContent className="space-y-3">
                          <div className="space-y-1">
                            <p className="text-sm font-medium">Why it breaks</p>
                            <p className="text-sm text-muted-foreground">{entry.why}</p>
                          </div>
                          <div className="space-y-1">
                            <p className="text-sm font-medium">How to fix it</p>
                            <p className="text-sm text-muted-foreground">{entry.fix}</p>
                          </div>
                          <div className="space-y-1">
                            <p className="text-sm font-medium">Tradeoffs</p>
                            <p className="text-sm text-muted-foreground">{entry.tradeoffs}</p>
                          </div>
                        </AccordionContent>
                      </AccordionItem>
                    ))}
                  </Accordion>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </section>
    </div>
  );
}
