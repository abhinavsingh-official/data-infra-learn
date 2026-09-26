"use client";

import { useState } from "react";
import { toast } from "sonner";
import { GradingReportView } from "@/components/shared/grading-report";
import { SqlWorkspace } from "@/components/shared/sql-workspace";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import {
  ApiError,
  createLakehouseSession,
  endLakehouseSession,
  executeLakehouseSql,
  gradeLakehouseSession,
  releaseLakehouseBatch2,
} from "@/lib/api";
import type { GradingReport } from "@/lib/types";
import { CommitBatchBox } from "./commit-batch-box";

export function SessionPanel() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [deltaPath, setDeltaPath] = useState<string | null>(null);
  const [batch2Released, setBatch2Released] = useState(false);
  const [starting, setStarting] = useState(false);
  const [releasing, setReleasing] = useState(false);
  const [grading, setGrading] = useState(false);
  const [ending, setEnding] = useState(false);
  const [report, setReport] = useState<GradingReport | null>(null);

  async function handleStart() {
    setStarting(true);
    try {
      const { session_id, delta_table_path } = await createLakehouseSession();
      setSessionId(session_id);
      setDeltaPath(delta_table_path);
      setBatch2Released(false);
      setReport(null);
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Could not start a session.");
    } finally {
      setStarting(false);
    }
  }

  async function handleReleaseBatch2() {
    if (!sessionId) return;
    setReleasing(true);
    try {
      const { batch_2_row_count } = await releaseLakehouseBatch2(sessionId);
      setBatch2Released(true);
      toast(`Batch 2 released - ${batch_2_row_count} rows now in batch_2_events.`);
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Could not release batch 2.");
    } finally {
      setReleasing(false);
    }
  }

  async function handleGrade() {
    if (!sessionId) return;
    setGrading(true);
    try {
      setReport(await gradeLakehouseSession(sessionId));
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
      await endLakehouseSession(sessionId);
      setSessionId(null);
      setDeltaPath(null);
      setBatch2Released(false);
      setReport(null);
      toast("Session ended - your Delta table and Postgres read-only role were torn down.");
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
            Provisions a DuckDB file with <code>batch_1_events</code> ready to go - the second
            batch arrives only once you ask for it.
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
        <CardContent className="space-y-6">
          <div className="rounded-md border bg-muted/30 p-3">
            <p className="mb-1 text-xs font-medium">Your Delta table path</p>
            <code className="break-all text-xs">{deltaPath}</code>
          </div>

          <CommitBatchBox sessionId={sessionId} label="Commit batch 1 (from batch_1_events)" />

          <Separator />

          {!batch2Released ? (
            <Button onClick={handleReleaseBatch2} variant="secondary" disabled={releasing}>
              {releasing ? "Releasing..." : "Release Batch 2"}
            </Button>
          ) : (
            <CommitBatchBox sessionId={sessionId} label="Commit batch 2 (from batch_2_events only)" />
          )}

          <Separator />

          <div>
            <p className="mb-2 text-sm font-medium">Inspect your Delta table (delta_scan)</p>
            <SqlWorkspace
              sessionId={sessionId}
              execute={executeLakehouseSql}
              placeholder={`SELECT count(*) FROM delta_scan('${deltaPath}')`}
              rows={4}
            />
          </div>

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
