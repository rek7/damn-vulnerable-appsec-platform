// Module page: assessment submission, repository intake, and inline evidence.
import { useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { createScan, createUploadScan, listBeacons } from '../api/client';
import { moduleFor } from '../modules';
import { AnalyzerList } from '../components/AnalyzerList';
import { StepLog } from '../components/StepLog';
import { BeaconCard } from '../components/BeaconCard';
import { FindingList } from '../components/FindingList';
import { statusColor } from '../format';
import { findingsForScan } from '../findings';
import { assessmentDisplayId, displayOperationalText } from '../presentation';
import { useStreamContext } from '../stream-context';
import type { Beacon, Scan } from '../types';

export function ModulePage() {
  const { moduleId = '' } = useParams();
  const meta = moduleFor(moduleId);
  const { beacons } = useStreamContext();

  const [scan, setScan] = useState<Scan | null>(null);
  const [scanBeacons, setScanBeacons] = useState<Beacon[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [gitUrl, setGitUrl] = useState('');
  const [file, setFile] = useState<File | null>(null);

  // Evidence activity correlated to the current scan, merging REST hydration with live arrivals.
  const correlatedBeacons = useMemo<Beacon[]>(() => {
    if (!scan) return [];
    const byId = new Map<string, Beacon>();
    for (const b of scanBeacons) byId.set(b.id, b);
    for (const b of beacons) {
      if (b.scan_token === scan.scan_token) byId.set(b.id, b);
    }
    return Array.from(byId.values()).sort(
      (a, b) => new Date(b.received_at).getTime() - new Date(a.received_at).getTime(),
    );
  }, [scan, scanBeacons, beacons]);

  const inlineFindings = useMemo(
    () => (scan ? findingsForScan(scan, correlatedBeacons) : []),
    [scan, correlatedBeacons],
  );

  if (!meta) {
    return (
      <div className="panel p-6">
        <p className="text-danger">Unknown module: {moduleId}</p>
        <Link to="/" className="btn mt-4">
          ← Home
        </Link>
      </div>
    );
  }

  async function run(fn: () => Promise<Scan>) {
    setSubmitting(true);
    setError(null);
    setScanBeacons([]);
    try {
      const result = await fn();
      setScan(result);
      try {
        setScanBeacons(await listBeacons({ scan_token: result.scan_token }));
      } catch {
        // The scan result is still valid; live WS signals can fill in later.
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'submission failed');
    } finally {
      setSubmitting(false);
    }
  }

  const runSample = (vector: string) =>
    run(() => createScan({ module: meta.id, vector, source_type: 'sample' }));

  const runGit = () =>
    run(() => createScan({ module: meta.id, source_type: 'git', git_url: gitUrl.trim() }));

  const runUpload = () => {
    if (!file) return;
    return run(() => createUploadScan({ module: meta.id, source_type: 'upload' }, file));
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3 text-sm text-dim">
        <Link to="/" className="hover:text-ink">
          Home
        </Link>
        <span>/</span>
        <span className="text-ink">{meta.title}</span>
      </div>

      <section className="panel p-6">
        <div className="flex items-center gap-3">
          <span
            className="flex h-12 min-w-12 items-center justify-center rounded-md border border-edge bg-bg px-2 text-xs font-black text-dim"
            aria-hidden
          >
            {meta.icon}
          </span>
          <div>
            <h1 className={`text-2xl font-black tracking-tight ${meta.accent}`}>{meta.title}</h1>
            <p className="text-sm italic text-dim">{meta.analog}</p>
          </div>
        </div>
        <p className="mt-4 max-w-3xl text-sm leading-relaxed text-dim">{meta.blurb}</p>
      </section>

      <div className="grid gap-6 lg:grid-cols-[1.4fr_0.9fr]">
        {/* Submit surface */}
        <div className="space-y-6">
          <section className="panel p-5">
            <h2 className="mb-3 text-sm font-bold uppercase tracking-widest text-dim">
              Assessment templates
            </h2>
            <div className="space-y-3">
              {meta.vectors.map((v) => (
                <div
                  key={v.id}
                  className="flex flex-wrap items-center gap-3 rounded border border-edge bg-panel2 px-3 py-3"
                >
                  <div className="min-w-0 flex-1">
                    <p className="font-semibold text-ink">{v.label}</p>
                    <p className="text-xs text-dim">{v.description}</p>
                    <p className="mt-1 text-[0.7rem] font-semibold uppercase tracking-wide text-dim">
                      Analyzer: {v.analyzer}
                    </p>
                  </div>
                  <button
                    type="button"
                    className="btn btn-neon"
                    disabled={submitting}
                    onClick={() => void runSample(v.id)}
                    data-testid={`run-sample-${v.id}`}
                  >
                    Run assessment
                  </button>
                </div>
              ))}
            </div>
          </section>

          <section className="panel p-5">
            <h2 className="mb-3 text-sm font-bold uppercase tracking-widest text-dim">
              Repository intake
            </h2>
            <div className="space-y-4">
              <div>
                <label
                  htmlFor="git-url"
                  className="mb-1 block text-xs font-semibold uppercase tracking-wide text-dim"
                >
                  Public git URL (https; github/gitlab/bitbucket/codeberg)
                </label>
                <div className="flex gap-2">
                  <input
                    id="git-url"
                    type="url"
                    placeholder="https://github.com/owner/repo"
                    value={gitUrl}
                    onChange={(e) => setGitUrl(e.target.value)}
                    className="flex-1 rounded border border-edge bg-bg px-3 py-2 text-sm text-ink placeholder:text-dim focus:border-cyan focus:outline-none"
                  />
                  <button
                    type="button"
                    className="btn"
                    disabled={submitting || gitUrl.trim().length === 0}
                    onClick={() => void runGit()}
                    data-testid="run-git"
                  >
                    Scan repository
                  </button>
                </div>
              </div>

              <div>
                <label
                  htmlFor="archive"
                  className="mb-1 block text-xs font-semibold uppercase tracking-wide text-dim"
                >
                  Upload archive (.zip / .tar.gz, max 20 MB)
                </label>
                <div className="flex gap-2">
                  <input
                    id="archive"
                    type="file"
                    accept=".zip,.tar.gz,.tgz"
                    onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                    className="flex-1 rounded border border-edge bg-bg px-3 py-2 text-sm text-ink file:mr-3 file:rounded file:border-0 file:bg-panel2 file:px-3 file:py-1 file:text-ink"
                  />
                  <button
                    type="button"
                    className="btn"
                    disabled={submitting || !file}
                    onClick={() => void runUpload()}
                    data-testid="run-upload"
                  >
                    Scan archive
                  </button>
                </div>
              </div>
            </div>
          </section>
        </div>

        <section className="panel p-5">
          <h2 className="text-sm font-bold uppercase tracking-widest text-dim">
            Assessment context
          </h2>
          <div className="mt-4 space-y-3">
            <div className="rounded-md border border-edge bg-panel2 p-3">
              <p className="text-xs font-semibold uppercase tracking-wide text-dim">
                Assessment profile
              </p>
              <p className="mt-1 text-sm font-semibold text-ink">Standard review</p>
              <p className="mt-1 text-xs leading-relaxed text-dim">
                Repository assessment inputs are processed with the selected analyzer workflow so
                findings and evidence are available for review.
              </p>
            </div>
            <div className="rounded-md border border-edge bg-panel2 p-3">
              <p className="text-xs font-semibold uppercase tracking-wide text-dim">
                Evidence captured
              </p>
              <ul className="mt-2 space-y-1 text-xs leading-relaxed text-dim">
                <li>Analyzer summary and status</li>
                <li>Evidence event count and supporting details</li>
                <li>Masked data-handling markers</li>
                <li>Finding severity and affected surface</li>
              </ul>
            </div>
            <div className="rounded-md border border-edge bg-panel2 p-3">
              <p className="text-xs font-semibold uppercase tracking-wide text-dim">Review focus</p>
              <p className="mt-1 text-xs leading-relaxed text-dim">
                Use this page to review repository assessment behavior across common scanner
                integrations.
              </p>
            </div>
          </div>
        </section>
      </div>

      {/* Inline live result */}
      <section className="panel p-5" data-testid="inline-result" aria-live="polite">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold uppercase tracking-widest text-dim">Latest result</h2>
          {submitting && <span className="text-xs text-cyan animate-pulseband">running…</span>}
        </div>

        {error && (
          <p
            className="mt-3 rounded border border-danger/50 bg-danger/10 px-3 py-2 text-sm text-danger"
            role="alert"
          >
            {error}
          </p>
        )}

        {!scan && !error && (
          <p className="mt-3 text-sm italic text-dim">
            Run an assessment above to see findings, analyzers, the step log, and supporting
            evidence activity.
          </p>
        )}

        {scan && (
          <div className="mt-4 space-y-4">
            <div className="flex flex-wrap items-center gap-2">
              <span className={`tag ${statusColor(scan.status)}`}>{scan.status}</span>
              <span className="font-mono text-xs text-dim">
                {assessmentDisplayId(scan.scan_token)}
              </span>
              <Link to={`/scans/${scan.id}`} className="ml-auto text-xs text-cyan hover:underline">
                Full detail -&gt;
              </Link>
            </div>
            <p className="text-sm text-ink">{displayOperationalText(scan.result) || '-'}</p>

            <div>
              <h3 className="mb-2 text-xs font-bold uppercase tracking-widest text-dim">
                Findings generated
              </h3>
              <FindingList findings={inlineFindings} compact />
            </div>

            <div>
              <h3 className="mb-2 text-xs font-bold uppercase tracking-widest text-dim">
                Analyzers
              </h3>
              <AnalyzerList analyzers={scan.analyzers} />
            </div>

            <div>
              <h3 className="mb-2 text-xs font-bold uppercase tracking-widest text-dim">
                Step log
              </h3>
              <StepLog steps={scan.steps} />
            </div>

            <div>
              <h3 className="mb-2 text-xs font-bold uppercase tracking-widest text-dim">
                Evidence events ({correlatedBeacons.length})
              </h3>
              {correlatedBeacons.length === 0 ? (
                <p className="text-sm italic text-dim">
                  No evidence event has been linked to this assessment yet.
                </p>
              ) : (
                <div className="space-y-2">
                  {correlatedBeacons.map((b) => (
                    <BeaconCard key={b.id} beacon={b} />
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
