// Scans table: status, source, evidence count, link to detail.
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { listScans } from '../api/client';
import { statusColor } from '../format';
import { formatDateTime } from '../format';
import { findingStatusSummary, findingsForScan, highestSeverity, severityClass } from '../findings';
import { assessmentDisplayId, sourceDisplayName } from '../presentation';
import { useStreamContext } from '../stream-context';
import type { Scan } from '../types';

export function Scans() {
  const [scans, setScans] = useState<Scan[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const { scanUpdates, beacons } = useStreamContext();

  const load = useCallback(async () => {
    try {
      const list = await listScans();
      setScans(list);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'failed to load scans');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
    const t = setInterval(() => void load(), 5000);
    return () => clearInterval(t);
  }, [load]);

  // Reload when new scan transitions or signals arrive over the WS.
  useEffect(() => {
    if (Object.keys(scanUpdates).length > 0) void load();
  }, [scanUpdates, load]);

  // Live signal counts overlay (server count may lag the WS).
  const liveCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const b of beacons) {
      counts[b.scan_token] = (counts[b.scan_token] ?? 0) + 1;
    }
    return counts;
  }, [beacons]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-black tracking-tight text-ink">Assessments</h1>
        <button type="button" className="btn" onClick={() => void load()}>
          ↻ Refresh
        </button>
      </div>

      {error && (
        <p
          className="rounded border border-danger/50 bg-danger/10 px-3 py-2 text-sm text-danger"
          role="alert"
        >
          {error}
        </p>
      )}

      <div className="panel overflow-x-auto">
        <table className="w-full min-w-[720px] text-left text-sm">
          <thead className="border-b border-edge text-xs uppercase tracking-wider text-dim">
            <tr>
              <th className="px-4 py-3">Created</th>
              <th className="px-4 py-3">Module</th>
              <th className="px-4 py-3">Source</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Findings</th>
              <th className="px-4 py-3 text-right">Evidence events</th>
              <th className="px-4 py-3 text-right">Assessment ID</th>
            </tr>
          </thead>
          <tbody>
            {scans.map((s) => {
              const beaconCount = Math.max(s.beacon_count, liveCounts[s.scan_token] ?? 0);
              const scanFindings = findingsForScan(
                s,
                beacons.filter((b) => b.scan_token === s.scan_token),
              );
              const severity = highestSeverity(scanFindings);
              const summary = findingStatusSummary(scanFindings);
              return (
                <tr
                  key={s.id}
                  className="border-b border-edge/50 transition-colors hover:bg-panel2"
                  data-testid="scan-row"
                >
                  <td className="px-4 py-3 text-dim">{formatDateTime(s.created_at)}</td>
                  <td className="px-4 py-3">
                    <span className="tag border-edge text-ink">{s.module}</span>
                  </td>
                  <td className="px-4 py-3 text-dim">{sourceDisplayName(s)}</td>
                  <td className="px-4 py-3">
                    <span className={`tag ${statusColor(s.status)}`}>{s.status}</span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap items-center gap-1.5">
                      {severity ? (
                        <span className={`tag ${severityClass(severity)}`}>{severity}</span>
                      ) : (
                        <span className="tag border-edge text-dim">none</span>
                      )}
                      {summary.open > 0 && (
                        <span className="tag border-danger/60 text-danger">
                          {summary.open} open
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right font-mono">
                    <span className={beaconCount > 0 ? 'text-neon' : 'text-dim'}>
                      {beaconCount}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <Link to={`/scans/${s.id}`} className="font-mono text-cyan hover:underline">
                      {assessmentDisplayId(s.scan_token)}
                    </Link>
                  </td>
                </tr>
              );
            })}
            {!loading && scans.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-10 text-center text-sm italic text-dim">
                  No assessments yet. Pick a program and run an assessment template.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
