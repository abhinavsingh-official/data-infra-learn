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

export interface NosqlTask {
  title: string;
  summary: string;
  source: string;
  design_questions_to_answer: string[];
  required_output: {
    collection: string;
    note: string;
    document_shape: Record<string, string>;
  };
  hint: string;
}

export interface QuerySourceResult {
  success: boolean;
  columns: string[];
  rows: unknown[][];
  truncated: boolean;
  error_code: string | null;
  error_message: string | null;
}

export interface MongoExecuteResult {
  success: boolean;
  result: Record<string, unknown>;
  truncated: boolean;
  error_code: string | null;
  error_message: string | null;
}

export interface NosqlFinding {
  error_code: string;
  account_id: string;
  detail: string;
  why: string;
  fix: string;
  tradeoffs: string;
}

export interface NosqlGradingReport {
  passed: boolean;
  total_profiles: number;
  total_accounts: number;
  findings: NosqlFinding[];
}

export interface WarehouseRequiredTable {
  note: string;
  columns: Record<string, string>;
}

export interface WarehouseTask {
  title: string;
  summary: string;
  source: Record<string, string>;
  required_output: Record<string, WarehouseRequiredTable>;
  workflow: string[];
  hint: string;
}

export interface WarehouseExecuteResult {
  success: boolean;
  columns: string[];
  rows: unknown[][];
  truncated: boolean;
  error_code: string | null;
  error_message: string | null;
}

export interface WarehouseFinding {
  error_code: string;
  entity_id: string;
  detail: string;
  why: string;
  fix: string;
  tradeoffs: string;
}

export interface WarehouseGradingReport {
  passed: boolean;
  total_accounts: number;
  total_users: number;
  total_transactions: number;
  findings: WarehouseFinding[];
}
