import Link from "next/link";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { buttonVariants } from "@/components/ui/button";
import { DailyChallengeView } from "@/components/daily/daily-challenge-view";
import { fetchDailyChallengeServerSide, sessionToken } from "@/lib/server-progress";

export default async function DailyChallengePage() {
  const token = await sessionToken();
  if (!token) {
    return (
      <Alert>
        <AlertTitle>Sign in to get today's challenge</AlertTitle>
        <AlertDescription className="space-y-3">
          <p>The Daily Challenge tracks your streak and XP per user - sign in (top right) to start it.</p>
          <Link href="/" className={buttonVariants({ variant: "outline" })}>
            Back home
          </Link>
        </AlertDescription>
      </Alert>
    );
  }

  const challenge = await fetchDailyChallengeServerSide();
  if (!challenge) {
    return (
      <Alert variant="destructive">
        <AlertTitle>Backend unreachable</AlertTitle>
        <AlertDescription>
          Could not load today's challenge from the API. Make sure the backend is running and reachable.
        </AlertDescription>
      </Alert>
    );
  }

  return <DailyChallengeView challenge={challenge} />;
}
