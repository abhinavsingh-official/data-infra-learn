"use client";

import { useEffect, useState } from "react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { TaskDetail } from "@/components/warehouse-phase/task-detail";
import { SessionPanel } from "@/components/warehouse-phase/session-panel";
import { getWarehouseTask } from "@/lib/api";
import type { WarehouseTask } from "@/lib/types";

export default function WarehousePhasePage() {
  const [task, setTask] = useState<WarehouseTask | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    getWarehouseTask()
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
      <TaskDetail task={task} />
      <SessionPanel />
    </div>
  );
}
