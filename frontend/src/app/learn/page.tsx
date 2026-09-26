"use client";

import { useEffect, useState } from "react";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { getLearnPage } from "@/lib/api";
import type { LearnPage } from "@/lib/types";

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
    <div className="space-y-8">
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight">Learn</h1>
        <p className="text-muted-foreground">{data.overview}</p>
      </div>

      {data.phases.map((phase) => (
        <Card key={phase.phase}>
          <CardHeader>
            <CardTitle>{phase.phase}</CardTitle>
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
      ))}

      <Card>
        <CardHeader>
          <CardTitle>{data.comparison.operation}</CardTitle>
          <CardDescription>{data.comparison.why_this_operation}</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          {data.comparison.entries.map((entry) => (
            <div key={entry.paradigm} className="space-y-2 rounded-md border p-3">
              <p className="text-sm font-medium">{entry.paradigm}</p>
              <pre className="overflow-x-auto rounded-md border bg-muted/30 p-3 text-xs">
                <code>{entry.code}</code>
              </pre>
              <p className="text-sm text-muted-foreground">{entry.explanation}</p>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
