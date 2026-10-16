import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { SkillTreePath } from "@/components/shared/skill-tree-path";
import { PageHero } from "@/components/shared/page-hero";
import { getSkillTree } from "@/lib/api";
import { fetchProgressServerSide } from "@/lib/server-progress";

/** The per-track skill-tree page body - identical shell across tracks
 * (Postgres, SQL Databases, and future paradigms per Module 20), only
 * the backend route prefix, title, and description differ. Extracted
 * once a second track needed the exact same page, per this project's
 * own "promote to shared once a second consumer needs it" convention.
 *
 * Module 24: a track's own `paradigm` field (not every one of them is a
 * literal PHASE_THEME key - the fundamentals tracks use their own slugs
 * like "sql-databases") maps to the phase color closest to what it's
 * actually teaching, so all 8 skill-tree pages get a paradigm-colored
 * PageHero from this one edit. */
const PARADIGM_ACCENT: Record<string, string> = {
  postgres: "--phase-postgres",
  "sql-databases": "--phase-postgres",
  nosql: "--phase-nosql",
  "mongo-databases": "--phase-nosql",
  warehouse: "--phase-warehouse",
  "warehouse-databases": "--phase-warehouse",
  lake: "--phase-lake",
  lakehouse: "--phase-lakehouse",
  "pipeline-architecture": "--phase-pipeline-architecture",
};

export async function TrackSkillTreeView({
  routePrefix,
  title,
  description,
}: {
  routePrefix: string;
  title: string;
  description: string;
}) {
  let tree;
  try {
    tree = await getSkillTree(routePrefix);
  } catch {
    return (
      <Alert variant="destructive">
        <AlertTitle>Backend unreachable</AlertTitle>
        <AlertDescription>
          Could not load the skill tree from the API. Make sure the backend is running and
          reachable at the configured API base URL.
        </AlertDescription>
      </Alert>
    );
  }

  const progress = await fetchProgressServerSide();
  const accentVar = PARADIGM_ACCENT[tree.paradigm] ?? "--primary";

  return (
    <div className="space-y-6">
      <PageHero title={title} description={description} accentVar={accentVar} />
      {!progress && (
        <p className="text-sm text-muted-foreground">
          Sign in (top right) to save progress and earn XP as you go - the tree itself works
          either way.
        </p>
      )}
      <SkillTreePath tree={tree} progress={progress} />
    </div>
  );
}
