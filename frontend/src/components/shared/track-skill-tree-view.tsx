import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { SkillTreePath } from "@/components/shared/skill-tree-path";
import { getSkillTree } from "@/lib/api";
import { fetchProgressServerSide } from "@/lib/server-progress";

/** The per-track skill-tree page body - identical shell across tracks
 * (Postgres, SQL Databases, and future paradigms per Module 20), only
 * the backend route prefix, title, and description differ. Extracted
 * once a second track needed the exact same page, per this project's
 * own "promote to shared once a second consumer needs it" convention. */
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

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        <p className="text-muted-foreground">{description}</p>
        {!progress && (
          <p className="text-sm text-muted-foreground">
            Sign in (top right) to save progress and earn XP as you go - the tree itself works
            either way.
          </p>
        )}
      </div>
      <SkillTreePath tree={tree} progress={progress} />
    </div>
  );
}
