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
import {
  ApiError,
  createWarehouseSession,
  endWarehouseSession,
  executeWarehouseSql,
  gradeWarehouseSession,
  simulateWarehouseChanges,
} from "@/lib/api";
import type { WarehouseGradingReport, WarehouseTask } from "@/lib/types";
import { GradingReportView } from "./grading-report";

const STEPS = ["Overview", "The task", "Explore & write", "Grade"];

export function SessionPanel({ task }: { task: WarehouseTask }) {
  const [step, setStep] = useState(0);
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
      const result = await gradeWarehouseSession(sessionId);
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
      await endWarehouseSession(sessionId);
      setSessionId(null);
      setReport(null);
      setStep(0);
      toast("Session ended - your DuckDB file and Postgres read-only role were torn down.");
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Could not end the session.");
    } finally {
      setEnding(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <Stepper steps={STEPS} currentIndex={step} phase="warehouse" />
      </CardHeader>
      <CardContent className="space-y-4">
        {step === 0 && (
          <div className="space-y-4">
            <div>
              <CardTitle className="mb-1">{task.title}</CardTitle>
              <CardDescription>{task.summary}</CardDescription>
            </div>
            <DatasetStats stats={task.dataset_stats} phase="warehouse" />
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
              <h3 className="mb-2 font-medium">Required output</h3>
              <div className="space-y-4">
                {Object.entries(task.required_output).map(([table, spec]) => (
                  <div key={table}>
                    <p className="mb-1 font-medium">
                      <code>{table}</code>
                    </p>
                    <p className="mb-1 text-muted-foreground">{spec.note}</p>
                    <ul className="space-y-1 text-muted-foreground">
                      {Object.entries(spec.columns).map(([column, description]) => (
                        <li key={column}>
                          <code className="text-foreground">{column}</code> — {description}
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            </section>

            <section>
              <h3 className="mb-2 font-medium">Workflow</h3>
              <ol className="list-decimal space-y-1 pl-5 text-muted-foreground">
                {task.workflow.map((workflowStep) => (
                  <li key={workflowStep}>{workflowStep.replace(/^\d+\.\s*/, "")}</li>
                ))}
              </ol>
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
                  Provisions a DuckDB file with the Postgres source already attached as{" "}
                  <code>pg</code>, plus a local <code>source_accounts_snapshot</code> to build from.
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
                  execute={executeWarehouseSql}
                  placeholder="CREATE TABLE dim_users AS SELECT ... FROM pg.users"
                  starterValue={task.starter_sql}
                  rows={6}
                />
                <Button onClick={handleSimulateChanges} variant="secondary" disabled={simulating}>
                  {simulating ? "Simulating..." : "Simulate Day-2 Changes"}
                </Button>
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
