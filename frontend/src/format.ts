// Small display helpers shared across pages.
import type { AnalyzerStatus, ScanStatus } from './types';

/** Render an ISO timestamp as HH:MM:SS (local). Falls back to the raw string. */
export function formatTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleTimeString(undefined, { hour12: false });
}

/** Render an ISO timestamp as a full local date-time. */
export function formatDateTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, { hour12: false });
}

export function statusColor(status: ScanStatus): string {
  switch (status) {
    case 'completed':
      return 'text-neon border-neon/60';
    case 'running':
      return 'text-cyan border-cyan/60 animate-pulseband';
    case 'queued':
      return 'text-dim border-edge';
    case 'failed':
      return 'text-danger border-danger/60';
    default:
      return 'text-dim border-edge';
  }
}

export function analyzerStatusColor(status: AnalyzerStatus): string {
  switch (status) {
    case 'ok':
      return 'text-neon border-neon/60';
    case 'error':
      return 'text-danger border-danger/60';
    default:
      return 'text-dim border-edge';
  }
}

export function stepLevelColor(level: string): string {
  switch (level) {
    case 'warn':
      return 'text-amber';
    case 'error':
      return 'text-danger';
    default:
      return 'text-dim';
  }
}
