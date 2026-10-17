import Link from "next/link";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { PageHero } from "@/components/shared/page-hero";
import { PHASE_THEME } from "@/lib/phase-theme";
import { cn } from "@/lib/utils";

const TRACKS = [
  {
    href: "/lakehouse-databases/skill-tree",
    name: "Lakehouse Databases",
    tagline: "ACID on object storage, commits, time travel",
    description:
      "What a table format (Delta/Iceberg-style) actually adds on top of a plain data lake - " +
      "schema enforcement, atomic commits, and querying an older version of a table - on small, " +
      "hand-sized data.",
  },
  {
    href: "/lakehouse/skill-tree",
    name: "Lakehouse Capstone",
    tagline: "Real Delta table, real time travel",
    description:
      "Commit two incremental batches to a real Delta table, dedupe within and across batches, " +
      "then confirm it with real time travel against real Spark.",
  },
];

export default function LakehouseUmbrellaPage() {
  const theme = PHASE_THEME.lakehouse;
  return (
    <div className="space-y-8">
      <PageHero
        title="Lakehouse"
        description="Same split as SQL, NoSQL, Warehouse, and Lake: generic table-format fundamentals on small data first, then the real capstone - a real Delta table against the real feed - right after."
        accentVar="--phase-lakehouse"
      />

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
