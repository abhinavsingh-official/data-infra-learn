import Link from "next/link";
import { ArrowRight, Database, FlaskConical, ClipboardCheck, Layers } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { QueryDemo } from "@/components/query-demo";
import { PARADIGM_ICONS } from "@/components/paradigm-icons";
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
    title: "Learn the fundamentals first",
    body: "Joins, WHERE, GROUP BY, ORDER BY - small, hand-sized exercises before the real dataset shows up.",
  },
  {
    icon: Database,
    title: "Then the real dataset",
    body: "The same million-row fintech feed, with the real edge cases that actually show up in production.",
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

const PARADIGM_PREVIEW: { slug: PhaseSlug; name: string; tagline: string }[] = [
  { slug: "postgres", name: "Relational", tagline: "Postgres - schemas, joins, constraints" },
  { slug: "nosql", name: "Document", tagline: "MongoDB - the same data, remodeled" },
  { slug: "warehouse", name: "Warehouse", tagline: "Star schemas, slowly changing dimensions" },
  { slug: "lake", name: "Lake", tagline: "Partitioned Parquet, schema-on-read" },
  { slug: "lakehouse", name: "Lakehouse", tagline: "ACID tables on object storage" },
];

export default function HomePage() {
  return (
    <div className="space-y-20">
      <section className="grid items-center gap-10 py-8 lg:grid-cols-[1.1fr_1fr]">
        <div className="space-y-6">
          <h1 className="max-w-xl text-4xl font-semibold tracking-tight text-balance">
            Learn how ETL actually breaks - and how to fix it - across five storage paradigms
          </h1>
          <p className="max-w-lg text-balance text-muted-foreground">
            Start with the fundamentals - joins, filters, aggregation - then take on one real
            fintech dataset's actual mess: nulls, drift, duplicates, late arrivals. Graded with
            a remediation report, not a bare pass/fail.
          </p>
          <div className="flex gap-3 pt-2">
            <Button size="lg" nativeButton={false} render={<Link href="/start" />}>
              Start learning
              <ArrowRight className="size-4" />
            </Button>
            <Button size="lg" variant="outline" nativeButton={false} render={<Link href="/compare" />}>
              See paradigms compared
            </Button>
          </div>
        </div>
        <QueryDemo />
      </section>

      <section className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {STATS.map((stat) => (
          <Card key={stat.label} className="border-2 text-center shadow-[0_3px_0_0] shadow-border">
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
            <Card key={step.title} className="relative border-2 shadow-[0_3px_0_0] shadow-border">
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

      <section className="space-y-6">
        <div className="space-y-2 text-center">
          <h2 className="text-xl font-semibold tracking-tight">Five paradigms, one real dataset</h2>
          <p className="mx-auto max-w-lg text-sm text-balance text-muted-foreground">
            The same fintech data, reshaped five different ways - see how differently each
            paradigm actually models and visualizes it.
          </p>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          {PARADIGM_PREVIEW.map((paradigm) => {
            const theme = PHASE_THEME[paradigm.slug];
            const Icon = PARADIGM_ICONS[paradigm.slug];
            return (
              <Link key={paradigm.slug} href={`/${paradigm.slug}`} className="block">
                <Card
                  className={cn(
                    "h-full border-2 text-center shadow-[0_3px_0_0] transition-transform hover:-translate-y-0.5",
                    theme.border,
                  )}
                >
                  <CardContent className={cn("flex flex-col items-center gap-2 pt-6", theme.text)}>
                    <Icon className="size-12" />
                    <p className="font-medium text-foreground">{paradigm.name}</p>
                    <p className="text-xs text-muted-foreground">{paradigm.tagline}</p>
                  </CardContent>
                </Card>
              </Link>
            );
          })}
        </div>
        <div className="text-center">
          <Button nativeButton={false} render={<Link href="/start" />}>
            Explore all five
            <ArrowRight className="size-4" />
          </Button>
        </div>
      </section>
    </div>
  );
}
