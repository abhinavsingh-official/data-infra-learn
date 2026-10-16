import Link from "next/link";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { PageHero } from "@/components/shared/page-hero";
import { PHASE_THEME } from "@/lib/phase-theme";
import { cn } from "@/lib/utils";

const TRACKS = [
  {
    href: "/warehouse-databases/skill-tree",
    name: "Warehouse Databases",
    tagline: "Grain, star JOINs, SCD2, fact aggregation",
    description:
      "Kimball's four-step design process on small, hand-sized data - declaring the grain, " +
      "star-schema JOINs, querying a historized dimension, and the analytics queries a star " +
      "schema exists to make easy.",
  },
  {
    href: "/warehouse/skill-tree",
    name: "Warehouse Capstone",
    tagline: "Real star schema, real SCD Type 2",
    description:
      "Build dim_users/dim_accounts/fact_transactions against the real fintech feed on real " +
      "Spark + Delta, then survive a changing dimension - the same four steps, at real scale.",
  },
];

export default function WarehouseUmbrellaPage() {
  const theme = PHASE_THEME.warehouse;
  return (
    <div className="space-y-8">
      <PageHero
        title="Data Warehouse"
        description="Same split as SQL and NoSQL: generic dimensional-modeling fundamentals on small data first, then the real capstone - a star schema against the real feed - right after."
        accentVar="--phase-warehouse"
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
