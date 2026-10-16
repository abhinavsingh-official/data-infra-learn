import Link from "next/link";
import { ArrowRight, Check, Database, FlaskConical, Trophy } from "lucide-react";
import { Button } from "@/components/ui/button";
import { PageHero } from "@/components/shared/page-hero";
import { SkillTreePreview } from "@/components/start/skill-tree-preview";

const HOW_IT_WORKS = [
  {
    icon: Check,
    title: "Nodes unlock one at a time",
    body: "Finish one small exercise, the next one unlocks - just like the preview on the right. Nothing is thrown at you before you're ready for it.",
  },
  {
    icon: Database,
    title: "You pick the approach",
    body: "Postgres, MongoDB, a Spark warehouse, a data lake, a lakehouse, or the cross-cutting pipeline discipline - six different lenses on the exact same dataset.",
  },
  {
    icon: FlaskConical,
    title: "You write real code, not multiple choice",
    body: "Every exercise is a real SQL or Python submission against real (small, safe) data - checked instantly, with a starter query if you want a nudge.",
  },
  {
    icon: Trophy,
    title: "The last node is always the real thing",
    body: "Each tree ends in a capstone against the full-scale dataset, graded like a real code review - what broke, why, and how to fix it.",
  },
];

export default function StartPage() {
  return (
    <div className="space-y-14">
      <PageHero
        title="Here's how it actually works"
        description="No quizzes, no videos to sit through - a short guided path per approach, each one ending in a real exercise against real data."
        aside={<SkillTreePreview />}
      />

      <section className="grid gap-5 sm:grid-cols-2">
        {HOW_IT_WORKS.map((item) => (
          <div key={item.title} className="flex gap-3 rounded-xl border bg-card p-5">
            <item.icon className="size-5 shrink-0 text-primary" />
            <div className="space-y-1">
              <p className="font-medium">{item.title}</p>
              <p className="text-sm text-muted-foreground">{item.body}</p>
            </div>
          </div>
        ))}
      </section>

      <section className="flex flex-col items-center gap-4 rounded-2xl border bg-card py-12 text-center">
        <p className="text-xl font-medium">Ready to pick an approach?</p>
        <p className="max-w-md text-sm text-muted-foreground">
          All six tracks, what each one teaches, and how they compare - one page.
        </p>
        <Button size="lg" nativeButton={false} render={<Link href="/learn" />}>
          Go to Learn
          <ArrowRight className="size-4" />
        </Button>
      </section>
    </div>
  );
}
