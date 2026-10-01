import Link from "next/link";
import { ArrowRight, Database, FlaskConical, ClipboardCheck, Layers } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { QueryDemo } from "@/components/query-demo";
import { PipelineIllustration } from "@/components/pipeline-illustration";
import { PARADIGM_ICONS } from "@/components/paradigm-icons";
import { PHASE_THEME, type PhaseSlug } from "@/lib/phase-theme";
import { cn } from "@/lib/utils";

const STATS = [
  { value: "5", label: "Storage paradigms" },
  { value: "1M", label: "Simulated transactions" },
  { value: "51,495", label: "Raw feed events" },
  { value: "29", label: "Remediation writeups" },
];

const HOW_IT_WORKS = [
  { icon: Layers, title: "Fundamentals first", body: "Joins, WHERE, GROUP BY - the small stuff before the real mess." },
  { icon: Database, title: "Then the real dataset", body: "One million rows, real production edge cases." },
  { icon: FlaskConical, title: "Write, run, fix", body: "A starter query, a hidden solution if you get stuck." },
  { icon: ClipboardCheck, title: "A real grading report", body: "Root cause and fix - not just a score." },
];

const PARADIGM_PREVIEW: { slug: PhaseSlug; name: string; tagline: string }[] = [
  { slug: "postgres", name: "SQL / Postgres", tagline: "Schemas, joins, constraints" },
  { slug: "nosql", name: "NoSQL", tagline: "The same data, remodeled" },
  { slug: "warehouse", name: "Warehouse", tagline: "Star schemas, SCD" },
  { slug: "lake", name: "Lake", tagline: "Partitioned, schema-on-read" },
  { slug: "lakehouse", name: "Lakehouse", tagline: "ACID on object storage" },
];

export default function HomePage() {
  return (
    <div className="space-y-20">
      <section className="grid items-center gap-10 py-8 lg:grid-cols-[1.1fr_1fr]">
        <div className="space-y-6">
          <h1 className="max-w-xl text-4xl font-semibold tracking-tight text-balance">
            Learn data engineering by fixing what actually breaks
          </h1>
          <p className="max-w-lg text-balance text-muted-foreground">
            Fundamentals first, then one real million-row dataset across five storage
            paradigms - graded with a real fix, not just a score.
          </p>
          <div className="flex gap-3 pt-2">
            <Button size="lg" nativeButton={false} render={<Link href="/start" />}>
              Start learning
              <ArrowRight className="size-4" />
            </Button>
            <Button size="lg" variant="outline" nativeButton={false} render={<Link href="/compare" />}>
              Compare paradigms
            </Button>
          </div>
        </div>
        <QueryDemo />
      </section>

      <section className="rounded-2xl bg-card p-6 shadow-sm sm:p-10">
        <PipelineIllustration />
        <p className="mt-4 text-center text-sm text-muted-foreground">
          Raw, messy, out of order - in. Clean, validated rows - out.
        </p>
      </section>

      <section className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {STATS.map((stat) => (
          <Card key={stat.label} className="text-center shadow-sm">
            <CardContent className="space-y-1 pt-6">
              <p className="text-2xl font-semibold tabular-nums text-primary">{stat.value}</p>
              <p className="text-sm text-muted-foreground">{stat.label}</p>
            </CardContent>
          </Card>
        ))}
      </section>

      <section className="space-y-6">
        <h2 className="text-center text-xl font-semibold tracking-tight">How it works</h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {HOW_IT_WORKS.map((step, index) => (
            <Card key={step.title} className="shadow-sm">
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
          <h2 className="text-xl font-semibold tracking-tight">One dataset, five paradigms</h2>
          <p className="mx-auto max-w-md text-sm text-balance text-muted-foreground">
            Same fintech data, reshaped five ways - see how differently each one models it.
          </p>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          {PARADIGM_PREVIEW.map((paradigm) => {
            const theme = PHASE_THEME[paradigm.slug];
            const Icon = PARADIGM_ICONS[paradigm.slug];
            return (
              <Link key={paradigm.slug} href={`/${paradigm.slug}`} className="block">
                <Card className="h-full text-center shadow-sm transition-transform hover:-translate-y-0.5">
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
