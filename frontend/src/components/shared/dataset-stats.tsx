import type { PhaseSlug } from "@/lib/phase-theme";
import { PHASE_THEME } from "@/lib/phase-theme";
import { cn } from "@/lib/utils";

export interface DatasetStat {
  label: string;
  value: string;
  hint?: string;
}

interface DatasetStatsProps {
  stats: DatasetStat[];
  phase: PhaseSlug;
}

/** The "how much data is actually here" tile row - the user's explicit
 * ask was that row counts shouldn't be hidden until you stumble into
 * them via a query. Real numbers only; each phase's task_content.py
 * supplies them, this just renders whatever it's given. */
export function DatasetStats({ stats, phase }: DatasetStatsProps) {
  const theme = PHASE_THEME[phase];
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4">
      {stats.map((stat) => (
        <div key={stat.label} className={cn("rounded-lg border p-3", theme.border, theme.bg)}>
          <p className={cn("text-lg font-semibold tabular-nums", theme.text)}>{stat.value}</p>
          <p className="text-xs font-medium text-foreground">{stat.label}</p>
          {stat.hint && <p className="mt-0.5 text-xs text-muted-foreground">{stat.hint}</p>}
        </div>
      ))}
    </div>
  );
}
