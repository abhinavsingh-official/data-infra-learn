"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Stepper } from "@/components/shared/stepper";
import { DatasetStats } from "@/components/shared/dataset-stats";
import { ReferenceSolution } from "@/components/shared/reference-solution";
import { ApiError, createNosqlSession, endNosqlSession, gradeNosqlSession } from "@/lib/api";
import type { NosqlGradingReport, NosqlTask } from "@/lib/types";
import { GradingReportView } from "./grading-report";
import { MongoExecuteBox } from "./mongo-execute-box";
import { SourceQueryBox } from "./source-query-box";

const STEPS = ["Overview", "The task", "Explore & write", "Grade"];

export function SessionPanel({ task }: { task: NosqlTask }) {
  const [step, setStep] = useState(0);
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
      const result = await gradeNosqlSession(sessionId);
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
      await endNosqlSession(sessionId);
      setSessionId(null);
      setReport(null);
      setStep(0);
      toast("Session ended - your Mongo database and Postgres read-only role were torn down.");
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Could not end the session.");
    } finally {
      setEnding(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <Stepper steps={STEPS} currentIndex={step} phase="nosql" />
      </CardHeader>
      <CardContent className="space-y-4">
        {step === 0 && (
          <div className="space-y-4">
            <div>
              <CardTitle className="mb-1">{task.title}</CardTitle>
              <CardDescription>{task.summary}</CardDescription>
            </div>
            <DatasetStats stats={task.dataset_stats} phase="nosql" />
            <div className="flex justify-end">
              <Button onClick={() => setStep(1)}>Next: the task</Button>
            </div>
          </div>
        )}

        {step === 1 && (
          <div className="space-y-6 text-sm">
            <section>
              <h3 className="mb-2 font-medium">Source</h3>
              <p className="text-muted-foreground">{task.source}</p>
            </section>

            <section>
              <h3 className="mb-2 font-medium">Design questions to answer</h3>
              <ul className="list-disc space-y-1 pl-5 text-muted-foreground">
                {task.design_questions_to_answer.map((question) => (
                  <li key={question}>{question}</li>
                ))}
              </ul>
            </section>

            <section>
              <h3 className="mb-2 font-medium">
                Required output: <code>{task.required_output.collection}</code>
              </h3>
              <p className="mb-2 text-muted-foreground">{task.required_output.note}</p>
              <ul className="space-y-1 text-muted-foreground">
                {Object.entries(task.required_output.document_shape).map(([field, spec]) => (
                  <li key={field}>
                    <code className="text-foreground">{field}</code> — {spec}
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
                  Provisions read-only access to the relational source tables and a Mongo database
                  scoped just to you.
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
                <div>
                  <h3 className="mb-2 text-sm font-medium">1. Query the Postgres source</h3>
                  <SourceQueryBox sessionId={sessionId} />
                </div>
                <Separator />
                <div>
                  <h3 className="mb-2 text-sm font-medium">2. Build account_profiles in Mongo</h3>
                  <MongoExecuteBox sessionId={sessionId} starterValue={task.starter_command} />
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
