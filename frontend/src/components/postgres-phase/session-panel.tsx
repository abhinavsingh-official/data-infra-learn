"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { SqlWorkspace } from "@/components/shared/sql-workspace";
import { Stepper } from "@/components/shared/stepper";
import { DatasetStats } from "@/components/shared/dataset-stats";
import { ReferenceSolution } from "@/components/shared/reference-solution";
import { ApiError, createSession, endSession, executeSql, gradeSession } from "@/lib/api";
import { GradingReportView } from "@/components/shared/grading-report";
import type { GradingReport, PostgresTask } from "@/lib/types";

const STEPS = ["Overview", "The task", "Explore & write", "Grade"];

export function SessionPanel({ task }: { task: PostgresTask }) {
  const [step, setStep] = useState(0);
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
      setStep(3);
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
      setStep(0);
      toast("Session ended - your schema and data were torn down.");
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Could not end the session.");
    } finally {
      setEnding(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <Stepper steps={STEPS} currentIndex={step} phase="postgres" />
      </CardHeader>
      <CardContent className="space-y-4">
        {step === 0 && (
          <div className="space-y-4">
            <div>
              <CardTitle className="mb-1">{task.title}</CardTitle>
              <CardDescription>{task.summary}</CardDescription>
            </div>
            <DatasetStats stats={task.dataset_stats} phase="postgres" />
            <div className="flex justify-end">
              <Button onClick={() => setStep(1)}>Next: the task</Button>
            </div>
          </div>
        )}

        {step === 1 && (
          <div className="space-y-6 text-sm">
            <section>
              <h3 className="mb-2 font-medium">Source: {task.source_table}</h3>
              <ul className="space-y-1 text-muted-foreground">
                {Object.entries(task.source_columns).map(([column, description]) => (
                  <li key={column}>
                    <code className="text-foreground">{column}</code> — {description}
                  </li>
                ))}
              </ul>
            </section>

            <section>
              <h3 className="mb-2 font-medium">Edge cases to handle</h3>
              <ul className="list-disc space-y-1 pl-5 text-muted-foreground">
                {task.edge_cases_to_handle.map((edgeCase) => (
                  <li key={edgeCase}>{edgeCase}</li>
                ))}
              </ul>
            </section>

            <section>
              <h3 className="mb-2 font-medium">
                Required output: <code>{task.required_output.table}</code>
              </h3>
              <p className="mb-2 text-muted-foreground">{task.required_output.note}</p>
              <ul className="space-y-1 text-muted-foreground">
                {Object.entries(task.required_output.columns).map(([column, spec]) => (
                  <li key={column}>
                    <code className="text-foreground">{column}</code> — {spec}
                  </li>
                ))}
              </ul>
            </section>

            <p className="italic text-muted-foreground">{task.hint}</p>

            <div className="flex justify-between">
              <Button variant="outline" onClick={() => setStep(0)}>
                Back
              </Button>
              <Button onClick={() => setStep(2)}>Next: explore &amp; write</Button>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-4">
            {!sessionId ? (
              <div>
                <p className="mb-4 text-sm text-muted-foreground">
                  Provisions a restricted Postgres role and schema just for you, with read access to
                  the raw feed above. Nothing else touches your work.
                </p>
                <Button onClick={handleStart} disabled={starting}>
                  {starting ? "Starting..." : "Start Session"}
                </Button>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-medium">Session</span>
                  <Badge variant="outline" className="font-mono text-xs">
                    {sessionId.slice(0, 12)}...
                  </Badge>
                </div>
                <SqlWorkspace
                  sessionId={sessionId}
                  execute={executeSql}
                  placeholder="CREATE TABLE clean_transactions ( ... );"
                  starterValue={task.starter_sql}
                  rows={10}
                />
                <ReferenceSolution
                  solution={task.reference_solution.sql}
                  note={task.reference_solution.note}
                />
              </div>
            )}

            <Separator />
            <div className="flex flex-wrap justify-between gap-2">
              <Button variant="outline" onClick={() => setStep(1)}>
                Back
              </Button>
              <div className="flex flex-wrap gap-2">
                <Button variant="outline" onClick={handleEnd} disabled={!sessionId || ending}>
                  {ending ? "Ending..." : "End Session"}
                </Button>
                <Button onClick={handleGrade} disabled={!sessionId || grading}>
                  {grading ? "Grading..." : "Grade Submission"}
                </Button>
              </div>
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="space-y-4">
            {report ? (
              <GradingReportView report={report} />
            ) : (
              <p className="text-sm text-muted-foreground">
                No grading report yet - go back and submit your work first.
              </p>
            )}
            <div className="flex justify-between">
              <Button variant="outline" onClick={() => setStep(2)}>
                Back
              </Button>
              <Button variant="outline" onClick={handleEnd} disabled={!sessionId || ending}>
                {ending ? "Ending..." : "End Session"}
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
