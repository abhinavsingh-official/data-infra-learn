import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

/** A full-bleed glow-blob hero for pages that want the homepage's visual
 * treatment without a plain heading-and-paragraph block. The homepage
 * (`app/page.tsx`) keeps its own hand-tuned version instead of using this
 * directly. `accentVar` lets a paradigm page pass its own `--phase-*`
 * color instead of the default `--primary` red, so the glow reads as
 * "this paradigm" rather than generic brand chrome. */
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
