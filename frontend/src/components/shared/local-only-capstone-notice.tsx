import { Terminal } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { PhaseSlug } from "@/lib/phase-theme";
import { PHASE_THEME } from "@/lib/phase-theme";

/** Unset on the hosted deployment, "true" locally - mirrors the backend's
 * enable_spark_phases flag, but is purely frontend copy, not enforcement. */
const SPARK_PHASES_ENABLED = process.env.NEXT_PUBLIC_SPARK_PHASES_ENABLED === "true";

export function sparkPhasesEnabled() {
  return SPARK_PHASES_ENABLED;
}

export function LocalOnlyCapstoneNotice({ phase }: { phase: PhaseSlug }) {
  const theme = PHASE_THEME[phase];
  return (
    <Card className={theme.border}>
      <CardHeader>
        <CardTitle className="text-xl">This capstone runs on real PySpark + Delta Lake</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 text-sm leading-relaxed text-muted-foreground">
        <p>
          That needs a JVM and real memory to run correctly, so the hosted demo doesn&apos;t run it
          live here - it runs it on your own machine instead, in about two minutes.
        </p>
        <div className="flex items-start gap-3 rounded-md border-2 border-panel-edge/40 bg-muted/40 p-4 font-mono text-xs">
          <Terminal className="mt-0.5 size-4 shrink-0 text-foreground" />
          <div className="space-y-1">
            <p className="text-foreground">git clone https://github.com/abhinavsingh-official/data-infra-learn.git</p>
            <p className="text-foreground">cd data-infra-learn &amp;&amp; ./setup.sh &amp;&amp; ./start.sh</p>
          </div>
        </div>
        <p>
          <code className="text-xs">./start.sh</code> brings up Postgres + Mongo in Docker, the
          FastAPI backend, and the Next.js frontend, and prints the local URL once everything is
          healthy - full details in the repo&apos;s README, including the one JDK prerequisite for
          PySpark.
        </p>
      </CardContent>
    </Card>
  );
}
