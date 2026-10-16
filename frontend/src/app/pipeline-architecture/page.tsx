import { TrackSkillTreeView } from "@/components/shared/track-skill-tree-view";

export default function PipelineArchitectureSkillTreePage() {
  return (
    <TrackSkillTreeView
      routePrefix="pipeline-architecture-track"
      title="Pipeline Architecture"
      description="Idempotent pipelines, schema evolution, batch vs. streaming, and monitoring - the cross-cutting ETL discipline underneath every paradigm, named explicitly and practiced once on its own."
    />
  );
}
