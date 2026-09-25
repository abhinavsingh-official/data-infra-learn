"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { ApiError, executeSql } from "@/lib/api";
import type { ExecuteResult } from "@/lib/types";

export function SqlWorkspace({ sessionId }: { sessionId: string }) {
  const [sql, setSql] = useState("");
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<ExecuteResult | null>(null);

  async function runSql() {
    if (!sql.trim()) return;
    setRunning(true);
    try {
      const outcome = await executeSql(sessionId, sql);
      setResult(outcome);
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Could not run that statement.");
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="space-y-3">
      <Textarea
        value={sql}
        onChange={(event) => setSql(event.target.value)}
        placeholder="CREATE TABLE clean_transactions ( ... );"
        rows={8}
        className="font-mono text-sm"
      />
      <Button onClick={runSql} disabled={running || !sql.trim()}>
        {running ? "Running..." : "Run"}
      </Button>

      {result && !result.success && (
        <Alert variant="destructive">
          <AlertTitle>{result.error_code ?? "ERROR"}</AlertTitle>
          <AlertDescription>{result.error_message}</AlertDescription>
        </Alert>
      )}

      {result?.success && result.columns.length > 0 && (
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                {result.columns.map((column) => (
                  <TableHead key={column}>{column}</TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {result.rows.map((row, rowIndex) => (
                <TableRow key={rowIndex}>
                  {row.map((cell, cellIndex) => (
                    <TableCell key={cellIndex} className="font-mono text-xs">
                      {cell === null ? <span className="italic text-muted-foreground">null</span> : String(cell)}
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
          {result.truncated && (
            <p className="border-t px-4 py-2 text-xs text-muted-foreground">
              Truncated to the first 1000 rows.
            </p>
          )}
        </div>
      )}

      {result?.success && result.columns.length === 0 && (
        <p className="text-sm text-muted-foreground">Statement executed successfully.</p>
      )}
    </div>
  );
}
