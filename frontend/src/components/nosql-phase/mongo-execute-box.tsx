"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ApiError, executeMongoCommand } from "@/lib/api";
import type { MongoExecuteResult } from "@/lib/types";

const PLACEHOLDER = `{
  "insert": "account_profiles",
  "documents": [{ "_id": "1", "owner": { "name": "...", "email": "..." } }]
}`;

interface MongoExecuteBoxProps {
  sessionId: string;
  /** Pre-fills the textarea with a runnable-but-incomplete example, same
   * pattern as SqlWorkspace's starterValue - applied once, on mount. */
  starterValue?: string;
}

export function MongoExecuteBox({ sessionId, starterValue = "" }: MongoExecuteBoxProps) {
  const [commandText, setCommandText] = useState(starterValue);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<MongoExecuteResult | null>(null);
  const [parseError, setParseError] = useState<string | null>(null);

  async function run() {
    if (!commandText.trim()) return;
    let command: object;
    try {
      command = JSON.parse(commandText);
    } catch {
      setParseError("That's not valid JSON.");
      return;
    }
    setParseError(null);
    setRunning(true);
    try {
      setResult(await executeMongoCommand(sessionId, command));
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Could not run that command.");
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="space-y-3">
      <Textarea
        value={commandText}
        onChange={(event) => setCommandText(event.target.value)}
        placeholder={PLACEHOLDER}
        rows={14}
        className="font-mono text-base"
      />
      <Button size="lg" onClick={run} disabled={running || !commandText.trim()}>
        {running ? "Running..." : "Run Mongo command"}
      </Button>

      {parseError && (
        <Alert variant="destructive">
          <AlertTitle>Invalid JSON</AlertTitle>
          <AlertDescription>{parseError}</AlertDescription>
        </Alert>
      )}

      {result && !result.success && (
        <Alert variant="destructive">
          <AlertTitle>{result.error_code ?? "ERROR"}</AlertTitle>
          <AlertDescription>{result.error_message}</AlertDescription>
        </Alert>
      )}

      {result?.success && (
        <div className="rounded-md border bg-muted/30 p-3">
          <pre className="max-h-96 overflow-auto text-sm">{JSON.stringify(result.result, null, 2)}</pre>
          {result.truncated && (
            <p className="mt-2 text-xs text-muted-foreground">Truncated to the first 1000 documents.</p>
          )}
        </div>
      )}
    </div>
  );
}
