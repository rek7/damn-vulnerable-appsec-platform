// A single correlated signal. Used in the scan-detail timeline and live feed.
import { Link } from 'react-router-dom';
import { vectorColor, vectorLabel } from '../modules';
import { formatTime } from '../format';
import type { Beacon } from '../types';
import { SignalDetails } from './SignalDetails';
import { assessmentDisplayId } from '../presentation';

interface Props {
  beacon: Beacon;
  /** Stage sizing for the live feed. */
  large?: boolean;
  /** Link the assessment identifier to its detail page. */
  linkScan?: boolean;
  /** Highlight newly-arrived activity. */
  fresh?: boolean;
}

export function BeaconCard({ beacon, large = false, linkScan = false, fresh = false }: Props) {
  const color = vectorColor(beacon.vector);
  return (
    <article
      data-testid="signal-card"
      data-vector={beacon.vector}
      className={`panel border-l-4 p-3 ${color.split(' ')[1] ?? 'border-edge'} ${
        fresh ? 'animate-flashin' : ''
      }`}
    >
      <header className="flex flex-wrap items-center gap-2">
        <span className={`tag ${color}`}>{vectorLabel(beacon.vector)}</span>
        <time
          className={`font-mono text-dim ${large ? 'text-base' : 'text-xs'}`}
          dateTime={beacon.received_at}
        >
          {formatTime(beacon.received_at)}
        </time>
        <span className={`text-dim ${large ? 'text-sm' : 'text-xs'}`}>Assessment</span>
        {linkScan && beacon.scan_id ? (
          <Link
            to={`/scans/${beacon.scan_id}`}
            className={`font-mono text-cyan underline-offset-2 hover:underline ${
              large ? 'text-lg' : 'text-sm'
            }`}
          >
            {assessmentDisplayId(beacon.scan_token)}
          </Link>
        ) : (
          <span className={`font-mono text-ink ${large ? 'text-lg' : 'text-sm'}`}>
            {assessmentDisplayId(beacon.scan_token)}
          </span>
        )}
        {beacon.method && <span className="tag border-edge text-dim">{beacon.method}</span>}
      </header>

      <div className="mt-2">
        <SignalDetails decoded={beacon.decoded} />
      </div>
    </article>
  );
}
