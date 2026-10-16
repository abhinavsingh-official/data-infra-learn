"use client";

import { useEffect, useState } from "react";
import { Check, Flag, Lock, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

const STEPS = [
  { label: "Intro", icon: Sparkles },
  { label: "Edge case 1", icon: Sparkles },
  { label: "Edge case 2", icon: Sparkles },
  { label: "Edge case 3", icon: Sparkles },
  { label: "Capstone", icon: Flag },
];

const OFFSET = ["ml-0", "ml-8", "ml-16", "ml-8", "ml-0"];
const STEP_MS = 1100;

/** A small looping animation of the real skill-tree mechanic - nodes
 * unlock one at a time as the one above them is completed, same zigzag
 * layout as the real SkillTreePath component. Lets a brand-new visitor
 * see how the progression actually works before they've unlocked
 * anything themselves. */
export function SkillTreePreview() {
  const [unlocked, setUnlocked] = useState(1);

  useEffect(() => {
    const interval = setInterval(() => {
      setUnlocked((current) => (current >= STEPS.length ? 1 : current + 1));
    }, STEP_MS);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-3 rounded-2xl border bg-card p-6 shadow-sm">
      {STEPS.map((step, index) => {
        const done = index + 1 < unlocked;
        const active = index + 1 === unlocked;
        const Icon = done ? Check : step.icon;
        return (
          <div key={step.label} className={cn("flex items-center gap-3 transition-all duration-500", OFFSET[index])}>
            <div
              className={cn(
                "flex size-10 shrink-0 items-center justify-center rounded-full border-2 transition-colors duration-500",
                done && "border-success bg-success text-success-foreground",
                active && "border-primary text-primary",
                !done && !active && "border-border text-muted-foreground",
              )}
            >
              {!done && !active ? <Lock className="size-4" /> : <Icon className="size-4" />}
            </div>
            <span
              className={cn(
                "text-sm transition-colors duration-500",
                active ? "font-medium text-foreground" : "text-muted-foreground",
              )}
            >
              {step.label}
            </span>
          </div>
        );
      })}
    </div>
  );
}
