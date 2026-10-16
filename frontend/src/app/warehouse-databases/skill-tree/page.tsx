import { TrackSkillTreeView } from "@/components/shared/track-skill-tree-view";

export default function WarehouseDatabasesSkillTreePage() {
  return (
    <TrackSkillTreeView
      routePrefix="warehouse-databases-track"
      title="Warehouse Databases: The Fundamentals"
      description="Declaring the grain, star-schema JOINs, querying a historized SCD2 dimension, and fact aggregation - Kimball's four-step process in SQL form."
    />
  );
}
