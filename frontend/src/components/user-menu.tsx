import { auth, signIn, signOut } from "@/auth";
import { Button } from "@/components/ui/button";

/** Module 15. Sign-in is additive, not a gate - per the still-open question
 * in MODULE_13_PLAN.md ("does sign-in gate the whole platform, or only
 * progress-tracking"), the default here is the more welcoming option:
 * every page stays usable signed-out, sign-in just has nothing to attach
 * progress to yet (that's Module 16). */
export async function UserMenu() {
  const session = await auth();

  if (!session?.user) {
    return (
      <form
        action={async () => {
          "use server";
          await signIn("google");
        }}
      >
        <Button type="submit" size="sm" variant="outline">
          Sign in
        </Button>
      </form>
    );
  }

  return (
    <form
      action={async () => {
        "use server";
        await signOut();
      }}
      className="flex items-center gap-2"
    >
      <span className="text-sm text-muted-foreground">{session.user.name ?? session.user.email}</span>
      <Button type="submit" size="sm" variant="ghost">
        Sign out
      </Button>
    </form>
  );
}
