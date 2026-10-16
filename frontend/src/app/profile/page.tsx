import Link from "next/link";
import { Award, Flame, Lock, Sparkles } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import {
  fetchBadgesServerSide,
  fetchCertificatesServerSide,
  fetchProgressServerSide,
  sessionToken,
} from "@/lib/server-progress";

export default async function ProfilePage() {
  const token = await sessionToken();
  if (!token) {
    return (
      <Alert>
        <AlertTitle>Sign in to see your badges and certificates</AlertTitle>
        <AlertDescription className="space-y-3">
          <p>Progress, XP, badges, and certificates are all tied to your signed-in account.</p>
          <Link href="/" className={buttonVariants({ variant: "outline" })}>
            Back home
          </Link>
        </AlertDescription>
      </Alert>
    );
  }

  const [progress, badges, certificates] = await Promise.all([
    fetchProgressServerSide(),
    fetchBadgesServerSide(),
    fetchCertificatesServerSide(),
  ]);

  if (!progress || !badges || !certificates) {
    return (
      <Alert variant="destructive">
        <AlertTitle>Backend unreachable</AlertTitle>
        <AlertDescription>Could not load your profile from the API.</AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="space-y-10">
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight">Your Profile</h1>
        <div className="flex items-center gap-4 text-sm">
          <span className="flex items-center gap-1 text-amber-500">
            <Sparkles className="size-4" /> {progress.xp_total} XP
          </span>
          <span className="flex items-center gap-1 text-orange-500">
            <Flame className="size-4" /> {progress.current_streak}-day streak (best: {progress.longest_streak})
          </span>
        </div>
      </div>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Badges</h2>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4">
          {badges.map((badge) => (
            <Card
              key={badge.badge_id}
              className={cn(
                "flex flex-col items-center gap-2 p-4 text-center",
                !badge.earned && "opacity-40 grayscale",
              )}
            >
              {badge.earned ? <Award className="size-8 text-amber-500" /> : <Lock className="size-8" />}
              <p className="text-xs font-medium">{badge.label}</p>
            </Card>
          ))}
        </div>
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Certificates</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          {Object.entries(certificates).map(([groupId, cert]) => (
            <Card key={groupId} className="space-y-3 p-6">
              <CardHeader className="p-0">
                <div className="flex items-center justify-between gap-2">
                  <CardTitle>{cert.label}</CardTitle>
                  {cert.unlocked && <Badge className="bg-emerald-600 text-white hover:bg-emerald-600">Earned</Badge>}
                </div>
                <CardDescription>
                  {cert.completed} / {cert.total} nodes completed
                </CardDescription>
              </CardHeader>
              <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
                <div
                  className="h-full bg-primary"
                  style={{ width: `${cert.total === 0 ? 0 : Math.round((cert.completed / cert.total) * 100)}%` }}
                />
              </div>
              {cert.unlocked && (
                <Link href={`/certificate/${groupId}`} className={buttonVariants({ variant: "outline", size: "sm" })}>
                  View certificate
                </Link>
              )}
            </Card>
          ))}
        </div>
      </section>
    </div>
  );
}
