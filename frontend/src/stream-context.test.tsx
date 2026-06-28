import type { ReactNode } from 'react';
import { renderHook, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { StreamProvider, useStreamContext } from './stream-context';
import { sampleBeacon } from './test/fixtures';

class NoopWebSocket {
  onopen: (() => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  onmessage: ((ev: MessageEvent) => void) | null = null;
  close = vi.fn();
}

function wrapper({ children }: { children: ReactNode }) {
  return <StreamProvider>{children}</StreamProvider>;
}

describe('StreamProvider', () => {
  beforeEach(() => {
    vi.stubGlobal('WebSocket', NoopWebSocket as unknown as typeof WebSocket);
    vi.stubGlobal('location', { protocol: 'http:', host: 'localhost:5173' });
  });

  afterEach(() => vi.restoreAllMocks());

  it('hydrates recent beacons from REST before live websocket events arrive', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => new Response(JSON.stringify([sampleBeacon]))),
    );

    const { result } = renderHook(() => useStreamContext(), { wrapper });

    await waitFor(() => expect(result.current.beacons).toHaveLength(1));
    expect(result.current.beacons[0]).toEqual(sampleBeacon);
  });
});
