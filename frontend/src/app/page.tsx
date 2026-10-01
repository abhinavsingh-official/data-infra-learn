import Link from "next/link";
import Image from "next/image";
import { ArrowRight, Database, FlaskConical, ClipboardCheck, Layers } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { QueryDemo } from "@/components/query-demo";
import { PARADIGM_ICONS } from "@/components/paradigm-icons";
import { PHASE_THEME, type PhaseSlug } from "@/lib/phase-theme";
import { cn } from "@/lib/utils";

const STATS = [
  { value: "5", label: "Storage paradigms", hint: "One shared fintech dataset, five different models" },
  { value: "1,000,000", label: "Simulated transactions", hint: "Not a toy sample - a real production-scale feed" },
  { value: "51,495", label: "Raw feed events", hint: "With ~7,753 deliberately injected faults" },
  { value: "29", label: "Remediation writeups", hint: "Root cause, fix, and the tradeoffs - not a score" },
];

const HOW_IT_WORKS = [
  {
    icon: Layers,
    title: "Fundamentals first",
    body: "Joins, WHERE, GROUP BY, ORDER BY - small, hand-sized exercises before the real dataset shows up.",
  },
  {
    icon: Database,
    title: "Then the real dataset",
    body: "The same million-row feed every exercise has been building toward, with the edge cases that actually show up in production.",
  },
  {
    icon: FlaskConical,
    title: "Write, run, fix",
    body: "A starter query gets you moving. A hidden reference solution is there if you get stuck - not before.",
  },
  {
    icon: ClipboardCheck,
    title: "A real grading report",
    body: "Per-edge-case findings with the actual root cause and fix, so you learn why it broke, not just that it did.",
  },
];

const PARADIGM_PREVIEW: { slug: PhaseSlug; name: string; tagline: string; detail: string }[] = [
  { slug: "postgres", name: "SQL / Postgres", tagline: "Schemas, joins, constraints", detail: "Fundamentals, then deep internals" },
  { slug: "nosql", name: "NoSQL", tagline: "The same data, remodeled", detail: "Embedding vs. referencing, for real" },
  { slug: "warehouse", name: "Warehouse", tagline: "Star schemas, SCD", detail: "Kimball's own design process" },
  { slug: "lake", name: "Lake", tagline: "Partitioned, schema-on-read", detail: "Parquet internals, partition pruning" },
  { slug: "lakehouse", name: "Lakehouse", tagline: "ACID on object storage", detail: "Delta commits and time travel" },
];

export default function HomePage() {
  return (
    <div className="space-y-20">
      <section className="relative overflow-hidden rounded-2xl shadow-lg">
        <Image
          src="/images/hero-code.jpg"
          alt="A laptop showing real code on a desk"
          width={2400}
          height={1350}
          priority
          className="h-[480px] w-full object-cover"
        />
        <div className="absolute inset-0 bg-gradient-to-r from-background via-background/85 to-transparent" />
        <div className="absolute inset-0 flex items-center">
          <div className="max-w-lg space-y-5 px-8 sm:px-12">
            <h1 className="text-4xl font-semibold tracking-tight text-balance">
              Learn data engineering by fixing what actually breaks
            </h1>
            <p className="max-w-md text-balance text-muted-foreground">
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
        </div>
        <div className="absolute right-6 bottom-6 hidden w-80 lg:block xl:w-96">
          <QueryDemo />
        </div>
      </section>

      <section className="relative overflow-hidden rounded-2xl shadow-lg">
        <Image
          src="/images/dashboard.jpg"
          alt="A real analytics dashboard on screen"
          width={2400}
          height={1600}
          className="h-64 w-full object-cover"
        />
        <div className="absolute inset-0 bg-background/70 backdrop-blur-[2px]" />
        <div className="absolute inset-0 grid grid-cols-2 gap-4 p-6 sm:grid-cols-4 sm:p-8">
          {STATS.map((stat) => (
            <div key={stat.label} className="flex flex-col justify-center rounded-xl bg-card/90 p-4 text-center shadow-sm">
              <p className="text-2xl font-semibold tabular-nums text-primary">{stat.value}</p>
              <p className="text-sm font-medium">{stat.label}</p>
              <p className="mt-1 text-xs text-muted-foreground">{stat.hint}</p>
            </div>
          ))}
        </div>
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
                <Card className="h-full text-center shadow-sm transition-transform hover:-translate-y-0.5">
                  <CardContent className={cn("flex flex-col items-center gap-2 pt-6", theme.text)}>
                    <Icon className="size-12" />
                    <p className="font-medium text-foreground">{paradigm.name}</p>
                    <p className="text-xs text-muted-foreground">{paradigm.tagline}</p>
                    <p className="text-xs text-muted-foreground/70">{paradigm.detail}</p>
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
