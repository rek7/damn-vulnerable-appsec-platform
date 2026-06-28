// Dashboard: security-tool posture overview and recent evidence.
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { listScans } from '../api/client';
import { MODULES } from '../modules';
import { useStreamContext } from '../stream-context';
import { FindingList } from '../components/FindingList';
import { findingsForScan, findingStatusSummary } from '../findings';
import type { Scan } from '../types';

export function Home() {
  const { beacons, scanUpdates } = useStreamContext();
  const [scans, setScans] = useState<Scan[]>([]);
  const totalAssessments = MODULES.reduce((sum, m) => sum + m.vectors.length, 0);
  const signalEvents = scans.reduce((sum, scan) => sum + scan.beacon_count, 0);

  const loadScans = useCallback(async () => {
    try {
      setScans(await listScans());
    } catch {
      // The overview remains useful with static program/control data.
    }
  }, []);

  useEffect(() => {
    void loadScans();
    const timer = setInterval(() => void loadScans(), 5000);
    return () => clearInterval(timer);
  }, [loadScans]);

  useEffect(() => {
    if (Object.keys(scanUpdates).length > 0) void loadScans();
  }, [scanUpdates, loadScans]);

  const findings = useMemo(
    () =>
      scans.flatMap((scan) =>
        findingsForScan(
          scan,
          beacons.filter((beacon) => beacon.scan_token === scan.scan_token),
        ),
      ),
    [scans, beacons],
  );
  const findingSummary = findingStatusSummary(findings);
  const highlightedFindings = findings
    .filter((finding) => finding.status === 'open' || finding.status === 'error')
    .slice(0, 4);
  const recentFindings =
    highlightedFindings.length > 0 ? highlightedFindings : findings.slice(0, 4);
  const completed = scans.filter((scan) => scan.status === 'completed').length;

  return (
    <div className="space-y-6">
      <section className="grid gap-4 xl:grid-cols-[1.5fr_1fr]">
        <div className="panel p-6">
          <div className="max-w-4xl">
            <p className="text-xs font-semibold uppercase tracking-wide text-cyan">
              Application security operations
            </p>
            <h1 className="mt-2 text-3xl font-black tracking-tight text-ink">
              AppSec Posture Dashboard
            </h1>
            <p className="mt-3 text-sm leading-relaxed text-dim">
              Run repository assessments across the security programs used by application teams:
              code analysis, dependency review, infrastructure policy, container review, and secrets
              governance. Findings are reported from analyzer output, policy status, and assessment
              evidence.
            </p>
          </div>
          <div className="mt-5 flex flex-wrap gap-2">
            <Link to="/findings" className="btn btn-primary">
              Review findings
            </Link>
            <Link to="/docs" className="btn">
              Reference docs
            </Link>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="panel p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-dim">Open findings</p>
            <p className="mt-2 text-3xl font-black text-danger">{findingSummary.open}</p>
          </div>
          <div className="panel p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-dim">Completed</p>
            <p className="mt-2 text-3xl font-black text-neon">{completed}</p>
          </div>
          <div className="panel p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-dim">
              Evidence events
            </p>
            <p className="mt-2 text-3xl font-black text-cyan">
              {Math.max(signalEvents, beacons.length)}
            </p>
          </div>
          <div className="panel p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-dim">Assessments</p>
            <p className="mt-2 text-3xl font-black text-ink">{scans.length}</p>
          </div>
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-[1.15fr_0.85fr]">
        <div className="panel p-5">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-bold uppercase tracking-widest text-dim">
              Recent findings
            </h2>
            <Link to="/findings" className="text-xs font-semibold text-cyan hover:underline">
              View all
            </Link>
          </div>
          {recentFindings.length > 0 ? (
            <FindingList findings={recentFindings} compact />
          ) : (
            <p className="rounded border border-edge bg-panel2 px-3 py-6 text-center text-sm text-dim">
              No findings yet. Run an assessment to populate findings and evidence.
            </p>
          )}
        </div>

        <div className="panel p-5">
          <h2 className="text-sm font-bold uppercase tracking-widest text-dim">Workspace scope</h2>
          <dl className="mt-4 grid gap-3">
            <div className="flex items-center justify-between rounded border border-edge bg-panel2 px-3 py-2">
              <dt className="text-sm text-dim">Scan surfaces</dt>
              <dd className="font-mono text-ink">{MODULES.length}</dd>
            </div>
            <div className="flex items-center justify-between rounded border border-edge bg-panel2 px-3 py-2">
              <dt className="text-sm text-dim">Assessment templates</dt>
              <dd className="font-mono text-ink">{totalAssessments}</dd>
            </div>
            <div className="flex items-center justify-between rounded border border-edge bg-panel2 px-3 py-2">
              <dt className="text-sm text-dim">Assessment profile</dt>
              <dd className="font-mono text-cyan">standard</dd>
            </div>
          </dl>
        </div>
      </section>

      <section>
        <h2 className="mb-3 text-sm font-bold uppercase tracking-widest text-dim">
          Security assessment programs
        </h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {MODULES.map((m) => (
            <Link
              key={m.id}
              to={`/module/${m.id}`}
              className="panel group flex flex-col p-5 transition-colors hover:border-neon hover:shadow-glow"
            >
              <div className="flex items-center gap-3">
                <span
                  aria-hidden
                  className="flex h-10 min-w-10 items-center justify-center rounded-md border border-edge bg-bg px-2 text-xs font-black text-dim"
                >
                  {m.icon}
                </span>
                <span className={`text-base font-black uppercase tracking-wide ${m.accent}`}>
                  {m.id}
                </span>
              </div>
              <h3 className="mt-2 font-semibold text-ink">{m.title}</h3>
              <p className="mt-1 text-xs italic text-dim">{m.analog}</p>
              <p className="mt-3 flex-1 text-xs leading-relaxed text-dim">{m.blurb}</p>
              <div className="mt-3 flex flex-wrap gap-1">
                {m.vectors.map((v) => (
                  <span key={v.id} className="tag border-edge text-dim">
                    {v.label}
                  </span>
                ))}
              </div>
              <span className="mt-4 text-xs font-semibold uppercase tracking-wide text-cyan opacity-0 transition-opacity group-hover:opacity-100">
                Open program -&gt;
              </span>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
