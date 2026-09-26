import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import type { NosqlGradingReport } from "@/lib/types";

export function GradingReportView({ report }: { report: NosqlGradingReport }) {
  return (
    <div className="space-y-6">
      <Alert variant={report.passed ? "default" : "destructive"}>
        <AlertTitle>{report.passed ? "Passed" : "Not passing yet"}</AlertTitle>
        <AlertDescription>
          {report.total_profiles} of {report.total_accounts} accounts have a document in
          account_profiles
          {report.passed ? " - every profile matches the source correctly." : ` - ${report.findings.length} finding(s) below.`}
        </AlertDescription>
      </Alert>

      <div>
        <h3 className="mb-2 font-medium">Findings ({report.findings.length})</h3>
        {report.findings.length === 0 ? (
          <p className="text-sm text-muted-foreground">None.</p>
        ) : (
          <Accordion className="w-full">
            {report.findings.map((finding, index) => (
              <AccordionItem key={index} value={`finding-${index}`}>
                <AccordionTrigger>
                  <div className="flex flex-wrap items-center gap-2 text-left">
                    <Badge variant="destructive">{finding.error_code}</Badge>
                    <span className="font-mono text-xs text-muted-foreground">
                      account {finding.account_id}
                    </span>
                  </div>
                </AccordionTrigger>
                <AccordionContent className="space-y-3">
                  <p className="text-sm">{finding.detail}</p>
                  <div className="space-y-1">
                    <p className="text-sm font-medium">Why it broke</p>
                    <p className="text-sm text-muted-foreground">{finding.why}</p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-sm font-medium">How to fix it</p>
                    <p className="text-sm text-muted-foreground">{finding.fix}</p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-sm font-medium">Tradeoffs</p>
                    <p className="text-sm text-muted-foreground">{finding.tradeoffs}</p>
                  </div>
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        )}
      </div>
    </div>
  );
}
