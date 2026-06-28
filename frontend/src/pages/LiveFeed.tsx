// Assessment activity across all scans, color-coded by assessment.
import { useMemo, useState } from 'react';
import { BeaconCard } from '../components/BeaconCard';
import { VECTOR_COLOR, vectorLabel } from '../modules';
import { useStreamContext } from '../stream-context';
import type { Vector } from '../types';

export function LiveFeed() {
  const { beacons } = useStreamContext();
  const [filter, setFilter] = useState<Vector | 'all'>('all');

  const shown = useMemo(
    () => (filter === 'all' ? beacons : beacons.filter((b) => b.vector === filter)),
    [beacons, filter],
  );

  // The most recent evidence id (for the fresh-arrival flash).
  const freshId = beacons[0]?.id;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-4">
        <h1 className="text-2xl font-black tracking-tight text-ink">Assessment Activity</h1>
        <span className="font-mono text-sm text-dim">{beacons.length} evidence events</span>
      </div>

      {/* Assessment filter / legend (color-coded) */}
      <div className="flex flex-wrap gap-2" role="group" aria-label="Filter by assessment">
        <button
          type="button"
          onClick={() => setFilter('all')}
          className={`tag ${filter === 'all' ? 'border-ink text-ink' : 'border-edge text-dim'}`}
        >
          all
        </button>
        {(Object.keys(VECTOR_COLOR) as Vector[]).map((v) => (
          <button
            key={v}
            type="button"
            onClick={() => setFilter(v)}
            className={`tag ${VECTOR_COLOR[v]} ${
              filter === v ? 'ring-1 ring-current' : 'opacity-70 hover:opacity-100'
            }`}
            data-testid={`filter-${v}`}
          >
            {vectorLabel(v)}
          </button>
        ))}
      </div>

      {shown.length === 0 ? (
        <div className="panel flex min-h-[40vh] items-center justify-center p-10">
          <p className="text-center text-lg italic text-dim">
            No assessment activity recorded yet.
            <br />
            <span className="text-sm">
              Run an assessment from any program to populate supporting evidence.
            </span>
          </p>
        </div>
      ) : (
        <div className="space-y-3" data-testid="live-feed-list">
          {shown.map((b) => (
            <BeaconCard key={b.id} beacon={b} large linkScan fresh={b.id === freshId} />
          ))}
        </div>
      )}
    </div>
  );
}
