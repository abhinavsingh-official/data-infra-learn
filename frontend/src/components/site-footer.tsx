import Link from "next/link";

export function SiteFooter() {
  return (
    <footer className="border-t">
      <div className="mx-auto max-w-5xl px-6 py-10">
        <div className="grid gap-8 sm:grid-cols-3">
          <div className="space-y-2">
            <p className="font-semibold tracking-tight">data-infra-learn</p>
            <p className="text-sm text-muted-foreground">
              One real fintech dataset, five storage paradigms, real ETL edge cases - learn
              by fixing what actually breaks.
            </p>
          </div>
          <div className="space-y-2 text-sm">
            <p className="font-medium">Platform</p>
            <nav className="flex flex-col gap-1.5 text-muted-foreground">
              <Link href="/start" className="hover:text-foreground">Start learning</Link>
              <Link href="/compare" className="hover:text-foreground">Compare paradigms</Link>
              <Link href="/learn" className="hover:text-foreground">Remediation catalog</Link>
            </nav>
          </div>
          <div className="space-y-2 text-sm">
            <p className="font-medium">About this project</p>
            <p className="text-muted-foreground">
              An independent learning project - not affiliated with or endorsed by Postgres,
              MongoDB, or any other project it teaches concepts from.
            </p>
          </div>
        </div>
        <p className="mt-8 border-t pt-6 text-xs text-muted-foreground">
          Synthetic data only - no real transactions, users, or companies. Homepage photos by
          Emile Perron and Luke Chesser via{" "}
          <a href="https://unsplash.com" className="underline hover:text-foreground">
            Unsplash
          </a>
          , used under the Unsplash License.
        </p>
      </div>
    </footer>
  );
}
