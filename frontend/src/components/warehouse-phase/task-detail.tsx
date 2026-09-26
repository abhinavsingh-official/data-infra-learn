import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { WarehouseTask } from "@/lib/types";

export function TaskDetail({ task }: { task: WarehouseTask }) {
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
          <h3 className="mb-2 font-medium">Required output</h3>
          <div className="space-y-4">
            {Object.entries(task.required_output).map(([table, spec]) => (
              <div key={table}>
                <p className="mb-1 font-medium">
                  <code>{table}</code>
                </p>
                <p className="mb-1 text-muted-foreground">{spec.note}</p>
                <ul className="space-y-1 text-muted-foreground">
                  {Object.entries(spec.columns).map(([column, description]) => (
                    <li key={column}>
                      <code className="text-foreground">{column}</code> — {description}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </section>

        <section>
          <h3 className="mb-2 font-medium">Workflow</h3>
          <ol className="list-decimal space-y-1 pl-5 text-muted-foreground">
            {task.workflow.map((step) => (
              <li key={step}>{step.replace(/^\d+\.\s*/, "")}</li>
            ))}
          </ol>
        </section>

        <p className="italic text-muted-foreground">{task.hint}</p>
      </CardContent>
    </Card>
  );
}
