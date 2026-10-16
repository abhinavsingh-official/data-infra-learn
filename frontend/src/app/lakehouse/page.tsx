import { TrackSkillTreeView } from "@/components/shared/track-skill-tree-view";

export default function LakehouseSkillTreePage() {
  return (
    <TrackSkillTreeView
      routePrefix="lakehouse-phase"
      title="Lakehouse: Transaction Log & Time Travel"
      description="One capstone: commit two incremental batches to a real Delta table, dedupe within and across batches, then confirm it with real time travel."
    />
  );
}
