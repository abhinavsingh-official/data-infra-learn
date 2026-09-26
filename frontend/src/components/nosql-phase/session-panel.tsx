"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { ApiError, createNosqlSession, endNosqlSession, gradeNosqlSession } from "@/lib/api";
import type { NosqlGradingReport } from "@/lib/types";
import { GradingReportView } from "./grading-report";
import { MongoExecuteBox } from "./mongo-execute-box";
import { SourceQueryBox } from "./source-query-box";

export function SessionPanel() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);
  const [grading, setGrading] = useState(false);
  const [ending, setEnding] = useState(false);
  const [report, setReport] = useState<NosqlGradingReport | null>(null);

  async function handleStart() {
    setStarting(true);
    try {
      const { session_id } = await createNosqlSession();
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
      setReport(await gradeNosqlSession(sessionId));
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
      await endNosqlSession(sessionId);
      setSessionId(null);
      setReport(null);
      toast("Session ended - your Mongo database and Postgres read-only role were torn down.");
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
            Provisions read-only access to the relational source tables and a Mongo database
            scoped just to you.
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
          <div>
            <h3 className="mb-2 text-sm font-medium">1. Query the Postgres source</h3>
            <SourceQueryBox sessionId={sessionId} />
          </div>
          <Separator />
          <div>
            <h3 className="mb-2 text-sm font-medium">2. Build account_profiles in Mongo</h3>
            <MongoExecuteBox sessionId={sessionId} />
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
