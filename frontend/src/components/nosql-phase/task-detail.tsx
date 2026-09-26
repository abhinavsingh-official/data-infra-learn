import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { NosqlTask } from "@/lib/types";

export function TaskDetail({ task }: { task: NosqlTask }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{task.title}</CardTitle>
        <CardDescription>{task.summary}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6 text-sm">
        <section>
          <h3 className="mb-2 font-medium">Source</h3>
          <p className="text-muted-foreground">{task.source}</p>
        </section>

        <section>
          <h3 className="mb-2 font-medium">Design questions to answer</h3>
          <ul className="list-disc space-y-1 pl-5 text-muted-foreground">
            {task.design_questions_to_answer.map((question) => (
              <li key={question}>{question}</li>
            ))}
          </ul>
        </section>

        <section>
          <h3 className="mb-2 font-medium">
            Required output: <code>{task.required_output.collection}</code>
          </h3>
          <p className="mb-2 text-muted-foreground">{task.required_output.note}</p>
          <ul className="space-y-1 text-muted-foreground">
            {Object.entries(task.required_output.document_shape).map(([field, spec]) => (
              <li key={field}>
                <code className="text-foreground">{field}</code> — {spec}
              </li>
            ))}
          </ul>
        </section>

        <p className="italic text-muted-foreground">{task.hint}</p>
      </CardContent>
    </Card>
  );
}
