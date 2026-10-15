"use client";

import { useEffect, useState } from "react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { SessionPanel } from "@/components/nosql-phase/session-panel";
import { getNosqlTask } from "@/lib/api";
import type { NosqlTask } from "@/lib/types";

export default function NosqlPhasePage() {
  const [task, setTask] = useState<NosqlTask | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    getNosqlTask()
      .then(setTask)
      .catch(() => setFailed(true));
  }, []);

  if (failed) {
    return (
      <Alert variant="destructive">
        <AlertTitle>Backend unreachable</AlertTitle>
        <AlertDescription>
          Could not load the task from the API. Make sure the backend is running
          (`uvicorn app.main:app` from `backend/`, or `python -m app.main`) and reachable at the
          configured API base URL.
        </AlertDescription>
      </Alert>
    );
  }

  if (!task) {
    return <p className="text-sm text-muted-foreground">Loading task...</p>;
  }

  return (
    <div className="space-y-6">
      <SessionPanel task={task} />
    </div>
  );
}
