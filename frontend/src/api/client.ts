// REST client for the DVAP API. All calls are relative to /api so the same
// build works behind the Vite dev proxy and the nginx container proxy.
import type { Beacon, Config, CreateScanJSON, CreateScanMeta, Scan } from '../types';

export const API_BASE = '/api';

export class ApiError extends Error {
  readonly status: number;
  readonly body: string;

  constructor(status: number, body: string) {
    super(`API ${status}: ${body || '(no body)'}`);
    this.name = 'ApiError';
    this.status = status;
    this.body = body;
  }
}

async function parse<T>(res: Response): Promise<T> {
  const text = await res.text();
  if (!res.ok) {
    throw new ApiError(res.status, text);
  }
  return (text ? JSON.parse(text) : null) as T;
}

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { Accept: 'application/json' },
  });
  return parse<T>(res);
}

async function sendJSON<T>(path: string, method: 'POST' | 'PUT', body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify(body),
  });
  return parse<T>(res);
}

// ----- Scans -----------------------------------------------------------------

export function listScans(): Promise<Scan[]> {
  return getJSON<Scan[]>('/scans');
}

export function getScan(id: string): Promise<Scan> {
  return getJSON<Scan>(`/scans/${encodeURIComponent(id)}`);
}

/** Create + run a sample or git scan (JSON body). Resolves when the scan completes. */
export function createScan(body: CreateScanJSON): Promise<Scan> {
  return sendJSON<Scan>('/scans', 'POST', body);
}

/** Create + run an upload scan (multipart: `meta` JSON field + `archive` file). */
export async function createUploadScan(meta: CreateScanMeta, archive: File): Promise<Scan> {
  try {
    return await postUploadScan('/scans', meta, archive);
  } catch (e) {
    if (e instanceof ApiError && [404, 405, 415, 422].includes(e.status)) {
      return postUploadScan('/scans/upload', meta, archive);
    }
    throw e;
  }
}

async function postUploadScan(path: string, meta: CreateScanMeta, archive: File): Promise<Scan> {
  const form = new FormData();
  form.append('meta', JSON.stringify(meta));
  form.append('archive', archive);
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    body: form,
    headers: { Accept: 'application/json' },
  });
  return parse<Scan>(res);
}

// ----- Config / mitigations --------------------------------------------------

export function getConfig(): Promise<Config> {
  return getJSON<Config>('/config');
}

/** Partial or full config update. */
export function updateConfig(patch: Partial<Config>): Promise<Config> {
  return sendJSON<Config>('/config', 'PUT', patch);
}

export function applyPreset(name: 'vulnerable' | 'hardened'): Promise<Config> {
  return sendJSON<Config>(`/config/preset/${name}`, 'POST', {});
}

// ----- Beacons ---------------------------------------------------------------

export function listBeacons(filters?: { scan_token?: string; vector?: string }): Promise<Beacon[]> {
  const params = new URLSearchParams();
  if (filters?.scan_token) params.set('scan_token', filters.scan_token);
  if (filters?.vector) params.set('vector', filters.vector);
  const qs = params.toString();
  return getJSON<Beacon[]>(`/beacons${qs ? `?${qs}` : ''}`);
}
