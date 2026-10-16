"use client";

import { useState } from "react";
import { CheckCircle2, Flame, XCircle } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { RowTable } from "@/components/shared/lesson-node-modal";
import { ApiError, checkDailyPython, checkDailySql } from "@/lib/api";
import type { DailyChallengeDto, NodeCheckResult, PythonCheckResult } from "@/lib/types";

const DIFFICULTY_LABEL: Record<number, string> = { 1: "Tier 1", 2: "Tier 2", 3: "Tier 3" };

function SqlChallengeCard({ sql }: { sql: DailyChallengeDto["sql"] }) {
  const [code, setCode] = useState(sql.starter_sql ?? "");
  const [checking, setChecking] = useState(false);
  const [result, setResult] = useState<NodeCheckResult | null>(null);
  const [solvedToday, setSolvedToday] = useState(sql.completed_today);

  async function handleCheck() {
    if (!code.trim()) return;
    setChecking(true);
    try {
      const outcome = await checkDailySql(code);
      setResult(outcome);
      if (outcome.passed) {
        setSolvedToday(true);
        toast.success(outcome.progress?.newly_awarded_xp ? `Correct! +${outcome.progress.newly_awarded_xp} XP` : "Correct!");
      }
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Could not check that submission.");
    } finally {
      setChecking(false);
    }
  }

  return (
    <Card className="space-y-4 p-6">
      <div className="flex items-center justify-between gap-2">
        <CardTitle>Today's SQL Challenge</CardTitle>
        <div className="flex items-center gap-2">
          <Badge variant="secondary">{DIFFICULTY_LABEL[sql.difficulty] ?? `Tier ${sql.difficulty}`}</Badge>
          {solvedToday && (
            <Badge className="gap-1 bg-emerald-600 text-white hover:bg-emerald-600">
              <CheckCircle2 className="size-3.5" /> Solved
            </Badge>
          )}
        </div>
      </div>
      <CardDescription className="text-sm">{sql.prompt}</CardDescription>

      {sql.tables
        ? sql.tables.map((table) => (
            <div key={table.name}>
              <p className="mb-1 text-xs font-medium text-muted-foreground">
                {table.name} ({table.rows.length} row{table.rows.length === 1 ? "" : "s"})
              </p>
              <RowTable rows={table.rows} />
            </div>
          ))
        : sql.example_rows && (
            <div>
              <p className="mb-1 text-xs font-medium text-muted-foreground">
                {sql.table_name} ({sql.example_rows.length} row{sql.example_rows.length === 1 ? "" : "s"})
              </p>
              <RowTable rows={sql.example_rows} />
            </div>
          )}

      <Textarea
        value={code}
        onChange={(e) => setCode(e.target.value)}
        rows={6}
        className="font-mono text-sm"
        placeholder="Write a query against the table(s) above..."
      />
      <Button onClick={handleCheck} disabled={checking}>
        {checking ? "Checking..." : "Check"}
      </Button>

      {result && (
        <div className="space-y-2 rounded-md border p-3">
          <div className="flex items-center gap-2">
            {result.passed ? (
              <Badge className="gap-1 bg-emerald-600 text-white hover:bg-emerald-600">
                <CheckCircle2 className="size-3.5" /> Correct
              </Badge>
            ) : (
              <Badge variant="destructive" className="gap-1">
                <XCircle className="size-3.5" /> Not quite
              </Badge>
            )}
          </div>
          {result.error_message && <p className="font-mono text-xs text-destructive">{result.error_message}</p>}
          {!result.passed && !result.error_message && (
            <>
              <p className="text-xs text-muted-foreground">{result.mismatch}</p>
              <p className="mb-1 text-xs font-medium text-muted-foreground">Your output</p>
              <RowTable rows={result.actual_rows} />
            </>
          )}
        </div>
      )}
    </Card>
  );
}

function PythonChallengeCard({ python }: { python: DailyChallengeDto["python"] }) {
  const [code, setCode] = useState(python.starter_code);
  const [checking, setChecking] = useState(false);
  const [result, setResult] = useState<PythonCheckResult | null>(null);
  const [solvedToday, setSolvedToday] = useState(python.completed_today);

  async function handleCheck() {
    if (!code.trim()) return;
    setChecking(true);
    try {
      const outcome = await checkDailyPython(code);
      setResult(outcome);
      if (outcome.passed) {
        setSolvedToday(true);
        toast.success(outcome.progress?.newly_awarded_xp ? `Correct! +${outcome.progress.newly_awarded_xp} XP` : "Correct!");
      }
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Could not check that submission.");
    } finally {
      setChecking(false);
    }
  }

  return (
    <Card className="space-y-4 p-6">
      <div className="flex items-center justify-between gap-2">
        <CardTitle>Today's Python Challenge</CardTitle>
        <div className="flex items-center gap-2">
          <Badge variant="secondary">{DIFFICULTY_LABEL[python.difficulty] ?? `Tier ${python.difficulty}`}</Badge>
          {solvedToday && (
            <Badge className="gap-1 bg-emerald-600 text-white hover:bg-emerald-600">
              <CheckCircle2 className="size-3.5" /> Solved
            </Badge>
          )}
        </div>
      </div>
      <CardDescription className="text-sm">{python.prompt}</CardDescription>

      <Textarea
        value={code}
        onChange={(e) => setCode(e.target.value)}
        rows={8}
        className="font-mono text-sm"
      />
      <Button onClick={handleCheck} disabled={checking}>
        {checking ? "Checking..." : "Check"}
      </Button>

      {result && (
        <div className="space-y-2 rounded-md border p-3">
          <div className="flex items-center gap-2">
            {result.passed ? (
              <Badge className="gap-1 bg-emerald-600 text-white hover:bg-emerald-600">
                <CheckCircle2 className="size-3.5" /> Correct
              </Badge>
            ) : (
              <Badge variant="destructive" className="gap-1">
                <XCircle className="size-3.5" /> Not quite
              </Badge>
            )}
          </div>
          {result.error_message && <p className="font-mono text-xs text-destructive">{result.error_message}</p>}
          {!result.passed && (
            <ul className="space-y-1 text-xs text-muted-foreground">
              {result.results.map((r, i) => (
                <li key={i} className="font-mono">
                  Test {i + 1}: {r.passed ? "passed" : r.error ? `error - ${r.error}` : `got ${JSON.stringify(r.actual)}`}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </Card>
  );
}

export function DailyChallengeView({ challenge }: { challenge: DailyChallengeDto }) {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <Flame className="size-5 text-orange-500" />
        <h1 className="text-2xl font-semibold tracking-tight">Daily Challenge - {challenge.date}</h1>
      </div>
      <p className="text-muted-foreground">
        One SQL problem and one Python problem, picked fresh today. Solving both keeps your streak alive - a
        new pair rotates in tomorrow, and the difficulty rises as you clear more of them.
      </p>
      <div className="grid gap-6 lg:grid-cols-2">
        <SqlChallengeCard sql={challenge.sql} />
        <PythonChallengeCard python={challenge.python} />
      </div>
    </div>
  );
}
