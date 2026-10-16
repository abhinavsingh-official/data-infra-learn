"use client";

import { useState } from "react";
import { CheckCircle2, XCircle } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import Link from "next/link";
import { Button, buttonVariants } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { ApiError, checkNode } from "@/lib/api";
import type { NodeCheckResult, SkillNodeDto } from "@/lib/types";

// The capstone node's "Begin the full capstone" link used to be
// hardcoded to /postgres (the only capstone that existed when this
// modal was written) - Module 20 added a second one (NoSQL), so this
// maps a node's own task_ref to its real capstone route instead.
const CAPSTONE_HREF: Record<string, string> = {
  postgres: "/postgres",
  nosql: "/nosql/capstone",
  warehouse: "/warehouse/capstone",
  lake: "/lake/capstone",
  lakehouse: "/lakehouse/capstone",
};

function cellText(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

export function RowTable({ rows }: { rows: Record<string, unknown>[] }) {
  if (rows.length === 0) {
    return <p className="text-sm text-muted-foreground">(no rows)</p>;
  }
  const columns = Object.keys(rows[0]);
  return (
    <div className="overflow-x-auto rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            {columns.map((col) => (
              <TableHead key={col} className="whitespace-nowrap font-mono text-xs">
                {col}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((row, i) => (
            <TableRow key={i}>
              {columns.map((col) => (
                <TableCell key={col} className="whitespace-nowrap font-mono text-xs">
                  {cellText(row[col])}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

interface LessonNodeModalProps {
  node: SkillNodeDto;
  paradigm: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onNodeCompleted: () => void;
}

export function LessonNodeModal({ node, paradigm, open, onOpenChange, onNodeCompleted }: LessonNodeModalProps) {
  const [sql, setSql] = useState(node.practice?.starter_sql ?? "");
  const [checking, setChecking] = useState(false);
  const [result, setResult] = useState<NodeCheckResult | null>(null);

  async function handleCheck() {
    if (!sql.trim()) return;
    setChecking(true);
    try {
      const outcome = await checkNode(paradigm, node.id, sql);
      setResult(outcome);
      if (outcome.passed) {
        toast.success(
          outcome.progress?.newly_awarded_xp
            ? `Correct! +${outcome.progress.newly_awarded_xp} XP`
            : "Correct!",
        );
        onNodeCompleted();
      }
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Could not check that submission.");
    } finally {
      setChecking(false);
    }
  }

  const isGradable = node.type === "skill" && node.practice;
  // Mongo Databases track nodes submit a JSON command document through
  // the exact same textarea/field as SQL text (see mongo_node_practice.py's
  // docstring) - only the placeholder needs to say so.
  const isMongoTrack = paradigm === "mongo-databases";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[85vh] max-w-2xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{node.title}</DialogTitle>
          {node.body && <DialogDescription>{node.body}</DialogDescription>}
        </DialogHeader>

        {/* Dialog's own popup is a CSS grid - without min-w-0 here, a wide
        unbreakable child (the <pre> SQL blocks below) makes this grid item
        overflow the dialog's bounds instead of scrolling inside its own
        overflow-x-auto, since a grid item's default min-width is content-based,
        not 0. */}
        <div className="min-w-0 space-y-4">

        {node.type === "intro" && (
          <p className="text-sm leading-relaxed">{node.body}</p>
        )}

        {node.type === "review" && (
          <p className="text-sm leading-relaxed text-muted-foreground">{node.prompt}</p>
        )}

        {node.type === "capstone" && (
          <div className="space-y-3">
            <p className="text-sm leading-relaxed text-muted-foreground">{node.note}</p>
            <Link href={CAPSTONE_HREF[node.task_ref ?? ""] ?? "/start"} className={buttonVariants()}>
              Begin the full capstone
            </Link>
          </div>
        )}

        {isGradable && node.teach && node.practice && (
          <Tabs defaultValue="teach" className="w-full">
            <TabsList>
              <TabsTrigger value="teach">1. Teach</TabsTrigger>
              <TabsTrigger value="practice">2. Practice</TabsTrigger>
              {node.combine && <TabsTrigger value="combine">3. Combine</TabsTrigger>}
            </TabsList>

            <TabsContent value="teach" className="space-y-3">
              <p className="text-sm text-muted-foreground">{node.teach.note}</p>
              <pre className="overflow-x-auto rounded-md border bg-muted/40 p-3 font-mono text-xs">
                {node.teach.sql}
              </pre>
            </TabsContent>

            <TabsContent value="practice" className="space-y-4">
              <p className="text-sm">{node.practice.prompt}</p>

              {/* Multi-table nodes (the SQL Databases track's JOIN node) list
              each table separately; single-table nodes (every other node)
              fall back to the one example_rows set. */}
              {node.practice.tables
                ? node.practice.tables.map((table) => (
                    <div key={table.name}>
                      <p className="mb-1 text-xs font-medium text-muted-foreground">
                        {table.name} ({table.rows.length} row{table.rows.length === 1 ? "" : "s"})
                      </p>
                      <RowTable rows={table.rows} />
                    </div>
                  ))
                : node.practice.example_rows && (
                    <div>
                      <p className="mb-1 text-xs font-medium text-muted-foreground">
                        Example input ({node.practice.example_rows.length} row
                        {node.practice.example_rows.length === 1 ? "" : "s"})
                      </p>
                      <RowTable rows={node.practice.example_rows} />
                    </div>
                  )}

              <Textarea
                value={sql}
                onChange={(e) => setSql(e.target.value)}
                rows={isMongoTrack ? 8 : 6}
                className="font-mono text-sm"
                placeholder={
                  isMongoTrack
                    ? '{ "find": "...", "filter": {} }'
                    : "Write a SELECT against raw_transaction_events..."
                }
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
                  {result.error_message && (
                    <p className="font-mono text-xs text-destructive">{result.error_message}</p>
                  )}
                  {!result.passed && !result.error_message && (
                    <>
                      <p className="text-xs text-muted-foreground">{result.mismatch}</p>
                      <p className="mb-1 text-xs font-medium text-muted-foreground">Your output</p>
                      <RowTable rows={result.actual_rows} />
                    </>
                  )}
                  <p className="mb-1 text-xs font-medium text-muted-foreground">Expected output</p>
                  <RowTable rows={result.expected_rows} />
                </div>
              )}
            </TabsContent>

            {node.combine && (
              <TabsContent value="combine" className="space-y-2">
                <p className="text-sm">{node.combine.prompt}</p>
                <p className="text-xs text-muted-foreground">{node.combine.note}</p>
              </TabsContent>
            )}
          </Tabs>
        )}

        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
