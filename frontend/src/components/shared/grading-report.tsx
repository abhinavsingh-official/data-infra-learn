import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { Finding, GradingReport as GradingReportType } from "@/lib/types";

function FindingAccordion({ findings, idPrefix }: { findings: Finding[]; idPrefix: string }) {
  if (findings.length === 0) {
    return <p className="text-sm text-muted-foreground">None.</p>;
  }
  return (
    <Accordion className="w-full">
      {findings.map((finding, index) => (
        <AccordionItem key={`${idPrefix}-${index}`} value={`${idPrefix}-${index}`}>
          <AccordionTrigger>
            <div className="flex flex-wrap items-center gap-2 text-left">
              <Badge variant="destructive">{finding.error_code}</Badge>
              <span className="font-mono text-xs text-muted-foreground">{finding.event_id}</span>
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
  );
}

export function GradingReportView({ report }: { report: GradingReportType }) {
  return (
    <div className="space-y-6">
      <Alert variant={report.passed ? "default" : "destructive"}>
        <AlertTitle>{report.passed ? "Passed" : "Not passing yet"}</AlertTitle>
        <AlertDescription>
          {report.total_clean_rows} rows in <code>clean_transactions</code>
          {report.passed
            ? " - every edge case was handled correctly."
            : ` - ${report.structural_findings.length + report.fault_findings.length} finding(s) below.`}
        </AlertDescription>
      </Alert>

      <div>
        <h3 className="mb-2 font-medium">Fault type coverage</h3>
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Fault type</TableHead>
                <TableHead className="text-right">Total injected</TableHead>
                <TableHead className="text-right">Issues found</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {Object.entries(report.fault_type_summary).map(([faultType, summary]) => (
                <TableRow key={faultType}>
                  <TableCell className="font-mono text-xs">{faultType}</TableCell>
                  <TableCell className="text-right">{summary.total}</TableCell>
                  <TableCell className="text-right">
                    {summary.issues === 0 ? (
                      <span className="text-muted-foreground">0</span>
                    ) : (
                      <Badge variant="destructive">{summary.issues}</Badge>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </div>

      <div>
        <h3 className="mb-2 font-medium">
          Structural findings ({report.structural_findings.length})
        </h3>
        <FindingAccordion findings={report.structural_findings} idPrefix="structural" />
      </div>

      <div>
        <h3 className="mb-2 font-medium">Fault findings ({report.fault_findings.length})</h3>
        <FindingAccordion findings={report.fault_findings} idPrefix="fault" />
      </div>
    </div>
  );
}
