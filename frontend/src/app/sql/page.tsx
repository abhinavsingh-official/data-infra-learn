import Link from "next/link";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { PHASE_THEME } from "@/lib/phase-theme";
import { cn } from "@/lib/utils";

const TRACKS = [
  {
    href: "/sql-databases/skill-tree",
    name: "SQL Databases",
    tagline: "WHERE, JOINs, GROUP BY/ORDER BY, NULLs",
    description:
      "Generic, database-agnostic fundamentals on small, hand-sized data - the same core SQL whether you end up writing Postgres, MySQL, or SQL Server.",
  },
  {
    href: "/postgres/skill-tree",
    name: "Postgres",
    tagline: "Deep internals, real million-row scale",
    description:
      "The ETL capstone (schema-on-write, dirty webhook feeds) plus deeper tracks on constraints, indexing, transactions, and partitioning - what's actually specific to Postgres.",
  },
];

export default function SqlUmbrellaPage() {
  const theme = PHASE_THEME.postgres;
  return (
    <div className="space-y-8">
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight">SQL</h1>
        <p className="text-muted-foreground">
          SQL isn&apos;t one flat paradigm here - it&apos;s an umbrella over two tracks: the
          generic fundamentals every relational database shares, and the Postgres-specific depth
          beyond them.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {TRACKS.map((track) => (
          <Link key={track.href} href={track.href} className="block">
            <Card className={cn("h-full border-l-4 transition-colors hover:border-foreground/30", theme.border)}>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <span className={cn("size-2.5 rounded-full", theme.bgSolid)} />
                  <CardTitle>{track.name}</CardTitle>
                </div>
                <CardDescription className={cn("font-medium", theme.text)}>{track.tagline}</CardDescription>
              </CardHeader>
              <p className="px-6 pb-6 text-sm text-muted-foreground">{track.description}</p>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
