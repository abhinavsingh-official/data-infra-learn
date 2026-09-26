"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { ApiError, querySource } from "@/lib/api";
import type { QuerySourceResult } from "@/lib/types";

export function SourceQueryBox({ sessionId }: { sessionId: string }) {
  const [sql, setSql] = useState("SELECT * FROM accounts LIMIT 10");
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<QuerySourceResult | null>(null);

  async function run() {
    if (!sql.trim()) return;
    setRunning(true);
    try {
      setResult(await querySource(sessionId, sql));
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Could not query the source.");
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="space-y-3">
      <Textarea
        value={sql}
        onChange={(event) => setSql(event.target.value)}
        rows={3}
        className="font-mono text-sm"
      />
      <Button onClick={run} disabled={running || !sql.trim()}>
        {running ? "Querying..." : "Query source"}
      </Button>

      {result && !result.success && (
        <Alert variant="destructive">
          <AlertTitle>{result.error_code ?? "ERROR"}</AlertTitle>
          <AlertDescription>{result.error_message}</AlertDescription>
        </Alert>
      )}

      {result?.success && result.columns.length > 0 && (
        <div className="max-h-80 overflow-auto rounded-md border">
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
            <p className="border-t px-4 py-2 text-xs text-muted-foreground">Truncated to the first 1000 rows.</p>
          )}
        </div>
      )}
    </div>
  );
}
