"use client";

import { useState } from "react";
import { toast } from "sonner";
import { SqlWorkspace } from "@/components/shared/sql-workspace";
import { GradingReportView } from "@/components/shared/grading-report";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { ApiError, createLakeSession, endLakeSession, executeLakeSql, gradeLakeSession } from "@/lib/api";
import type { GradingReport } from "@/lib/types";

export function SessionPanel() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [outputDir, setOutputDir] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);
  const [grading, setGrading] = useState(false);
  const [ending, setEnding] = useState(false);
  const [report, setReport] = useState<GradingReport | null>(null);

  async function handleStart() {
    setStarting(true);
    try {
      const { session_id, output_dir } = await createLakeSession();
      setSessionId(session_id);
      setOutputDir(output_dir);
      setReport(null);
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Could not start a session.");
    } finally {
      setStarting(false);
    }
  }

  async function handleGrade() {
    if (!sessionId) return;
    setGrading(true);
    try {
      setReport(await gradeLakeSession(sessionId));
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Grading failed.");
    } finally {
      setGrading(false);
    }
  }

  async function handleEnd() {
    if (!sessionId) return;
    setEnding(true);
    try {
      await endLakeSession(sessionId);
      setSessionId(null);
      setOutputDir(null);
      setReport(null);
      toast("Session ended - your Parquet output and Postgres read-only role were torn down.");
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Could not end the session.");
    } finally {
      setEnding(false);
    }
  }

  if (!sessionId) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Start a session</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="mb-4 text-sm text-muted-foreground">
            Provisions a DuckDB file with the Postgres source already attached as{" "}
            <code>pg</code>, plus a real local directory for your own Parquet output.
          </p>
          <Button onClick={handleStart} disabled={starting}>
            {starting ? "Starting..." : "Start Session"}
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between gap-2">
            <CardTitle className="text-base">Session</CardTitle>
            <Badge variant="outline" className="font-mono text-xs">
              {sessionId.slice(0, 12)}...
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="rounded-md border bg-muted/30 p-3">
            <p className="mb-1 text-xs font-medium">Your output directory - use this literally in COPY TO</p>
            <code className="break-all text-xs">{outputDir}</code>
          </div>
          <SqlWorkspace
            sessionId={sessionId}
            execute={executeLakeSql}
            placeholder="COPY (SELECT ... FROM pg.raw_transaction_events) TO '<output directory>' (FORMAT PARQUET, PARTITION_BY (event_date))"
            rows={6}
          />
          <Separator />
          <div className="flex flex-wrap gap-2">
            <Button onClick={handleGrade} disabled={grading}>
              {grading ? "Grading..." : "Grade Submission"}
            </Button>
            <Button onClick={handleEnd} variant="outline" disabled={ending}>
              {ending ? "Ending..." : "End Session"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {report && (
        <Card>
          <CardHeader>
            <CardTitle>Grading report</CardTitle>
          </CardHeader>
          <CardContent>
            <GradingReportView report={report} />
          </CardContent>
        </Card>
      )}
    </div>
  );
}
