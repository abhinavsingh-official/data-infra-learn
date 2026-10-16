import { TrackSkillTreeView } from "@/components/shared/track-skill-tree-view";

export default function WarehouseSkillTreePage() {
  return (
    <TrackSkillTreeView
      routePrefix="warehouse-phase"
      title="Data Warehouse: Star Schema"
      description="One capstone: build dim_users/dim_accounts/fact_transactions against the real fintech feed, then survive a Slowly Changing Dimension."
    />
  );
}
