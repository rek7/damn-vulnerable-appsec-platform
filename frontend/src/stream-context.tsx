// A single app-wide websocket connection. The live feed, the connection
// indicator, and any page that wants live scan/beacon updates subscribe here so
// we never open more than one socket.
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import type { ReactNode } from 'react';
import { listBeacons } from './api/client';
import { useStream } from './api/ws';
import type { StreamStatus } from './api/ws';
import type { Beacon, Scan } from './types';

const MAX_FEED = 200;

export interface StreamContextValue {
  status: StreamStatus;
  /** Most-recent-first beacons seen this session (capped). */
  beacons: Beacon[];
  /** Latest scan snapshots received over the wire, keyed by scan id. */
  scanUpdates: Record<string, Scan>;
  clearFeed: () => void;
}

const StreamContext = createContext<StreamContextValue | null>(null);

export function StreamProvider({ children }: { children: ReactNode }) {
  const [beacons, setBeacons] = useState<Beacon[]>([]);
  const [scanUpdates, setScanUpdates] = useState<Record<string, Scan>>({});
  const seen = useRef<Set<string>>(new Set());

  const onBeacon = useCallback((b: Beacon) => {
    if (seen.current.has(b.id)) return;
    seen.current.add(b.id);
    setBeacons((prev) => [b, ...prev].slice(0, MAX_FEED));
  }, []);

  useEffect(() => {
    let cancelled = false;
    void listBeacons()
      .then((initial) => {
        if (cancelled) return;
        setBeacons((prev) => {
          const byId = new Map<string, Beacon>();
          for (const b of [...initial, ...prev]) byId.set(b.id, b);
          for (const id of byId.keys()) seen.current.add(id);
          return Array.from(byId.values())
            .sort((a, b) => new Date(b.received_at).getTime() - new Date(a.received_at).getTime())
            .slice(0, MAX_FEED);
        });
      })
      .catch(() => {
        // The live socket is still useful if the initial REST hydration fails.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const onScanUpdate = useCallback((s: Scan) => {
    setScanUpdates((prev) => ({ ...prev, [s.id]: s }));
  }, []);

  const status = useStream({ onBeacon, onScanUpdate });

  const clearFeed = useCallback(() => {
    seen.current = new Set();
    setBeacons([]);
  }, []);

  const value = useMemo<StreamContextValue>(
    () => ({ status, beacons, scanUpdates, clearFeed }),
    [status, beacons, scanUpdates, clearFeed],
  );

  return <StreamContext.Provider value={value}>{children}</StreamContext.Provider>;
}

export function useStreamContext(): StreamContextValue {
  const ctx = useContext(StreamContext);
  if (!ctx) throw new Error('useStreamContext must be used within StreamProvider');
  return ctx;
}
