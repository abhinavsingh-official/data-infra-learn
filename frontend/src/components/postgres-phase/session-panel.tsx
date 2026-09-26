"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { SqlWorkspace } from "@/components/shared/sql-workspace";
import { ApiError, createSession, endSession, executeSql, gradeSession } from "@/lib/api";
import { GradingReportView } from "@/components/shared/grading-report";
import type { GradingReport } from "@/lib/types";

export function SessionPanel() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);
  const [grading, setGrading] = useState(false);
  const [ending, setEnding] = useState(false);
  const [report, setReport] = useState<GradingReport | null>(null);

  async function handleStart() {
    setStarting(true);
    try {
      const { session_id } = await createSession();
      setSessionId(session_id);
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
      const result = await gradeSession(sessionId);
      setReport(result);
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
      await endSession(sessionId);
      setSessionId(null);
      setReport(null);
      toast("Session ended - your schema and data were torn down.");
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
            Provisions a restricted Postgres role and schema just for you, with read access to the
            raw feed above. Nothing else touches your work.
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
          <SqlWorkspace
            sessionId={sessionId}
            execute={executeSql}
            placeholder="CREATE TABLE clean_transactions ( ... );"
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
