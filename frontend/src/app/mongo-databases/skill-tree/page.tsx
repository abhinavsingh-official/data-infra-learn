import { TrackSkillTreeView } from "@/components/shared/track-skill-tree-view";

export default function MongoDatabasesSkillTreePage() {
  return (
    <TrackSkillTreeView
      routePrefix="mongo-databases-track"
      title="MongoDB Databases: The Fundamentals"
      description="Querying, referencing, aggregating, and handling missing fields - the document-model basics every MongoDB course starts with."
    />
  );
}
