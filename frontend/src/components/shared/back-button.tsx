"use client";

import { ArrowLeft } from "lucide-react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";

/** An in-page back affordance - a learner several steps deep in a skill
 * tree or capstone session shouldn't have to reach for their browser's
 * own back button to retrace a step. */
export function BackButton({ fallbackHref = "/start" }: { fallbackHref?: string }) {
  const router = useRouter();

  return (
    <Button
      variant="ghost"
      size="sm"
      className="gap-1.5 text-muted-foreground hover:text-foreground"
      onClick={() => {
        if (window.history.length > 1) {
          router.back();
        } else {
          router.push(fallbackHref);
        }
      }}
    >
      <ArrowLeft className="size-4" />
      Back
    </Button>
  );
}
