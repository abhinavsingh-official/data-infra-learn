import { TrackSkillTreeView } from "@/components/shared/track-skill-tree-view";

export default function LakehouseDatabasesSkillTreePage() {
  return (
    <TrackSkillTreeView
      routePrefix="lakehouse-databases-track"
      title="Lakehouse Databases: The Fundamentals"
      description="What a table format adds on top of a plain data lake - schema enforcement, atomic commits, and querying an older version of a table via time travel."
    />
  );
}
