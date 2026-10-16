import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

/** Module 24: the homepage's full-bleed glow-blob hero, generalized so
 * every other page can get the same visual treatment instead of a plain
 * heading-and-paragraph block - without touching the homepage's own
 * hand-tuned hero (`app/page.tsx`), which stays as-is since it's already
 * shipped and visually signed off. `accentVar` lets a paradigm page pass
 * its own `--phase-*` color instead of the default `--primary` red, so
 * the glow reads as "this paradigm" rather than generic brand chrome. */
export function PageHero({
  title,
  description,
  accentVar = "--primary",
  aside,
}: {
  title: string;
  description?: string;
  accentVar?: string;
  aside?: ReactNode;
}) {
  return (
    <section className="relative left-1/2 right-1/2 -mx-[50vw] w-screen overflow-hidden bg-background py-14">
      <div
        aria-hidden
        className="absolute left-[15%] bottom-[-10rem] size-[26rem] rounded-full opacity-20 blur-[120px]"
        style={{ background: `var(${accentVar})` }}
      />
      <div
        className={cn(
          "relative mx-auto w-full max-w-7xl items-center gap-10 px-6",
          aside ? "grid lg:grid-cols-[1.3fr_1fr]" : "",
        )}
      >
        <div className="space-y-3">
          <h1 className="text-3xl leading-tight font-normal tracking-tight text-balance lg:text-4xl">{title}</h1>
          {description && <p className="max-w-xl text-balance text-muted-foreground">{description}</p>}
        </div>
        {aside && <div className="relative">{aside}</div>}
      </div>
    </section>
  );
}
