import { TrackSkillTreeView } from "@/components/shared/track-skill-tree-view";

export default function PostgresSkillTreePage() {
  return (
    <TrackSkillTreeView
      routePrefix="postgres-phase"
      title="Postgres: Relational Storage"
      description="Work through each edge case one at a time, then combine everything in the real capstone."
    />
  );
}
