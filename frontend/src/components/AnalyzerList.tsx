// Renders product-facing review-path status from backend analyzer entries.
import { analyzerStatusColor } from '../format';
import { vectorColor, vectorLabel } from '../modules';
import { displayOperationalText } from '../presentation';
import type { AnalyzerResult } from '../types';

export function AnalyzerList({ analyzers }: { analyzers: AnalyzerResult[] }) {
  if (analyzers.length === 0) {
    return <p className="text-sm italic text-dim">No review paths ran.</p>;
  }
  return (
    <ul className="space-y-2" data-testid="analyzer-list">
      {analyzers.map((a, i) => (
        <li
          key={`${a.name}-${a.vector}-${i}`}
          className="flex flex-wrap items-center gap-2 rounded border border-edge bg-panel2 px-3 py-2"
        >
          <span className="font-semibold text-ink">{`Review path ${i + 1}`}</span>
          <span className={`tag ${vectorColor(a.vector)}`}>{vectorLabel(a.vector)}</span>
          <span className={`tag ${analyzerStatusColor(a.status)}`}>{a.status}</span>
          <span
            className={`tag ${a.triggered ? 'border-neon/60 text-neon' : 'border-edge text-dim'}`}
          >
            {a.triggered ? 'evidence' : 'clear'}
          </span>
          <span className="ml-auto text-xs text-dim">{a.duration_ms} ms</span>
          {a.summary && (
            <p className="w-full text-xs text-dim">{displayOperationalText(a.summary)}</p>
          )}
        </li>
      ))}
    </ul>
  );
}
