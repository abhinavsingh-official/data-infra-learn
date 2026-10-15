import { TrackSkillTreeView } from "@/components/shared/track-skill-tree-view";

export default function SqlDatabasesSkillTreePage() {
  return (
    <TrackSkillTreeView
      routePrefix="sql-databases-track"
      title="SQL Databases: The Fundamentals"
      description="WHERE, JOIN, GROUP BY/ORDER BY, and NULL handling - generic SQL, before going deep on Postgres specifically."
    />
  );
}
