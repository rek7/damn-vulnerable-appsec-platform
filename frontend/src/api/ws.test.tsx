import { act, render, renderHook, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useStream } from './ws';
import type { Beacon, Scan } from '../types';
import { sampleBeacon, sampleScan } from '../test/fixtures';

// A minimal controllable WebSocket mock.
class MockWebSocket {
  static instances: MockWebSocket[] = [];
  static OPEN = 1;

  url: string;
  readyState = 0;
  onopen: (() => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  onmessage: ((ev: MessageEvent) => void) | null = null;

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
  }

  // Test-side helpers.
  open() {
    this.readyState = MockWebSocket.OPEN;
    this.onopen?.();
  }
  emit(data: unknown) {
    this.onmessage?.({ data: JSON.stringify(data) } as MessageEvent);
  }
  emitRaw(data: string) {
    this.onmessage?.({ data } as MessageEvent);
  }
  triggerClose() {
    this.readyState = 3;
    this.onclose?.();
  }

  close = vi.fn(() => {
    this.readyState = 3;
  });

  static latest() {
    return MockWebSocket.instances[MockWebSocket.instances.length - 1];
  }
  static reset() {
    MockWebSocket.instances = [];
  }
}

describe('useStream', () => {
  beforeEach(() => {
    MockWebSocket.reset();
    vi.stubGlobal('WebSocket', MockWebSocket as unknown as typeof WebSocket);
    // jsdom needs a location host for streamUrl().
    vi.stubGlobal('location', { protocol: 'http:', host: 'localhost:5173' });
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it('connects to /api/stream and reports open', async () => {
    const { result } = renderHook(() => useStream({}));
    expect(result.current).toBe('connecting');

    const ws = MockWebSocket.latest();
    expect(ws.url).toContain('/api/stream');
    expect(ws.url.startsWith('ws://')).toBe(true);

    act(() => ws.open());
    await waitFor(() => expect(result.current).toBe('open'));
  });

  it('routes scan_update and beacon envelopes to the matching handlers', async () => {
    const scans: Scan[] = [];
    const beacons: Beacon[] = [];
    renderHook(() =>
      useStream({
        onScanUpdate: (s) => scans.push(s),
        onBeacon: (b) => beacons.push(b),
      }),
    );

    const ws = MockWebSocket.latest();
    act(() => ws.open());

    act(() => ws.emit({ type: 'scan_update', scan: sampleScan }));
    act(() => ws.emit({ type: 'beacon', beacon: sampleBeacon }));

    expect(scans).toHaveLength(1);
    expect(scans[0].id).toBe(sampleScan.id);
    expect(beacons).toHaveLength(1);
    expect(beacons[0].id).toBe(sampleBeacon.id);
  });

  it('ignores malformed / unknown / incomplete frames', () => {
    const onEnvelope = vi.fn();
    const onBeacon = vi.fn();
    renderHook(() => useStream({ onEnvelope, onBeacon }));
    const ws = MockWebSocket.latest();
    act(() => ws.open());

    act(() => ws.emitRaw('not json'));
    act(() => ws.emit({ type: 'mystery' }));
    act(() => ws.emit({ type: 'beacon' }));

    expect(onEnvelope).not.toHaveBeenCalled();
    expect(onBeacon).not.toHaveBeenCalled();
  });

  it('reconnects with backoff after the socket closes', () => {
    vi.useFakeTimers();
    renderHook(() => useStream({}));
    expect(MockWebSocket.instances).toHaveLength(1);

    act(() => MockWebSocket.latest().triggerClose());

    // First backoff is 500ms.
    act(() => vi.advanceTimersByTime(500));
    expect(MockWebSocket.instances).toHaveLength(2);
  });

  it('closes the socket and stops reconnecting on unmount', () => {
    function Harness() {
      useStream({});
      return null;
    }
    const { unmount } = render(<Harness />);
    const ws = MockWebSocket.latest();

    unmount();
    expect(ws.close).toHaveBeenCalled();

    // A close fired after unmount must not schedule a reconnect.
    vi.useFakeTimers();
    act(() => ws.triggerClose());
    act(() => vi.advanceTimersByTime(5000));
    expect(MockWebSocket.instances).toHaveLength(1);
  });
});
