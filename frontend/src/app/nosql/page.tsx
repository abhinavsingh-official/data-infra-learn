import Link from "next/link";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { PHASE_THEME } from "@/lib/phase-theme";
import { cn } from "@/lib/utils";

const TRACKS = [
  {
    href: "/mongo-databases/skill-tree",
    name: "MongoDB Databases",
    tagline: "find, $lookup, $group/$sort, $ifNull",
    description:
      "The document-model fundamentals on small, hand-sized collections - querying, " +
      "referencing across collections, aggregating, and what 'no value' means without a NULL type.",
  },
  {
    href: "/nosql/skill-tree",
    name: "NoSQL Capstone",
    tagline: "Document modeling, denormalization",
    description:
      "Remodel the same relational fintech data as one denormalized account_profiles document, " +
      "at real 15,000-account scale - what to embed, cap, and aggregate is the actual exercise.",
  },
];

export default function NosqlUmbrellaPage() {
  const theme = PHASE_THEME.nosql;
  return (
    <div className="space-y-8">
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight">NoSQL</h1>
        <p className="text-muted-foreground">
          Same split as SQL: generic MongoDB fundamentals on small data first, then the real
          capstone - remodeling the whole fintech dataset as documents - right after.
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
