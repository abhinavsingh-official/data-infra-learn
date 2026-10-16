"use client";

import { useEffect, useState } from "react";
import { PageHero } from "@/components/shared/page-hero";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { getSkillTree } from "@/lib/api";
import { PHASE_THEME, type PhaseSlug } from "@/lib/phase-theme";
import { cn } from "@/lib/utils";
import type { SkillTreeDto } from "@/lib/types";

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

export default function ReferencePage() {
  const [trees, setTrees] = useState<SkillTreeDto[] | null>(null);
  const [trackIndex, setTrackIndex] = useState(0);

  useEffect(() => {
    Promise.all(REFERENCE_TRACKS.map((t) => getSkillTree(t.routePrefix)))
      .then(setTrees)
      .catch(() => setTrees([]));
  }, []);

  const activeTrack = REFERENCE_TRACKS[trackIndex];
  const theme = PHASE_THEME[activeTrack.slug];
  const activeTree = trees?.[trackIndex];
  const teachNodes = activeTree?.nodes.filter((n) => n.type === "skill" && n.teach) ?? [];

  return (
    <div className="space-y-8">
      <PageHero
        title="Reference"
        description="Pick a track to see its worked examples - no need to start an exercise just to see the syntax again."
        showBack
        backHref="/learn"
      />

      <div className="flex flex-wrap gap-2">
        {REFERENCE_TRACKS.map((track, i) => {
          const isActive = i === trackIndex;
          const t = PHASE_THEME[track.slug];
          return (
            <Button
              key={track.label}
              size="sm"
              variant={isActive ? "default" : "outline"}
              onClick={() => setTrackIndex(i)}
              className={cn(!isActive && t.text, isActive && "retro-box")}
            >
              <span className={cn("mr-1.5 size-2 rounded-full", t.bgSolid)} />
              {track.label}
            </Button>
          );
        })}
      </div>

      {!trees ? (
        <p className="text-sm text-muted-foreground">Loading...</p>
      ) : (
        <div className="space-y-8">
          {teachNodes.map((node) => {
            const points = (node.teach!.steps ?? []).map((s) => s.body);
            return (
              <Card key={node.id} className={cn("border-l-4 overflow-hidden", theme.border)}>
                <CardHeader>
                  <CardTitle className="text-lg">{node.title}</CardTitle>
                </CardHeader>
                <CardContent className="grid gap-6 lg:grid-cols-2">
                  <pre className="min-h-48 overflow-auto rounded-lg border bg-muted/30 p-5 font-mono text-sm leading-relaxed">
                    <code>{node.teach!.sql}</code>
                  </pre>
                  <ul className="space-y-4">
                    {(points.length ? points : [node.teach!.note]).map((point, i) => (
                      <li key={i} className="flex gap-3 border-b pb-4 text-sm leading-relaxed last:border-b-0 last:pb-0">
                        <span className={cn("mt-1 size-1.5 shrink-0 rounded-full", theme.bgSolid)} />
                        <span>{point}</span>
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
