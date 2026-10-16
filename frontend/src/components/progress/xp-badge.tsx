import { Flame, Sparkles } from "lucide-react";
import { fetchProgressServerSide } from "@/lib/server-progress";

/** Server Component (not client) - reads the session cookie directly,
 * same as UserMenu, so showing XP/streak in the header costs one extra
 * server-side fetch per request, not a client round trip. Renders
 * nothing for a signed-out visitor - XP only exists once there's a real
 * user id to key it by. */
export async function XpBadge() {
  const progress = await fetchProgressServerSide();
  if (!progress) return null;

  return (
    <div className="flex items-center gap-3 text-sm">
      <span className="flex items-center gap-1 text-amber-500" title={`${progress.xp_total} XP`}>
        <Sparkles className="size-4" />
        {progress.xp_total}
      </span>
      {progress.current_streak > 0 && (
        <span className="flex items-center gap-1 text-orange-500" title={`${progress.current_streak}-day streak`}>
          <Flame className="size-4" />
          {progress.current_streak}
        </span>
      )}
    </div>
  );
}
