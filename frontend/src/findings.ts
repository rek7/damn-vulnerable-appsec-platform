import { moduleFor } from './modules';
import { displayOperationalText, sourceDisplayName } from './presentation';
import type { AnalyzerResult, Beacon, Scan } from './types';

export type FindingSeverity = 'critical' | 'high' | 'medium' | 'info';
export type FindingStatus = 'open' | 'error' | 'observed';

export interface Finding {
  id: string;
  title: string;
  severity: FindingSeverity;
  status: FindingStatus;
  scanId: string;
  scanToken: string;
  module: string;
  vector: string;
  affectedSurface: string;
  evidence: string[];
  recommendation: string;
  control: string;
  eventCount: number;
}

interface FindingTemplate {
  title: string;
  severity: FindingSeverity;
  affectedSurface: string;
  evidence: string;
  recommendation: string;
  control: string;
}

const TEMPLATES: Record<string, FindingTemplate> = {
  checkov_external_checks: {
    title: 'IaC policy-pack review generated a finding',
    severity: 'critical',
    affectedSurface: 'IaC policy governance',
    evidence: 'Repository IaC policy-pack settings were present during assessment.',
    recommendation: 'Require centrally managed, signed policy packs for IaC review jobs.',
    control: 'Managed policy packs',
  },
  terragrunt_before_hook: {
    title: 'Infrastructure wrapper review generated a finding',
    severity: 'critical',
    affectedSurface: 'IaC wrapper execution hooks',
    evidence: 'Repository infrastructure wrapper configuration was executed during assessment.',
    recommendation:
      'Review repository-defined IaC wrapper hooks in isolated workers before allowing plan jobs.',
    control: 'Constrained IaC wrapper execution',
  },
  setup_py_exec: {
    title: 'Python dependency metadata review generated a finding',
    severity: 'high',
    affectedSurface: 'Python package metadata resolution',
    evidence:
      'Python package metadata required dynamic analyzer handling during dependency review.',
    recommendation:
      'Collect package metadata with constrained worker permissions and approved metadata sources.',
    control: 'Constrained dependency review',
  },
  gemspec_eval: {
    title: 'Ruby dependency metadata review generated a finding',
    severity: 'high',
    affectedSurface: 'Ruby package metadata resolution',
    evidence: 'Ruby package metadata required dynamic analyzer handling during dependency review.',
    recommendation:
      'Collect gem metadata with constrained worker permissions and approved metadata sources.',
    control: 'Constrained dependency review',
  },
  npm_lifecycle: {
    title: 'Node dependency workflow review generated a finding',
    severity: 'high',
    affectedSurface: 'Node package workflow settings',
    evidence: 'Node package inventory collection used repository-defined workflow settings.',
    recommendation:
      'Prefer lockfile and manifest analysis for inventory jobs unless workflow execution is approved.',
    control: 'Approved dependency workflow',
  },
  eslintrc_js_exec: {
    title: 'JavaScript analyzer policy review generated a finding',
    severity: 'high',
    affectedSurface: 'Security-tool configuration governance',
    evidence: 'JavaScript analyzer configuration was supplied by the assessed repository.',
    recommendation:
      'Prefer centrally governed analyzer settings or isolate project-specific configuration review.',
    control: 'Managed analyzer policy',
  },
  rubocop_require: {
    title: 'Ruby analyzer policy review generated a finding',
    severity: 'high',
    affectedSurface: 'Security-tool configuration governance',
    evidence: 'Ruby analyzer configuration was supplied by the assessed repository.',
    recommendation: 'Prefer centrally governed analyzer settings or approved project rule bundles.',
    control: 'Managed analyzer policy',
  },
  symlink_traversal: {
    title: 'Repository boundary review generated a finding',
    severity: 'critical',
    affectedSurface: 'Secret scanning workspace boundaries',
    evidence: 'The repository assessment reached a file outside the expected project boundary.',
    recommendation:
      'Resolve real paths before file review and reject paths outside the scan workspace.',
    control: 'Workspace boundary enforcement',
  },
};

const SEVERITY_RANK: Record<FindingSeverity, number> = {
  critical: 4,
  high: 3,
  medium: 2,
  info: 1,
};

function statusForAnalyzer(analyzer: AnalyzerResult): FindingStatus {
  if (analyzer.status === 'error') return 'error';
  if (analyzer.triggered) return 'open';
  return 'observed';
}

function templateFor(vector: string): FindingTemplate {
  return (
    TEMPLATES[vector] ?? {
      title: 'Scanner behavior requires review',
      severity: 'medium',
      affectedSurface: 'Repository analysis workflow',
      evidence: 'Analyzer output indicates a behavior that should be reviewed.',
      recommendation: 'Review analyzer settings and isolate repository-supplied inputs.',
      control: 'Review scanner isolation',
    }
  );
}

function moduleLabel(scan: Scan): string {
  return moduleFor(scan.module)?.title ?? scan.module;
}

export function findingsForScan(scan: Scan, beacons: Beacon[] = []): Finding[] {
  const analyzers =
    scan.analyzers.length > 0
      ? scan.analyzers
      : scan.vector
        ? [
            {
              name: scan.module,
              vector: scan.vector,
              triggered: scan.beacon_count > 0,
              status: 'ok',
              summary: scan.result,
              duration_ms: 0,
            } satisfies AnalyzerResult,
          ]
        : [];

  return analyzers.map((analyzer, index) => {
    const template = templateFor(analyzer.vector);
    const vectorEvents = beacons.filter((b) => b.vector === analyzer.vector).length;
    const eventCount = Math.max(vectorEvents, analyzer.triggered ? scan.beacon_count : 0);
    const evidence = [template.evidence];
    if (analyzer.summary) evidence.push(displayOperationalText(analyzer.summary));
    if (eventCount > 0) evidence.push(`${eventCount} evidence event(s) linked to this assessment.`);
    if (scan.source.ref) evidence.push(`Source: ${sourceDisplayName(scan)}`);

    return {
      id: `${scan.id}-${analyzer.vector}-${index}`,
      title: template.title,
      severity: template.severity,
      status: statusForAnalyzer(analyzer),
      scanId: scan.id,
      scanToken: scan.scan_token,
      module: moduleLabel(scan),
      vector: analyzer.vector,
      affectedSurface: template.affectedSurface,
      evidence,
      recommendation: template.recommendation,
      control: template.control,
      eventCount,
    };
  });
}

export function highestSeverity(findings: Finding[]): FindingSeverity | null {
  if (findings.length === 0) return null;
  return findings.reduce<FindingSeverity>(
    (highest, finding) =>
      SEVERITY_RANK[finding.severity] > SEVERITY_RANK[highest] ? finding.severity : highest,
    findings[0].severity,
  );
}

export function findingStatusSummary(findings: Finding[]): {
  open: number;
  error: number;
  observed: number;
} {
  return findings.reduce(
    (acc, finding) => {
      acc[finding.status] += 1;
      return acc;
    },
    { open: 0, error: 0, observed: 0 },
  );
}

export function severityClass(severity: FindingSeverity): string {
  switch (severity) {
    case 'critical':
      return 'border-danger/60 bg-danger/10 text-danger';
    case 'high':
      return 'border-amber/60 bg-amber/10 text-amber';
    case 'medium':
      return 'border-cyan/60 bg-cyan/10 text-cyan';
    case 'info':
      return 'border-edge bg-panel2 text-dim';
  }
}

export function statusClass(status: FindingStatus): string {
  switch (status) {
    case 'open':
      return 'border-danger/60 bg-danger/10 text-danger';
    case 'error':
      return 'border-amber/60 bg-amber/10 text-amber';
    case 'observed':
      return 'border-cyan/60 bg-cyan/10 text-cyan';
  }
}
