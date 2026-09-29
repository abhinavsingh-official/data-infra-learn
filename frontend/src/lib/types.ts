export interface DatasetStatDto {
  label: string;
  value: string;
  hint?: string;
}

export interface ReferenceSolutionStepDto {
  title: string;
  sql: string;
  note?: string;
}

export interface ReferenceSolutionDto {
  sql: string;
  note?: string;
  /** Optional staged breakdown of the same final query, one edge case at a
   * time - not every phase has this yet, so callers fall back to the plain
   * sql/note pair when it's absent. */
  steps?: ReferenceSolutionStepDto[];
}

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
  dataset_stats: DatasetStatDto[];
  starter_sql: string;
  reference_solution: ReferenceSolutionDto;
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
  dataset_stats: DatasetStatDto[];
  starter_command: string;
  reference_solution: ReferenceSolutionDto;
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
  dataset_stats: DatasetStatDto[];
  starter_sql: string;
  reference_solution: ReferenceSolutionDto;
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

export interface RemediationEntry {
  error_code: string;
  why: string;
  fix: string;
  tradeoffs: string;
}

export interface LearnPhase {
  phase: string;
  one_liner: string;
  entries: RemediationEntry[];
}

export interface LearnPage {
  overview: string;
  phases: LearnPhase[];
  comparison: ComparisonView;
}

export interface ComparisonEntry {
  paradigm: string;
  source: string;
  code: string;
  explanation: string;
}

export interface ComparisonView {
  operation: string;
  why_this_operation: string;
  entries: ComparisonEntry[];
  real_duplicate_count: number;
}

export interface LakehouseTask {
  title: string;
  summary: string;
  source: Record<string, string>;
  workflow: string[];
  required_output: {
    table: string;
    columns: Record<string, string>;
  };
  hints: string[];
  dataset_stats: DatasetStatDto[];
  starter_sql: string;
  reference_solution: ReferenceSolutionDto;
}

export interface CommitBatchResult {
  success: boolean;
  version: number | null;
  row_count: number | null;
  error_code: string | null;
  error_message: string | null;
}

export interface LakeTask {
  title: string;
  summary: string;
  source: string;
  your_output_directory: string;
  workflow: string[];
  required_output: {
    table: string;
    columns: Record<string, string>;
  };
  hints: string[];
  dataset_stats: DatasetStatDto[];
  starter_sql: string;
  reference_solution: ReferenceSolutionDto;
}
