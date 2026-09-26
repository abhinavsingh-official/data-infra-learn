"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ApiError, commitLakehouseBatch } from "@/lib/api";
import type { CommitBatchResult } from "@/lib/types";

export function CommitBatchBox({ sessionId, label }: { sessionId: string; label: string }) {
  const [sql, setSql] = useState("");
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<CommitBatchResult | null>(null);

  async function commit() {
    if (!sql.trim()) return;
    setRunning(true);
    try {
      const outcome = await commitLakehouseBatch(sessionId, sql);
      setResult(outcome);
      if (outcome.success) {
        toast(`Committed as Delta version ${outcome.version} - ${outcome.row_count} rows.`);
      }
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Could not commit that batch.");
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="space-y-3">
      <p className="text-sm font-medium">{label}</p>
      <Textarea
        value={sql}
        onChange={(event) => setSql(event.target.value)}
        placeholder="SELECT event_id, amount, merchant, currency, event_timestamp FROM ..."
        rows={6}
        className="font-mono text-sm"
      />
      <Button onClick={commit} disabled={running || !sql.trim()}>
        {running ? "Committing..." : "Commit Batch"}
      </Button>

      {result && !result.success && (
        <Alert variant="destructive">
          <AlertTitle>{result.error_code ?? "ERROR"}</AlertTitle>
          <AlertDescription>{result.error_message}</AlertDescription>
        </Alert>
      )}

      {result?.success && (
        <p className="text-sm text-muted-foreground">
          Committed as Delta version <code>{result.version}</code> — {result.row_count} rows.
        </p>
      )}
    </div>
  );
}
