"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowRight, Lightbulb, Scale, Wrench } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
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

function PillSelector<T extends { label: string; slug: PhaseSlug }>({
  items,
  active,
  onSelect,
}: {
  items: T[];
  active: number;
  onSelect: (i: number) => void;
}) {
  return (
    <div className="flex flex-wrap gap-2">
      {items.map((item, i) => {
        const theme = PHASE_THEME[item.slug];
        const isActive = i === active;
        return (
          <Button
            key={item.label}
            size="sm"
            variant={isActive ? "default" : "outline"}
            onClick={() => onSelect(i)}
            className={cn(!isActive && theme.text, isActive && "retro-box")}
          >
            <span className={cn("mr-1.5 size-2 rounded-full", theme.bgSolid)} />
            {item.label}
          </Button>
        );
      })}
    </div>
  );
}

export default function LearnPagePage() {
  const [data, setData] = useState<LearnPage | null>(null);
  const [referenceTrees, setReferenceTrees] = useState<SkillTreeDto[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [referenceIndex, setReferenceIndex] = useState(0);
  const [edgeCaseIndex, setEdgeCaseIndex] = useState(0);

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

  const edgeCasePhases = data.phases.map((phase) => {
    const path = PATHS.find((p) => phase.phase.startsWith(p.match));
    return { phase, slug: path?.slug ?? ("postgres" as PhaseSlug), href: path?.href };
  });
  const activeEdgeCasePhase = edgeCasePhases[edgeCaseIndex];

  const activeReferenceTrack = REFERENCE_TRACKS[referenceIndex];
  const activeReferenceTree = referenceTrees?.[referenceIndex];
  const activeTeachNodes = activeReferenceTree?.nodes.filter((n) => n.type === "skill" && n.teach) ?? [];

  return (
    <div className="space-y-10">
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

      <Tabs defaultValue="compare" className="w-full">
        <TabsList>
          <TabsTrigger value="compare">Compare</TabsTrigger>
          <TabsTrigger value="reference">Reference</TabsTrigger>
          <TabsTrigger value="edge-cases">Edge Cases</TabsTrigger>
        </TabsList>

        <TabsContent value="compare" className="space-y-4 pt-2">
          <p className="text-sm text-muted-foreground">Click a node to jump straight into that paradigm.</p>
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
        </TabsContent>

        <TabsContent value="reference" className="space-y-4 pt-2">
          <p className="text-sm text-muted-foreground">
            Pick a track to see its worked examples - no need to start an exercise just to see
            the syntax again.
          </p>
          <PillSelector items={REFERENCE_TRACKS} active={referenceIndex} onSelect={setReferenceIndex} />
          {!referenceTrees ? (
            <p className="text-sm text-muted-foreground">Loading...</p>
          ) : (
            <div className="grid gap-3 md:grid-cols-2">
              {activeTeachNodes.map((node) => (
                <Card
                  key={node.id}
                  className={cn("border-l-4", PHASE_THEME[activeReferenceTrack.slug].border)}
                >
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
          )}
        </TabsContent>

        <TabsContent value="edge-cases" className="space-y-4 pt-2">
          <p className="text-sm text-muted-foreground">
            Every real fault this platform injects, and how to actually fix it - pick a paradigm.
          </p>
          <PillSelector
            items={edgeCasePhases.map((p) => ({ label: p.phase.phase, slug: p.slug }))}
            active={edgeCaseIndex}
            onSelect={setEdgeCaseIndex}
          />
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">{activeEdgeCasePhase.phase.one_liner}</p>
            {activeEdgeCasePhase.href && (
              <Link
                href={activeEdgeCasePhase.href}
                className="flex shrink-0 items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
              >
                Open track <ArrowRight className="size-3" />
              </Link>
            )}
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            {activeEdgeCasePhase.phase.entries.map((entry) => (
              <Card key={entry.error_code} className={cn("border-l-4", PHASE_THEME[activeEdgeCasePhase.slug].border)}>
                <CardHeader>
                  <Badge variant="destructive">{entry.error_code}</Badge>
                </CardHeader>
                <CardContent className="space-y-2.5">
                  <div className="flex gap-2">
                    <Lightbulb className="mt-0.5 size-4 shrink-0 text-warning" />
                    <p className="text-sm text-muted-foreground">{entry.why}</p>
                  </div>
                  <div className="flex gap-2">
                    <Wrench className="mt-0.5 size-4 shrink-0 text-success" />
                    <p className="text-sm text-muted-foreground">{entry.fix}</p>
                  </div>
                  <div className="flex gap-2">
                    <Scale className="mt-0.5 size-4 shrink-0 text-primary" />
                    <p className="text-sm text-muted-foreground">{entry.tradeoffs}</p>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
