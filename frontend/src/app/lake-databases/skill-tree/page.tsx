import { TrackSkillTreeView } from "@/components/shared/track-skill-tree-view";

export default function LakeDatabasesSkillTreePage() {
  return (
    <TrackSkillTreeView
      routePrefix="lake-databases-track"
      title="Lake Databases: The Fundamentals"
      description="Schema-on-read vs. schema-on-write, why Parquet beats CSV for analytics, partitioning by date/key, and querying a raw feed whose schema isn't enforced until read time."
    />
  );
}
