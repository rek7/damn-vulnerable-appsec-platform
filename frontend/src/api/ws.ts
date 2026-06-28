// useStream: subscribes to the /api/stream websocket, parses the scan_update /
// beacon envelopes, and auto-reconnects with capped backoff.
import { useEffect, useRef, useState } from 'react';
import type { Beacon, Scan, StreamEnvelope } from '../types';

export type StreamStatus = 'connecting' | 'open' | 'closed';

export interface StreamHandlers {
  onScanUpdate?: (scan: Scan) => void;
  onBeacon?: (beacon: Beacon) => void;
  onEnvelope?: (env: StreamEnvelope) => void;
}

/** Build the absolute ws(s):// URL for /api/stream from the current page origin. */
export function streamUrl(): string {
  if (typeof window === 'undefined' || !window.location) {
    return 'ws://localhost/api/stream';
  }
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${proto}//${window.location.host}/api/stream`;
}

function parseEnvelope(data: unknown): StreamEnvelope | null {
  if (typeof data !== 'string') return null;
  try {
    const obj = JSON.parse(data) as unknown;
    if (!obj || typeof obj !== 'object') return null;
    if ('type' in obj && obj.type === 'scan_update' && 'scan' in obj && obj.scan) {
      return obj as StreamEnvelope;
    }
    if ('type' in obj && obj.type === 'beacon' && 'beacon' in obj && obj.beacon) {
      return obj as StreamEnvelope;
    }
  } catch {
    // ignore malformed frames
  }
  return null;
}

/**
 * Hook returning the live connection status. Handlers are read from a ref so the
 * socket is only (re)created when `enabled` changes — passing fresh callbacks
 * inline every render will NOT churn the connection.
 */
export function useStream(handlers: StreamHandlers, enabled = true): StreamStatus {
  const [status, setStatus] = useState<StreamStatus>('connecting');
  const handlersRef = useRef(handlers);
  handlersRef.current = handlers;

  useEffect(() => {
    if (!enabled) {
      setStatus('closed');
      return;
    }

    let ws: WebSocket | null = null;
    let retry = 0;
    let reconnectTimer: ReturnType<typeof setTimeout> | undefined;
    let closed = false;

    const connect = () => {
      setStatus('connecting');
      ws = new WebSocket(streamUrl());

      ws.onopen = () => {
        retry = 0;
        setStatus('open');
      };

      ws.onmessage = (ev: MessageEvent) => {
        const env = parseEnvelope(ev.data);
        if (!env) return;
        const h = handlersRef.current;
        h.onEnvelope?.(env);
        if (env.type === 'scan_update') h.onScanUpdate?.(env.scan);
        else if (env.type === 'beacon') h.onBeacon?.(env.beacon);
      };

      ws.onerror = () => {
        // surfaced via onclose
      };

      ws.onclose = () => {
        setStatus('closed');
        if (closed) return;
        // Capped exponential backoff: 0.5s, 1s, 2s, 4s … max 10s.
        const delay = Math.min(10000, 500 * 2 ** retry);
        retry += 1;
        reconnectTimer = setTimeout(connect, delay);
      };
    };

    connect();

    return () => {
      closed = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (ws) {
        ws.onclose = null;
        ws.onerror = null;
        ws.onmessage = null;
        ws.onopen = null;
        ws.close();
      }
    };
  }, [enabled]);

  return status;
}
