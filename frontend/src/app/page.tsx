import Link from "next/link";
import { ArrowRight, Database, FlaskConical, ClipboardCheck, Layers } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { PHASE_THEME, type PhaseSlug } from "@/lib/phase-theme";
import { cn } from "@/lib/utils";

const STATS = [
  { value: "5", label: "Storage paradigms", hint: "Postgres, MongoDB, warehouse, lake, lakehouse" },
  { value: "1,000,000", label: "Simulated transactions", hint: "one fintech company's data, shared across every paradigm" },
  { value: "51,495", label: "Raw feed events", hint: "with ~7,753 deliberately injected faults" },
  { value: "29", label: "Real remediation writeups", hint: "not pass/fail - why it broke, how to fix it, the tradeoffs" },
];

const HOW_IT_WORKS = [
  {
    icon: Layers,
    title: "Pick a storage paradigm",
    body: "The same fintech data, reshaped five different ways - rows, documents, a star schema, partitioned files, a Delta table.",
  },
  {
    icon: Database,
    title: "See the real dataset first",
    body: "Row counts, known-good result sizes, and the exact edge cases hiding in the feed - before you write a line of code.",
  },
  {
    icon: FlaskConical,
    title: "Write, run, and fix",
    body: "A starter query gets you moving; a hidden reference solution is there if you get stuck, not before.",
  },
  {
    icon: ClipboardCheck,
    title: "Get a real grading report",
    body: "Per-edge-case findings with the actual root cause and fix - not just a score.",
  },
];

const PARADIGM_PREVIEW: { slug: PhaseSlug; name: string }[] = [
  { slug: "postgres", name: "Relational" },
  { slug: "nosql", name: "Document" },
  { slug: "warehouse", name: "Warehouse" },
  { slug: "lake", name: "Lake" },
  { slug: "lakehouse", name: "Lakehouse" },
];

export default function HomePage() {
  return (
    <div className="space-y-16">
      <section className="space-y-6 py-8 text-center">
        <h1 className="mx-auto max-w-2xl text-4xl font-semibold tracking-tight text-balance">
          Learn how ETL actually breaks - and how to fix it - across five storage paradigms
        </h1>
        <p className="mx-auto max-w-xl text-balance text-muted-foreground">
          One real fintech dataset, reshaped five different ways. Real edge cases - nulls, drift,
          duplicates, late arrivals - injected on purpose, graded with a remediation report instead
          of a bare pass/fail.
        </p>
        <div className="flex justify-center gap-3 pt-2">
          <Button size="lg" nativeButton={false} render={<Link href="/start" />}>
            Start learning
            <ArrowRight className="size-4" />
          </Button>
          <Button size="lg" variant="outline" nativeButton={false} render={<Link href="/compare" />}>
            See paradigms compared
          </Button>
        </div>
      </section>

      <section className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {STATS.map((stat) => (
          <Card key={stat.label} className="text-center">
            <CardContent className="space-y-1 pt-6">
              <p className="text-2xl font-semibold tabular-nums text-primary">{stat.value}</p>
              <p className="text-sm font-medium">{stat.label}</p>
              <p className="text-xs text-muted-foreground">{stat.hint}</p>
            </CardContent>
          </Card>
        ))}
      </section>

      <section className="space-y-6">
        <h2 className="text-center text-xl font-semibold tracking-tight">How it works</h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {HOW_IT_WORKS.map((step, index) => (
            <Card key={step.title} className="relative">
              <CardContent className="space-y-2 pt-6">
                <div className="flex items-center gap-2">
                  <span className="flex size-7 items-center justify-center rounded-full bg-primary text-xs font-medium text-primary-foreground">
                    {index + 1}
                  </span>
                  <step.icon className="size-4 text-muted-foreground" />
                </div>
                <p className="font-medium">{step.title}</p>
                <p className="text-sm text-muted-foreground">{step.body}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      <section className="space-y-4 text-center">
        <h2 className="text-xl font-semibold tracking-tight">Five paradigms, one real problem each time</h2>
        <div className="flex flex-wrap justify-center gap-3">
          {PARADIGM_PREVIEW.map((paradigm) => {
            const theme = PHASE_THEME[paradigm.slug];
            return (
              <span
                key={paradigm.slug}
                className={cn("flex items-center gap-2 rounded-full border px-4 py-1.5 text-sm", theme.border, theme.bg)}
              >
                <span className={cn("size-2 rounded-full", theme.bgSolid)} />
                {paradigm.name}
              </span>
            );
          })}
        </div>
        <div>
          <Button nativeButton={false} render={<Link href="/start" />}>
            Explore all five
            <ArrowRight className="size-4" />
          </Button>
        </div>
      </section>
    </div>
  );
}
