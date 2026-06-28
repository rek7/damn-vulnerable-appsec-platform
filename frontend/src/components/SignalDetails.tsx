// Renders normalized signal details. Values that look sensitive are redacted for
// the UI.
interface Props {
  decoded: string;
}

function shouldMask(value: string): boolean {
  return /fake|token|secret|key|postgres|stripe|akia|ghp_/i.test(value);
}

export function SignalDetails({ decoded }: Props) {
  const trimmed = decoded.trim();
  if (!trimmed) {
    return (
      <p className="text-xs italic text-dim" data-testid="signal-empty">
        No signal details were recorded.
      </p>
    );
  }

  const lines = trimmed.split('\n').filter((l) => l.length > 0);

  return (
    <pre
      className="overflow-x-auto rounded border border-edge bg-bg p-3 text-xs leading-relaxed"
      data-testid="signal-details"
    >
      {lines.map((line, i) => {
        const eq = line.indexOf('=');
        if (eq === -1) {
          return (
            <div key={i} className="text-ink">
              {line}
            </div>
          );
        }
        const key = line.slice(0, eq);
        const value = line.slice(eq + 1);
        const masked = shouldMask(value);
        return (
          <div key={i} className="whitespace-pre-wrap break-all">
            <span className="text-cyan">{key}</span>
            <span className="text-dim">=</span>
            <span className="text-amber">{masked ? '********' : value}</span>
            {masked && <span className="fake-label">MASKED</span>}
          </div>
        );
      })}
    </pre>
  );
}
