import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { LakehouseTask } from "@/lib/types";

export function TaskDetail({ task }: { task: LakehouseTask }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{task.title}</CardTitle>
        <CardDescription>{task.summary}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6 text-sm">
        <section>
          <h3 className="mb-2 font-medium">Source</h3>
          <ul className="space-y-1 text-muted-foreground">
            {Object.entries(task.source).map(([name, description]) => (
              <li key={name}>
                <code className="text-foreground">{name}</code> — {description}
              </li>
            ))}
          </ul>
        </section>

        <section>
          <h3 className="mb-2 font-medium">Workflow</h3>
          <ol className="list-decimal space-y-1 pl-5 text-muted-foreground">
            {task.workflow.map((step) => (
              <li key={step}>{step.replace(/^\d+\.\s*/, "")}</li>
            ))}
          </ol>
        </section>

        <section>
          <h3 className="mb-2 font-medium">
            Required output: <code>{task.required_output.table}</code>
          </h3>
          <ul className="space-y-1 text-muted-foreground">
            {Object.entries(task.required_output.columns).map(([column, spec]) => (
              <li key={column}>
                <code className="text-foreground">{column}</code> — {spec}
              </li>
            ))}
          </ul>
        </section>

        <section>
          <h3 className="mb-2 font-medium">Hints</h3>
          <ul className="list-disc space-y-1 pl-5 text-muted-foreground">
            {task.hints.map((hint) => (
              <li key={hint}>{hint}</li>
            ))}
          </ul>
        </section>
      </CardContent>
    </Card>
  );
}
