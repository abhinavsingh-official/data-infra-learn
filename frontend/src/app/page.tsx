import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

interface StorageParadigm {
  slug: string;
  name: string;
  tagline: string;
  description: string;
  available: boolean;
}

const PARADIGMS: StorageParadigm[] = [
  {
    slug: "postgres",
    name: "Relational (Postgres)",
    tagline: "Schema design, constraints, dirty webhook feeds",
    description:
      "Load a raw JSONB transaction feed into a clean, constrained schema - nulls, duplicate deliveries, late arrivals, schema drift, and Excel-style ID corruption all included.",
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
];

export default function StoragePickerPage() {
  return (
    <div className="space-y-8">
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight">Pick a storage paradigm</h1>
        <p className="text-muted-foreground">
          Same underlying fintech data, five different storage systems. Each one asks you to
          handle the ETL edge cases that actually show up in that paradigm, then grades your
          submission with a real explanation - why it broke, how to fix it, what the tradeoffs
          are.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {PARADIGMS.map((paradigm) => (
          <Link key={paradigm.slug} href={`/${paradigm.slug}`} className="block">
            <Card className="h-full transition-colors hover:border-foreground/30">
              <CardHeader>
                <div className="flex items-center justify-between gap-2">
                  <CardTitle>{paradigm.name}</CardTitle>
                  {!paradigm.available && <Badge variant="secondary">Coming soon</Badge>}
                </div>
                <CardDescription>{paradigm.tagline}</CardDescription>
              </CardHeader>
              <p className="px-6 pb-6 text-sm text-muted-foreground">{paradigm.description}</p>
            </Card>
          </Link>
        ))}
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
