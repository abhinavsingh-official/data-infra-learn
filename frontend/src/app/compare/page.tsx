"use client";

import { useEffect, useState } from "react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { getComparisonView } from "@/lib/api";
import type { ComparisonView } from "@/lib/types";
import { ParadigmMapGraph } from "@/components/compare/paradigm-map-graph";

export default function ComparePage() {
  const [data, setData] = useState<ComparisonView | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    getComparisonView()
      .then(setData)
      .catch(() => setFailed(true));
  }, []);

  if (failed) {
    return (
      <Alert variant="destructive">
        <AlertTitle>Backend unreachable</AlertTitle>
        <AlertDescription>
          Could not load the comparison from the API. Make sure the backend is running and
          reachable at the configured API base URL.
        </AlertDescription>
      </Alert>
    );
  }

  if (!data) {
    return <p className="text-sm text-muted-foreground">Loading comparison...</p>;
  }

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight">Cross-platform comparison</h1>
        <p className="text-muted-foreground">
          Same dataset, six lenses - click a node to jump into that paradigm.
        </p>
      </div>

      <ParadigmMapGraph />

      <div className="space-y-2">
        <h2 className="text-xl font-semibold tracking-tight">{data.operation}</h2>
        <p className="text-sm text-muted-foreground">{data.why_this_operation}</p>
        <Badge variant="secondary">
          {data.real_duplicate_count} real duplicate-delivery events in the seeded data
        </Badge>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {data.entries.map((entry) => (
          <Card key={entry.paradigm}>
            <CardHeader>
              <CardTitle className="text-base">{entry.paradigm}</CardTitle>
              <CardDescription className="text-xs italic">{entry.source}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <pre className="overflow-x-auto rounded-md border bg-muted/30 p-3 text-xs">
                <code>{entry.code}</code>
              </pre>
              <p className="text-sm text-muted-foreground">{entry.explanation}</p>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
