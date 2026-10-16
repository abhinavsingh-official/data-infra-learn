import { TrackSkillTreeView } from "@/components/shared/track-skill-tree-view";

export default function LakeSkillTreePage() {
  return (
    <TrackSkillTreeView
      routePrefix="lake-phase"
      title="Data Lake: Schema-on-Read"
      description="One capstone: write the feed as partitioned Parquet, then read it back schema-on-read, absorbing renamed fields and deduping redelivered events."
    />
  );
}
