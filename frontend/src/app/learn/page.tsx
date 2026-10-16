"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
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

export default function LearnPagePage() {
  const [data, setData] = useState<LearnPage | null>(null);
  const [failed, setFailed] = useState(false);

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
                  approach above.
                </CardDescription>
              </CardHeader>
            </Card>
          </Link>
        </div>
      </section>
    </div>
  );
}
