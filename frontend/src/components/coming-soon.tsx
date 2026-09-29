import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export function ComingSoon({
  name,
  roadmapNote,
}: {
  name: string;
  roadmapNote: string;
}) {
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between gap-2">
            <CardTitle>{name}</CardTitle>
            <Badge variant="secondary">Coming soon</Badge>
          </div>
          <CardDescription>{roadmapNote}</CardDescription>
        </CardHeader>
      </Card>
      <Button variant="outline" nativeButton={false} render={<Link href="/start" />}>
        Back to storage picker
      </Button>
    </div>
  );
}
