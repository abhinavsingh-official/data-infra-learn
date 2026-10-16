"use client";

import { useMemo, useState } from "react";
import { BookOpen, Check, Flag, Lock, RotateCcw, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
import { LessonNodeModal } from "@/components/shared/lesson-node-modal";
import type { ProgressDto, SkillNodeDto, SkillTreeDto } from "@/lib/types";

/** A node that isn't individually gradable (intro/review/capstone) is a
 * pass-through for UNLOCKING the next node - only "skill" nodes actually
 * gate progression, since those are the only ones the backend can grade.
 * That's a separate question from whether it should show a checkmark:
 * an intro node the learner has never opened shouldn't display as
 * already "done" just because it can't block anything. */
function unlocks(node: SkillNodeDto, completedIds: Set<string>): boolean {
  if (node.type !== "skill") return true;
  return completedIds.has(node.id);
}

function isDisplayComplete(node: SkillNodeDto, completedIds: Set<string>, viewedIds: Set<string>): boolean {
  if (node.type === "intro" || node.type === "review") return viewedIds.has(node.id);
  // Capstones are real backend-graded completions too (the real task page
  // posts back under this same node id) - never assume "done" by default,
  // that's exactly the "everything already looks finished" bug.
  return completedIds.has(node.id);
}

const NODE_ICON: Record<SkillNodeDto["type"], typeof BookOpen> = {
  intro: BookOpen,
  skill: Sparkles,
  review: RotateCcw,
  capstone: Flag,
};

// A gentle left/center/right zigzag, Duolingo-style, cycling every 3 nodes.
const OFFSET = ["ml-0", "ml-12", "ml-24", "ml-12"];

interface SkillTreePathProps {
  tree: SkillTreeDto;
  progress: ProgressDto | null;
}

export function SkillTreePath({ tree, progress }: SkillTreePathProps) {
  const [completedIds, setCompletedIds] = useState<Set<string>>(
    () => new Set(progress?.completed_nodes[tree.paradigm] ?? []),
  );
  const [viewedIds, setViewedIds] = useState<Set<string>>(() => new Set());
  const [activeNode, setActiveNode] = useState<SkillNodeDto | null>(null);

  const unlockFlags = useMemo(() => {
    const flags = new Map<string, boolean>();
    tree.nodes.forEach((node) => flags.set(node.id, unlocks(node, completedIds)));
    return flags;
  }, [tree.nodes, completedIds]);

  const completeFlags = useMemo(() => {
    const flags = new Map<string, boolean>();
    tree.nodes.forEach((node) => flags.set(node.id, isDisplayComplete(node, completedIds, viewedIds)));
    return flags;
  }, [tree.nodes, completedIds, viewedIds]);

  function unlockedAt(index: number): boolean {
    if (index === 0) return true;
    return unlockFlags.get(tree.nodes[index - 1].id) ?? false;
  }

  return (
    <div className="mx-auto max-w-md space-y-6 py-4">
      {tree.nodes.map((node, index) => {
        const unlocked = unlockedAt(index);
        const complete = completeFlags.get(node.id) ?? false;
        const Icon = complete ? Check : unlocked ? NODE_ICON[node.type] : Lock;

        return (
          <div key={node.id} className={cn("flex items-center gap-4", OFFSET[index % OFFSET.length])}>
            <button
              type="button"
              disabled={!unlocked}
              onClick={() => setActiveNode(node)}
              className={cn(
                "flex size-16 shrink-0 items-center justify-center rounded-full border-4 transition-colors",
                complete && "border-emerald-600 bg-emerald-500 text-white",
                !complete && unlocked && "border-phase-postgres bg-phase-postgres/10 text-phase-postgres hover:bg-phase-postgres/20",
                !unlocked && "border-muted bg-muted text-muted-foreground cursor-not-allowed",
              )}
              title={node.title}
            >
              <Icon className="size-6" />
            </button>
            <div className="min-w-0">
              <p className={cn("truncate text-sm font-medium", !unlocked && "text-muted-foreground")}>
                {node.title}
              </p>
              <p className="text-xs uppercase tracking-wide text-muted-foreground">{node.type}</p>
            </div>
          </div>
        );
      })}

      {activeNode && (
        <LessonNodeModal
          node={activeNode}
          paradigm={tree.paradigm}
          open={activeNode !== null}
          onOpenChange={(open) => {
            if (!open) {
              if (activeNode.type === "intro" || activeNode.type === "review") {
                setViewedIds((prev) => new Set(prev).add(activeNode.id));
              }
              setActiveNode(null);
            }
          }}
          onNodeCompleted={() => {
            setCompletedIds((prev) => new Set(prev).add(activeNode.id));
          }}
        />
      )}
    </div>
  );
}
