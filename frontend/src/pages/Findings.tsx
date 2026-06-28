// Findings view: normalized records derived from scans and telemetry.
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { listBeacons, listScans } from '../api/client';
import { FindingList } from '../components/FindingList';
import { findingStatusSummary, findingsForScan, highestSeverity, severityClass } from '../findings';
import { useStreamContext } from '../stream-context';
import type { Beacon, Scan } from '../types';

export function Findings() {
  const { beacons: liveBeacons, scanUpdates } = useStreamContext();
  const [scans, setScans] = useState<Scan[]>([]);
  const [beacons, setBeacons] = useState<Beacon[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const [scanList, beaconList] = await Promise.all([listScans(), listBeacons()]);
      setScans(scanList);
      setBeacons(beaconList);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'failed to load findings');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
    const timer = setInterval(() => void load(), 5000);
    return () => clearInterval(timer);
  }, [load]);

  useEffect(() => {
    if (Object.keys(scanUpdates).length > 0 || liveBeacons.length > 0) void load();
  }, [scanUpdates, liveBeacons.length, load]);

  const findings = useMemo(() => {
    const allBeacons = new Map<string, Beacon>();
    for (const beacon of beacons) allBeacons.set(beacon.id, beacon);
    for (const beacon of liveBeacons) allBeacons.set(beacon.id, beacon);
    const merged = Array.from(allBeacons.values());

    return scans.flatMap((scan) =>
      findingsForScan(
        scan,
        merged.filter((beacon) => beacon.scan_token === scan.scan_token),
      ),
    );
  }, [scans, beacons, liveBeacons]);

  const summary = findingStatusSummary(findings);
  const topSeverity = highestSeverity(findings);
  const byModule = findings.reduce<Record<string, number>>((acc, finding) => {
    acc[finding.module] = (acc[finding.module] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <div className="space-y-5">
      <section className="panel p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-cyan">
              Findings queue
            </p>
            <h1 className="mt-2 text-2xl font-black tracking-tight text-ink">
              Application Security Findings
            </h1>
            <p className="mt-2 max-w-3xl text-sm leading-relaxed text-dim">
              Findings are created from analyzer output, policy status, and correlated assessment
              telemetry.
            </p>
          </div>
          <Link to="/" className="btn">
            Run assessments
          </Link>
        </div>
      </section>

      <section className="grid gap-3 md:grid-cols-4">
        <div className="panel p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-dim">Open</p>
          <p className="mt-2 text-3xl font-black text-danger">{summary.open}</p>
        </div>
        <div className="panel p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-dim">Observed</p>
          <p className="mt-2 text-3xl font-black text-cyan">{findings.length}</p>
        </div>
        <div className="panel p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-dim">Top severity</p>
          <p className="mt-3">
            {topSeverity ? (
              <span className={`tag ${severityClass(topSeverity)}`}>{topSeverity}</span>
            ) : (
              <span className="tag border-edge text-dim">none</span>
            )}
          </p>
        </div>
        <div className="panel p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-dim">Programs</p>
          <p className="mt-2 text-3xl font-black text-ink">{Object.keys(byModule).length}</p>
        </div>
      </section>

      {error && (
        <p
          className="rounded border border-danger/50 bg-danger/10 px-3 py-2 text-sm text-danger"
          role="alert"
        >
          {error}
        </p>
      )}

      <section className="panel p-5">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-sm font-bold uppercase tracking-widest text-dim">
            Normalized findings
          </h2>
          <span className="font-mono text-xs text-dim">
            {loading ? 'loading' : `${findings.length} records`}
          </span>
        </div>
        <FindingList findings={findings} />
      </section>
    </div>
  );
}
