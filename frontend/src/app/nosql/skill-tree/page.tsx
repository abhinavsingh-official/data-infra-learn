import { TrackSkillTreeView } from "@/components/shared/track-skill-tree-view";

export default function NosqlSkillTreePage() {
  return (
    <TrackSkillTreeView
      routePrefix="nosql-phase"
      title="NoSQL: Document Modeling"
      description="One capstone: remodel the relational fintech data as a denormalized account_profiles document."
    />
  );
}
