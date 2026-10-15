"use client";

import { useState } from "react";
import { toast } from "sonner";
import { SqlWorkspace } from "@/components/shared/sql-workspace";
import { GradingReportView } from "@/components/shared/grading-report";
import { Stepper } from "@/components/shared/stepper";
import { DatasetStats } from "@/components/shared/dataset-stats";
import { ReferenceSolution } from "@/components/shared/reference-solution";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { ApiError, createLakeSession, endLakeSession, executeLakeSql, gradeLakeSession } from "@/lib/api";
import type { GradingReport, LakeTask } from "@/lib/types";

const STEPS = ["Overview", "Workspace"];

export function SessionPanel({ task }: { task: LakeTask }) {
  const [step, setStep] = useState(0);
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
      setStep(0);
      toast("Session ended - your Parquet output and Postgres read-only role were torn down.");
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Could not end the session.");
    } finally {
      setEnding(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <Stepper steps={STEPS} currentIndex={step} phase="lake" />
      </CardHeader>
      <CardContent>
        {step === 0 && (
          <div className="space-y-4">
            <div>
              <CardTitle className="mb-1">{task.title}</CardTitle>
              <CardDescription>{task.summary}</CardDescription>
            </div>
            <DatasetStats stats={task.dataset_stats} phase="lake" />
            <div className="flex justify-end">
              <Button onClick={() => setStep(1)}>Open the workspace</Button>
            </div>
          </div>
        )}

        {step === 1 && (
          <div className="grid gap-6 lg:grid-cols-[300px_1fr]">
            <aside className="space-y-6 text-sm lg:sticky lg:top-4 lg:self-start">
              <section>
                <h3 className="mb-2 font-medium">Source</h3>
                <p className="text-muted-foreground">{task.source}</p>
              </section>

              <section>
                <h3 className="mb-2 font-medium">Your output directory</h3>
                <p className="text-muted-foreground">{task.your_output_directory}</p>
              </section>

              <section>
                <h3 className="mb-2 font-medium">Workflow</h3>
                <ol className="list-decimal space-y-1 pl-5 text-muted-foreground">
                  {task.workflow.map((workflowStep) => (
                    <li key={workflowStep}>{workflowStep.replace(/^\d+\.\s*/, "")}</li>
                  ))}
                </ol>
              </section>

              <section>
                <h3 className="mb-2 font-medium">
                  Required output: <code>{task.required_output.table}</code>
                </h3>
                <ul className="space-y-1 text-muted-foreground">
                  {Object.entries(task.required_output.columns).map(([column, spec]) => (
                    <li key={column}>
                      <code className="text-foreground">{column}</code> — {spec}
                    </li>
                  ))}
                </ul>
              </section>

              <section>
                <h3 className="mb-2 font-medium">Hints</h3>
                <ul className="list-disc space-y-1 pl-5 text-muted-foreground">
                  {task.hints.map((hint) => (
                    <li key={hint}>{hint}</li>
                  ))}
                </ul>
              </section>

              <Button variant="outline" size="sm" onClick={() => setStep(0)}>
                Back to overview
              </Button>
            </aside>

            <div className="space-y-4">
              {!sessionId ? (
                <div className="rounded-lg border p-4">
                  <p className="mb-4 text-sm text-muted-foreground">
                    Provisions a Spark SQL session with the five relational source tables already
                    registered as live views, plus a real local directory for your own Parquet output.
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
                  <div className="rounded-md border bg-muted/30 p-3">
                    <p className="mb-1 text-xs font-medium">Your output directory - use this literally in COPY TO</p>
                    <code className="break-all text-xs">{outputDir}</code>
                  </div>
                  <SqlWorkspace
                    sessionId={sessionId}
                    execute={executeLakeSql}
                    placeholder="CREATE TABLE lake_output USING PARQUET PARTITIONED BY (event_date) LOCATION '<output directory>' AS SELECT ... FROM raw_transaction_events"
                    starterValue={task.starter_sql}
                    rows={6}
                  />
                  <ReferenceSolution
                    solution={task.reference_solution.sql}
                    note={task.reference_solution.note}
                    steps={task.reference_solution.steps}
                  />

                  <Separator />
                  <div className="flex flex-wrap justify-between gap-2">
                    <Button variant="outline" onClick={handleEnd} disabled={ending}>
                      {ending ? "Ending..." : "End Session"}
                    </Button>
                    <Button onClick={handleGrade} disabled={grading}>
                      {grading ? "Grading..." : "Grade Submission"}
                    </Button>
                  </div>

                  {report && (
                    <div className="rounded-lg border p-4">
                      <h3 className="mb-3 font-medium">Grading report</h3>
                      <GradingReportView report={report} />
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
