import Link from "next/link";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { PageHero } from "@/components/shared/page-hero";
import { PHASE_THEME } from "@/lib/phase-theme";
import { cn } from "@/lib/utils";

const TRACKS = [
  {
    href: "/lake-databases/skill-tree",
    name: "Lake Databases",
    tagline: "Schema-on-read, file formats, partitioning",
    description:
      "Schema-on-read vs. schema-on-write, why Parquet beats CSV for analytics, partitioning " +
      "by date/key, and dealing with a raw feed where the schema isn't enforced until you " +
      "query it - on small, hand-sized data.",
  },
  {
    href: "/lake/skill-tree",
    name: "Lake Capstone",
    tagline: "Real partitioned Parquet, real schema-on-read",
    description:
      "Write the real fintech feed as partitioned Parquet, then read it back schema-on-read, " +
      "absorbing renamed fields and deduping redelivered events on real Spark.",
  },
];

export default function LakeUmbrellaPage() {
  const theme = PHASE_THEME.lake;
  return (
    <div className="space-y-8">
      <PageHero
        title="Data Lake"
        description="Same split as SQL, NoSQL, and Warehouse: generic schema-on-read fundamentals on small data first, then the real capstone - partitioned Parquet against the real feed - right after."
        accentVar="--phase-lake"
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
