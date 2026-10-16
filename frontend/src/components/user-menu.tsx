import { auth, signIn, signOut } from "@/auth";
import { Button } from "@/components/ui/button";

/** Sign-in is additive, not a gate - every page stays usable signed-out;
 * signing in just lets progress/XP attach to a real account instead of
 * nothing. */
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
