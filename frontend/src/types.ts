// Wire types mirroring DVAP CONTRACTS.md §4, §6b, §11.
// These MUST stay in sync with api/app/models.py.

export type ModuleName = 'iac' | 'sca' | 'sast' | 'secrets';

export type Vector =
  | 'checkov_external_checks'
  | 'setup_py_exec'
  | 'gemspec_eval'
  | 'npm_lifecycle'
  | 'eslintrc_js_exec'
  | 'rubocop_require'
  | 'symlink_traversal';

export type ScanStatus = 'queued' | 'running' | 'completed' | 'failed';
export type SourceType = 'sample' | 'upload' | 'git';
export type StepLevel = 'info' | 'warn' | 'error';
export type AnalyzerStatus = 'ok' | 'blocked' | 'error';

// §4 — the four mitigation toggles.
export interface Config {
  strip_credentials: boolean;
  block_egress: boolean;
  resolve_symlinks: boolean;
  disable_extensibility: boolean;
}

export type MitigationKey = keyof Config;

export interface ScanSource {
  type: SourceType;
  ref: string; // git_url | filename | "sample"
}

export interface AnalyzerResult {
  name: string;
  vector: string;
  triggered: boolean;
  status: AnalyzerStatus;
  summary: string;
  duration_ms: number;
}

export interface Step {
  ts: string; // ISO8601
  level: StepLevel;
  message: string;
}

export interface Scan {
  id: string;
  scan_token: string; // ^[0-9a-f]{12}$
  module: ModuleName;
  vector: string | null;
  source: ScanSource;
  status: ScanStatus;
  mitigations: Config; // snapshot at scan time
  result: string;
  analyzers: AnalyzerResult[];
  steps: Step[];
  beacon_count: number;
  created_at: string;
  updated_at: string;
}

export interface Beacon {
  id: string;
  scan_id: string | null;
  scan_token: string;
  vector: string;
  raw: string;
  decoded: string;
  received_at: string;
  // The listener also forwards these; optional on the wire.
  method?: string;
  path?: string;
  remote?: string;
}

// POST /api/scans JSON body (sample/git).
export interface CreateScanJSON {
  module: ModuleName;
  vector?: string;
  source_type: 'sample' | 'git';
  git_url?: string;
}

// The `meta` field for multipart upload submission.
export interface CreateScanMeta {
  module: ModuleName;
  vector?: string;
  source_type: 'upload';
}

// Activity envelopes pushed by /api/stream.
export interface ScanUpdateEnvelope {
  type: 'scan_update';
  scan: Scan;
}
export interface BeaconEnvelope {
  type: 'beacon';
  beacon: Beacon;
}
export type StreamEnvelope = ScanUpdateEnvelope | BeaconEnvelope;
