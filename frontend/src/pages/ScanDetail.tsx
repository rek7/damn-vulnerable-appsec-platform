// Scan detail: analyzers run, result summary, step log, and correlated evidence.
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { getScan, listBeacons } from '../api/client';
import { AnalyzerList } from '../components/AnalyzerList';
import { StepLog } from '../components/StepLog';
import { BeaconCard } from '../components/BeaconCard';
import { FindingList } from '../components/FindingList';
import { statusColor, formatDateTime } from '../format';
import { findingsForScan } from '../findings';
import { vectorLabel } from '../modules';
import { assessmentDisplayId, displayOperationalText, sourceDisplayName } from '../presentation';
import { useStreamContext } from '../stream-context';
import type { Beacon, Scan } from '../types';

export function ScanDetail() {
  const { scanId = '' } = useParams();
  const [scan, setScan] = useState<Scan | null>(null);
  const [beacons, setBeacons] = useState<Beacon[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const { beacons: liveBeacons, scanUpdates } = useStreamContext();

  const load = useCallback(async () => {
    try {
      const s = await getScan(scanId);
      setScan(s);
      const b = await listBeacons({ scan_token: s.scan_token });
      setBeacons(b);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'failed to load scan');
    } finally {
      setLoading(false);
    }
  }, [scanId]);

  useEffect(() => {
    void load();
  }, [load]);

  // Apply live scan_update for this scan.
  useEffect(() => {
    const updated = scanUpdates[scanId];
    if (updated) setScan(updated);
  }, [scanUpdates, scanId]);

  // Merge fetched + live signals (dedupe by id), most recent first.
  const timeline = useMemo<Beacon[]>(() => {
    if (!scan) return [];
    const byId = new Map<string, Beacon>();
    for (const b of beacons) byId.set(b.id, b);
    for (const b of liveBeacons) {
      if (b.scan_token === scan.scan_token) byId.set(b.id, b);
    }
    return Array.from(byId.values()).sort(
      (a, b) => new Date(b.received_at).getTime() - new Date(a.received_at).getTime(),
    );
  }, [scan, beacons, liveBeacons]);

  const findings = useMemo(() => (scan ? findingsForScan(scan, timeline) : []), [scan, timeline]);

  if (loading) {
    return <p className="text-sm italic text-dim">Loading assessment...</p>;
  }

  if (error || !scan) {
    return (
      <div className="panel p-6">
        <p className="text-danger" role="alert">
          {error ?? 'Assessment not found.'}
        </p>
        <Link to="/scans" className="btn mt-4">
          &lt;- Assessments
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3 text-sm text-dim">
        <Link to="/scans" className="hover:text-ink">
          Assessments
        </Link>
        <span>/</span>
        <span className="font-mono text-ink">{assessmentDisplayId(scan.scan_token)}</span>
      </div>

      <section className="panel p-6">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-xl font-black tracking-tight text-ink">
            {scan.module}
            {scan.vector ? ` · ${vectorLabel(scan.vector)}` : ''}
          </h1>
          <span className={`tag ${statusColor(scan.status)}`}>{scan.status}</span>
          <span className="ml-auto text-xs text-dim">{formatDateTime(scan.created_at)}</span>
        </div>
        <p className="mt-3 text-sm text-ink">{displayOperationalText(scan.result) || '-'}</p>
        <dl className="mt-4 grid gap-3 text-xs sm:grid-cols-3">
          <div>
            <dt className="uppercase tracking-wide text-dim">Source</dt>
            <dd className="text-ink">{sourceDisplayName(scan)}</dd>
          </div>
          <div>
            <dt className="uppercase tracking-wide text-dim">Assessment ID</dt>
            <dd className="font-mono text-ink">{assessmentDisplayId(scan.scan_token)}</dd>
          </div>
          <div>
            <dt className="uppercase tracking-wide text-dim">Evidence events</dt>
            <dd className="font-mono text-neon">{Math.max(scan.beacon_count, timeline.length)}</dd>
          </div>
        </dl>
      </section>

      <section className="panel p-5">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-sm font-bold uppercase tracking-widest text-dim">
            Application security findings
          </h2>
          <span className="font-mono text-xs text-dim">{findings.length} generated</span>
        </div>
        <FindingList findings={findings} />
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="panel p-5">
          <h2 className="mb-3 text-sm font-bold uppercase tracking-widest text-dim">
            Analyzers run
          </h2>
          <AnalyzerList analyzers={scan.analyzers} />
        </section>

        <section className="panel p-5">
          <h2 className="mb-3 text-sm font-bold uppercase tracking-widest text-dim">
            Assessment profile
          </h2>
          <ul className="grid gap-2 text-xs sm:grid-cols-2">
            <li className="rounded border border-edge bg-panel2 px-3 py-2">
              <span className="block uppercase tracking-wide text-dim">Profile</span>
              <span className="mt-1 block font-semibold text-ink">Standard review</span>
            </li>
            <li className="rounded border border-edge bg-panel2 px-3 py-2">
              <span className="block uppercase tracking-wide text-dim">Repository evidence</span>
              <span className="mt-1 block font-semibold text-ink">Evaluated</span>
            </li>
            <li className="rounded border border-edge bg-panel2 px-3 py-2">
              <span className="block uppercase tracking-wide text-dim">Evidence correlation</span>
              <span className="mt-1 block font-semibold text-ink">Linked to assessment ID</span>
            </li>
            <li className="rounded border border-edge bg-panel2 px-3 py-2">
              <span className="block uppercase tracking-wide text-dim">Sensitive values</span>
              <span className="mt-1 block font-semibold text-ink">Masked in operator view</span>
            </li>
          </ul>
        </section>
      </div>

      <section className="panel p-5">
        <h2 className="mb-3 text-sm font-bold uppercase tracking-widest text-dim">Step log</h2>
        <StepLog steps={scan.steps} />
      </section>

      <section className="panel p-5">
        <h2 className="mb-3 text-sm font-bold uppercase tracking-widest text-dim">
          Evidence events ({timeline.length})
        </h2>
        <p className="mb-3 text-xs text-dim">
          Activity details are shown below. Sensitive-looking values are masked for operator review.
        </p>
        {timeline.length === 0 ? (
          <p className="text-sm italic text-dim" data-testid="no-signals">
            No evidence events were recorded for this assessment.
          </p>
        ) : (
          <ol className="space-y-3" data-testid="signal-timeline">
            {timeline.map((b) => (
              <li key={b.id}>
                <BeaconCard beacon={b} />
              </li>
            ))}
          </ol>
        )}
      </section>

      <section className="panel p-5">
        <h2 className="mb-3 text-sm font-bold uppercase tracking-widest text-dim">
          Investigation handoff
        </h2>
        <p className="text-sm leading-relaxed text-dim">
          Use the finding evidence, analyzer summary, and activity details above to explain which
          repository input or tool configuration produced the finding. Re-run from the program page
          when you want a fresh assessment record for the same review.
        </p>
      </section>
    </div>
  );
}
