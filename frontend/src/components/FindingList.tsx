import { Link } from 'react-router-dom';
import { severityClass, statusClass } from '../findings';
import { vectorLabel } from '../modules';
import { assessmentDisplayId } from '../presentation';
import type { Finding } from '../findings';

interface Props {
  findings: Finding[];
  compact?: boolean;
}

export function FindingList({ findings, compact = false }: Props) {
  if (findings.length === 0) {
    return (
      <p className="rounded border border-edge bg-panel2 px-3 py-2 text-sm text-dim">
        No application security findings have been reported yet.
      </p>
    );
  }

  return (
    <div className="space-y-3" data-testid="finding-list">
      {findings.map((finding) => (
        <article key={finding.id} className="rounded-md border border-edge bg-panel2 p-4">
          <header className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_auto]">
            <div className="min-w-0 flex-1">
              <h3 className="break-words font-semibold text-ink">{finding.title}</h3>
              <p className="mt-1 break-words text-xs text-dim">
                {finding.module} / {finding.affectedSurface}
              </p>
            </div>
            <div className="flex min-w-0 max-w-full flex-wrap items-start gap-2 sm:justify-end">
              <Link
                to={`/scans/${finding.scanId}`}
                className="max-w-full overflow-hidden text-ellipsis whitespace-nowrap font-mono text-xs text-cyan underline-offset-2 hover:underline"
              >
                {assessmentDisplayId(finding.scanToken)}
              </Link>
              <span className={`tag ${severityClass(finding.severity)}`}>
                {finding.severity}
              </span>
              <span className={`tag ${statusClass(finding.status)}`}>{finding.status}</span>
            </div>
          </header>

          <dl className="mt-3 grid gap-3 text-xs sm:grid-cols-3">
            <div>
              <dt className="font-semibold uppercase tracking-wide text-dim">Assessment</dt>
              <dd className="mt-1 text-ink">{vectorLabel(finding.vector)}</dd>
            </div>
            <div>
              <dt className="font-semibold uppercase tracking-wide text-dim">
                Recommended guardrail
              </dt>
              <dd className="mt-1 text-ink">{finding.control}</dd>
            </div>
            <div>
              <dt className="font-semibold uppercase tracking-wide text-dim">Evidence events</dt>
              <dd className="mt-1 font-mono text-ink">{finding.eventCount}</dd>
            </div>
          </dl>

          {!compact && (
            <div className="mt-3 grid gap-3 lg:grid-cols-2">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-dim">Evidence</p>
                <ul className="mt-1 list-disc space-y-1 pl-4 text-xs leading-relaxed text-dim">
                  {finding.evidence.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-dim">
                  Recommendation
                </p>
                <p className="mt-1 text-xs leading-relaxed text-dim">{finding.recommendation}</p>
              </div>
            </div>
          )}
        </article>
      ))}
    </div>
  );
}
