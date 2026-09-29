"use client";

import { useState } from "react";
import { toast } from "sonner";
import { GradingReportView } from "@/components/shared/grading-report";
import { SqlWorkspace } from "@/components/shared/sql-workspace";
import { Stepper } from "@/components/shared/stepper";
import { DatasetStats } from "@/components/shared/dataset-stats";
import { ReferenceSolution } from "@/components/shared/reference-solution";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import {
  ApiError,
  createLakehouseSession,
  endLakehouseSession,
  executeLakehouseSql,
  gradeLakehouseSession,
  releaseLakehouseBatch2,
} from "@/lib/api";
import type { GradingReport, LakehouseTask } from "@/lib/types";
import { CommitBatchBox } from "./commit-batch-box";

const STEPS = ["Overview", "The task", "Explore & write", "Grade"];

export function SessionPanel({ task }: { task: LakehouseTask }) {
  const [step, setStep] = useState(0);
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
      const result = await gradeLakehouseSession(sessionId);
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
      await endLakehouseSession(sessionId);
      setSessionId(null);
      setDeltaPath(null);
      setBatch2Released(false);
      setReport(null);
      setStep(0);
      toast("Session ended - your Delta table and Postgres read-only role were torn down.");
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Could not end the session.");
    } finally {
      setEnding(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <Stepper steps={STEPS} currentIndex={step} phase="lakehouse" />
      </CardHeader>
      <CardContent className="space-y-4">
        {step === 0 && (
          <div className="space-y-4">
            <div>
              <CardTitle className="mb-1">{task.title}</CardTitle>
              <CardDescription>{task.summary}</CardDescription>
            </div>
            <DatasetStats stats={task.dataset_stats} phase="lakehouse" />
            <div className="flex justify-end">
              <Button onClick={() => setStep(1)}>Next: the task</Button>
            </div>
          </div>
        )}

        {step === 1 && (
          <div className="space-y-6 text-sm">
            <section>
              <h3 className="mb-2 font-medium">Source</h3>
              <ul className="space-y-1 text-muted-foreground">
                {Object.entries(task.source).map(([name, description]) => (
                  <li key={name}>
                    <code className="text-foreground">{name}</code> — {description}
                  </li>
                ))}
              </ul>
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
                  Provisions a DuckDB file with <code>batch_1_events</code> ready to go - the second
                  batch arrives only once you ask for it.
                </p>
                <Button onClick={handleStart} disabled={starting}>
                  {starting ? "Starting..." : "Start Session"}
                </Button>
              </div>
            ) : (
              <div className="space-y-6">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-medium">Session</span>
                  <Badge variant="outline" className="font-mono text-xs">
                    {sessionId.slice(0, 12)}...
                  </Badge>
                </div>
                <div className="rounded-md border bg-muted/30 p-3">
                  <p className="mb-1 text-xs font-medium">Your Delta table path</p>
                  <code className="break-all text-xs">{deltaPath}</code>
                </div>

                <CommitBatchBox
                  sessionId={sessionId}
                  label="Commit batch 1 (from batch_1_events)"
                  starterValue={task.starter_sql}
                />

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
