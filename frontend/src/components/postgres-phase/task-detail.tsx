import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { PostgresTask } from "@/lib/types";

export function TaskDetail({ task }: { task: PostgresTask }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{task.title}</CardTitle>
        <CardDescription>{task.summary}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6 text-sm">
        <section>
          <h3 className="mb-2 font-medium">Source: {task.source_table}</h3>
          <ul className="space-y-1 text-muted-foreground">
            {Object.entries(task.source_columns).map(([column, description]) => (
              <li key={column}>
                <code className="text-foreground">{column}</code> — {description}
              </li>
            ))}
          </ul>
        </section>

        <section>
          <h3 className="mb-2 font-medium">Edge cases to handle</h3>
          <ul className="list-disc space-y-1 pl-5 text-muted-foreground">
            {task.edge_cases_to_handle.map((edgeCase) => (
              <li key={edgeCase}>{edgeCase}</li>
            ))}
          </ul>
        </section>

        <section>
          <h3 className="mb-2 font-medium">
            Required output: <code>{task.required_output.table}</code>
          </h3>
          <p className="mb-2 text-muted-foreground">{task.required_output.note}</p>
          <ul className="space-y-1 text-muted-foreground">
            {Object.entries(task.required_output.columns).map(([column, spec]) => (
              <li key={column}>
                <code className="text-foreground">{column}</code> — {spec}
              </li>
            ))}
          </ul>
        </section>

        <p className="italic text-muted-foreground">{task.hint}</p>
      </CardContent>
    </Card>
  );
}
