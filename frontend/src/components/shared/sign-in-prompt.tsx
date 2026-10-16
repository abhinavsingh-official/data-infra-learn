import { Sparkles } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

/** A visible nudge to sign in, not a buried line of muted text - progress,
 * XP, and streaks only ever attach to a real account, so a signed-out
 * visitor should actually notice this instead of scrolling past it. */
export function SignInPrompt() {
  return (
    <Card className="border-primary/30 bg-primary/5">
      <CardContent className="flex items-center gap-3 py-4">
        <Sparkles className="size-5 shrink-0 text-primary" />
        <p className="text-sm">
          <span className="font-medium">Sign in</span>
          <span className="text-muted-foreground"> (top right) to save your progress and start earning XP - everything below still works either way.</span>
        </p>
      </CardContent>
    </Card>
  );
}
