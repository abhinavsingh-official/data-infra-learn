"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import {
  ApiError,
  createWarehouseSession,
  endWarehouseSession,
  gradeWarehouseSession,
  simulateWarehouseChanges,
} from "@/lib/api";
import type { WarehouseGradingReport } from "@/lib/types";
import { GradingReportView } from "./grading-report";
import { SqlWorkspace } from "./sql-workspace";

export function SessionPanel() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);
  const [simulating, setSimulating] = useState(false);
  const [grading, setGrading] = useState(false);
  const [ending, setEnding] = useState(false);
  const [report, setReport] = useState<WarehouseGradingReport | null>(null);

  async function handleStart() {
    setStarting(true);
    try {
      const { session_id } = await createWarehouseSession();
      setSessionId(session_id);
      setReport(null);
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Could not start a session.");
    } finally {
      setStarting(false);
    }
  }

  async function handleSimulateChanges() {
    if (!sessionId) return;
    setSimulating(true);
    try {
      const { mutated_account_count } = await simulateWarehouseChanges(sessionId);
      toast(`Day 2 begins - ${mutated_account_count} accounts just changed.`);
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Could not simulate changes.");
    } finally {
      setSimulating(false);
    }
  }

  async function handleGrade() {
    if (!sessionId) return;
    setGrading(true);
    try {
      setReport(await gradeWarehouseSession(sessionId));
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
      await endWarehouseSession(sessionId);
      setSessionId(null);
      setReport(null);
      toast("Session ended - your DuckDB file and Postgres read-only role were torn down.");
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
            <code>pg</code>, plus a local <code>source_accounts_snapshot</code> to build from.
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
          <SqlWorkspace sessionId={sessionId} />
          <Separator />
          <div className="flex flex-wrap gap-2">
            <Button onClick={handleSimulateChanges} variant="secondary" disabled={simulating}>
              {simulating ? "Simulating..." : "Simulate Day-2 Changes"}
            </Button>
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
