"use client";

import { useEffect, useState } from "react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { SessionPanel } from "@/components/lake-phase/session-panel";
import { LocalOnlyCapstoneNotice, sparkPhasesEnabled } from "@/components/shared/local-only-capstone-notice";
import { getLakeTask } from "@/lib/api";
import type { LakeTask } from "@/lib/types";

export default function LakePhasePage() {
  const [task, setTask] = useState<LakeTask | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!sparkPhasesEnabled()) return;
    getLakeTask()
      .then(setTask)
      .catch(() => setFailed(true));
  }, []);

  if (!sparkPhasesEnabled()) {
    return <LocalOnlyCapstoneNotice phase="lake" />;
  }

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
