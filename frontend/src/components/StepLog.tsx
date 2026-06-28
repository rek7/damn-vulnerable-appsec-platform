// Terminal-style step log for a scan (CONTRACTS §9 steps).
import { formatTime, stepLevelColor } from '../format';
import { displayOperationalText } from '../presentation';
import type { Step } from '../types';

export function StepLog({ steps }: { steps: Step[] }) {
  if (steps.length === 0) {
    return <p className="text-sm italic text-dim">No steps logged.</p>;
  }
  return (
    <pre
      className="max-h-80 overflow-auto rounded border border-edge bg-bg p-3 text-xs leading-relaxed"
      data-testid="step-log"
    >
      {steps.map((s, i) => (
        <div key={i} className="whitespace-pre-wrap break-words">
          <span className="text-dim">{formatTime(s.ts)}</span>{' '}
          <span className={stepLevelColor(s.level)}>[{s.level}]</span>{' '}
          <span className="text-ink">{displayOperationalText(s.message)}</span>
        </div>
      ))}
    </pre>
  );
}
