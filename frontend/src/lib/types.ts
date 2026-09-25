export interface PostgresTask {
  title: string;
  summary: string;
  source_table: string;
  source_columns: Record<string, string>;
  edge_cases_to_handle: string[];
  hint: string;
  required_output: {
    table: string;
    note: string;
    columns: Record<string, string>;
  };
}

export interface ExecuteResult {
  success: boolean;
  columns: string[];
  rows: unknown[][];
  truncated: boolean;
  error_code: string | null;
  error_message: string | null;
}

export interface Finding {
  error_code: string;
  event_id: string;
  detail: string;
  why: string;
  fix: string;
  tradeoffs: string;
}

export interface FaultTypeSummary {
  total: number;
  issues: number;
}

export interface GradingReport {
  passed: boolean;
  total_clean_rows: number;
  structural_findings: Finding[];
  fault_findings: Finding[];
  fault_type_summary: Record<string, FaultTypeSummary>;
}
