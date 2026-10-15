import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { SkillTreePath } from "@/components/postgres-phase/skill-tree-path";
import { getSkillTree } from "@/lib/api";
import { fetchProgressServerSide } from "@/lib/server-progress";

export default async function PostgresSkillTreePage() {
  let tree;
  try {
    tree = await getSkillTree("postgres");
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
        <h1 className="text-2xl font-semibold tracking-tight">Postgres: Relational Storage</h1>
        <p className="text-muted-foreground">
          Work through each edge case one at a time, then combine everything in the real capstone.
        </p>
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
