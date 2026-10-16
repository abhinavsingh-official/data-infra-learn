import Link from "next/link";
import Image from "next/image";
import { ArrowRight, Database, FlaskConical, ClipboardCheck, Layers, GitBranch, BarChart3, Boxes } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { QueryDemo } from "@/components/query-demo";
import { PHASE_THEME, type PhaseSlug } from "@/lib/phase-theme";
import { cn } from "@/lib/utils";

const STATS = [
  { value: "5", label: "Storage paradigms", hint: "One shared fintech dataset, five different models - see how differently each one represents the same data." },
  { value: "1,000,000", label: "Simulated transactions", hint: "Not a toy sample - a real production-scale feed with the volume problems that only show up at scale." },
  { value: "51,495", label: "Raw feed events", hint: "With roughly 7,753 deliberately injected faults - nulls, duplicates, drift, late arrivals." },
  { value: "29", label: "Remediation writeups", hint: "Every failure comes with a root cause, a fix, and the tradeoffs between valid fixes - not a bare score." },
];

const HOW_IT_WORKS = [
  { icon: Layers, title: "Fundamentals first", body: "Joins, WHERE, GROUP BY, ORDER BY - small, hand-sized exercises before the real dataset shows up." },
  { icon: Database, title: "Then the real dataset", body: "The same million-row feed every exercise has been building toward, with the edge cases that actually show up in production." },
  { icon: FlaskConical, title: "Write, run, fix", body: "A starter query gets you moving. A hidden reference solution is there if you get stuck - not before." },
  { icon: ClipboardCheck, title: "A real grading report", body: "Per-edge-case findings with the actual root cause and fix, so you learn why it broke, not just that it did." },
];

const PARADIGM_PREVIEW: { slug: PhaseSlug; name: string; tagline: string; detail: string; logo?: string; icon?: typeof GitBranch }[] = [
  { slug: "postgres", name: "SQL / Postgres", tagline: "Schemas, joins, constraints", detail: "Fundamentals, then deep internals", logo: "/images/logos/postgresql.svg" },
  { slug: "nosql", name: "NoSQL", tagline: "The same data, remodeled", detail: "Embedding vs. referencing, for real", logo: "/images/logos/mongodb.svg" },
  { slug: "warehouse", name: "Warehouse", tagline: "Star schemas, SCD", detail: "Kimball's own design process", icon: BarChart3 },
  { slug: "lake", name: "Lake", tagline: "Partitioned, schema-on-read", detail: "Parquet internals, partition pruning", icon: Boxes },
  { slug: "lakehouse", name: "Lakehouse", tagline: "ACID on object storage", detail: "Delta commits and time travel", icon: GitBranch },
];

const TECH_LOGOS = [
  { name: "PostgreSQL", src: "/images/logos/postgresql.svg" },
  { name: "MongoDB", src: "/images/logos/mongodb.svg" },
  { name: "Python", src: "/images/logos/python.svg" },
  { name: "Apache Spark", src: "/images/logos/apachespark.svg" },
];

export default function HomePage() {
  return (
    <div className="space-y-24">
      <section className="relative left-1/2 right-1/2 -mx-[50vw] w-screen overflow-hidden bg-background py-20">
        <div
          aria-hidden
          className="absolute left-[15%] bottom-[-12rem] size-[32rem] rounded-full bg-primary opacity-20 blur-[140px]"
        />
        <div className="relative mx-auto grid w-full max-w-7xl items-center gap-12 px-6 lg:grid-cols-2">
          <div className="space-y-5">
            <h1 className="text-6xl leading-[0.95] font-normal tracking-tight text-balance">
              Learn data engineering by fixing what actually breaks
            </h1>
            <p className="max-w-md text-lg text-balance text-muted-foreground">
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
          <div className="relative">
            <QueryDemo />
          </div>
        </div>
      </section>

      <section className="grid gap-10 lg:grid-cols-[1.2fr_1fr] lg:items-center">
        <div className="space-y-4">
          <h2 className="text-2xl font-semibold tracking-tight">What this actually is</h2>
          <p className="text-muted-foreground">
            Most SQL courses teach you to query data that's already clean. Real data
            engineering work is mostly the opposite: a feed arrives with missing fields,
            duplicate deliveries, and records that showed up three days late, and it's your
            job to figure out why and fix it correctly.
          </p>
          <p className="text-muted-foreground">
            This platform simulates that - one real fintech company's data, generated at
            real scale, with real faults injected on purpose. You learn the fundamentals of
            each storage paradigm first, then take on the same dataset's actual mess, and get
            graded the way a real code review would: here's what broke, here's why, here's
            how to fix it.
          </p>
          <div className="flex flex-wrap items-center gap-x-6 gap-y-3 pt-2">
            {TECH_LOGOS.map((logo) => (
              <Image key={logo.name} src={logo.src} alt={logo.name} width={28} height={28} className="h-7 w-auto opacity-70" />
            ))}
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4">
          {STATS.map((stat) => (
            <Card key={stat.label} className="shadow-sm">
              <CardContent className="space-y-1.5 pt-6">
                <p className="text-3xl font-semibold tabular-nums text-primary">{stat.value}</p>
                <p className="text-sm font-medium">{stat.label}</p>
                <p className="text-xs text-muted-foreground">{stat.hint}</p>
              </CardContent>
            </Card>
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
            return (
              <Link key={paradigm.slug} href={`/${paradigm.slug}`} className="block">
                <Card className="h-full text-center shadow-sm transition-transform hover:-translate-y-0.5">
                  <CardContent className="flex flex-col items-center gap-2 pt-6">
                    {paradigm.logo ? (
                      <Image src={paradigm.logo} alt={paradigm.name} width={40} height={40} className="size-10" />
                    ) : paradigm.icon ? (
                      <paradigm.icon className={cn("size-10", theme.text)} />
                    ) : null}
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
