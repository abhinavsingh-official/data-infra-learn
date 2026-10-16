import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { PageHero } from "@/components/shared/page-hero";
import type { PhaseSlug } from "@/lib/phase-theme";
import { PHASE_THEME } from "@/lib/phase-theme";
import { cn } from "@/lib/utils";

interface StorageParadigm {
  slug: PhaseSlug;
  name: string;
  tagline: string;
  description: string;
  available: boolean;
}

const PARADIGMS: StorageParadigm[] = [
  {
    slug: "postgres",
    name: "SQL (Fundamentals + Postgres)",
    tagline: "Generic SQL, then Postgres-specific depth",
    description:
      "Not one flat paradigm - an umbrella over two tracks: database-agnostic fundamentals (WHERE, JOINs, GROUP BY), then Postgres's own deep internals on a real million-row dirty webhook feed.",
    available: true,
  },
  {
    slug: "nosql",
    name: "NoSQL (MongoDB)",
    tagline: "Document modeling, denormalization",
    description:
      "Remodel the same fintech data as documents instead of rows - what changes, what you trade away, what eventual consistency actually costs you.",
    available: true,
  },
  {
    slug: "warehouse",
    name: "Data Warehouse",
    tagline: "Star schema, slowly changing dimensions",
    description:
      "Dimensional modeling on top of the same source data - fact/dimension tables, SCD Type 2, analytics-shaped queries.",
    available: true,
  },
  {
    slug: "lake",
    name: "Data Lake",
    tagline: "Partitioned Parquet, schema-on-read",
    description:
      "The same data as partitioned Parquet files queried with DuckDB - schema-on-read tradeoffs instead of schema-on-write.",
    available: true,
  },
  {
    slug: "lakehouse",
    name: "Lakehouse",
    tagline: "ACID table semantics on object storage",
    description:
      "Delta/Iceberg-style table semantics on top of the lake layer - batch and incremental append unified under one table format.",
    available: true,
  },
  {
    slug: "pipeline-architecture",
    name: "Pipeline Architecture",
    tagline: "The cross-cutting discipline, named explicitly",
    description:
      "Idempotent pipelines, schema evolution, batch vs. streaming, and monitoring - the same " +
      "edge cases every paradigm above already teaches, pulled together as their own discipline " +
      "instead of staying scattered across five phases' fault types.",
    available: true,
  },
];

export default function StartPage() {
  return (
    <div className="space-y-8">
      <PageHero
        title="Pick a storage paradigm"
        description="Same underlying fintech data, six lenses. Each one asks you to handle the ETL edge cases that actually show up in that paradigm, then grades your submission with a real explanation - why it broke, how to fix it, what the tradeoffs are."
      />

      <div className="grid gap-4 sm:grid-cols-2">
        {PARADIGMS.map((paradigm) => {
          const theme = PHASE_THEME[paradigm.slug];
          const href = paradigm.slug === "postgres" ? "/sql" : `/${paradigm.slug}`;
          return (
            <Link key={paradigm.slug} href={href} className="block">
              <Card className={cn("h-full border-l-4 transition-colors hover:border-foreground/30", theme.border)}>
                <CardHeader>
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className={cn("size-2.5 rounded-full", theme.bgSolid)} />
                      <CardTitle>{paradigm.name}</CardTitle>
                    </div>
                    {!paradigm.available && <Badge variant="secondary">Coming soon</Badge>}
                  </div>
                  <CardDescription className={cn("font-medium", theme.text)}>{paradigm.tagline}</CardDescription>
                </CardHeader>
                <p className="px-6 pb-6 text-sm text-muted-foreground">{paradigm.description}</p>
              </Card>
            </Link>
          );
        })}
      </div>

      <Link href="/compare" className="block">
        <Card className="transition-colors hover:border-foreground/30">
          <CardHeader>
            <CardTitle>See how these compare</CardTitle>
            <CardDescription>
              The same real operation - deduplicating a retried event - expressed across all five
              paradigms side by side, with the real reference query from each one.
            </CardDescription>
          </CardHeader>
        </Card>
      </Link>
    </div>
  );
}
