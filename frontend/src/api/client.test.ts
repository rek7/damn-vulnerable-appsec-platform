import { describe, expect, it, vi } from 'vitest';
import {
  ApiError,
  applyPreset,
  createScan,
  createUploadScan,
  getConfig,
  listBeacons,
  updateConfig,
} from './client';
import { hardenedConfig, sampleScan, vulnerableConfig } from '../test/fixtures';

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

type FetchArgs = [input: RequestInfo | URL, init?: RequestInit];

/** A typed fetch mock so `mock.calls` is a proper [url, init?] tuple. */
function fetchMockOf(impl: (...args: FetchArgs) => Response) {
  return vi.fn((input: RequestInfo | URL, init?: RequestInit) =>
    Promise.resolve(impl(input, init)),
  );
}

describe('api client', () => {
  it('createScan POSTs JSON to /api/scans and returns the Scan', async () => {
    const fetchMock = fetchMockOf(() => jsonResponse(sampleScan));
    vi.stubGlobal('fetch', fetchMock);

    const scan = await createScan({
      module: 'iac',
      vector: 'checkov_external_checks',
      source_type: 'sample',
    });

    expect(scan).toEqual(sampleScan);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe('/api/scans');
    expect(init?.method).toBe('POST');
    expect(JSON.parse(init?.body as string)).toMatchObject({
      module: 'iac',
      source_type: 'sample',
    });
  });

  it('createUploadScan sends multipart with meta + archive', async () => {
    const fetchMock = fetchMockOf(() => jsonResponse(sampleScan));
    vi.stubGlobal('fetch', fetchMock);
    const file = new File(['payload'], 'evil.zip', { type: 'application/zip' });

    await createUploadScan({ module: 'sca', source_type: 'upload' }, file);

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe('/api/scans');
    expect(init?.method).toBe('POST');
    const form = init?.body as FormData;
    expect(form).toBeInstanceOf(FormData);
    expect(JSON.parse(form.get('meta') as string)).toMatchObject({
      module: 'sca',
      source_type: 'upload',
    });
    expect(form.get('archive')).toBeInstanceOf(File);
  });

  it('createUploadScan falls back to the current upload route when /api/scans rejects multipart', async () => {
    const responses = [
      jsonResponse({ detail: 'JSON body expected' }, 422),
      jsonResponse(sampleScan),
    ];
    let i = 0;
    const fetchMock = fetchMockOf(() => responses[i++]);
    vi.stubGlobal('fetch', fetchMock);
    const file = new File(['payload'], 'evil.zip', { type: 'application/zip' });

    await createUploadScan({ module: 'sca', source_type: 'upload' }, file);

    expect(fetchMock.mock.calls).toHaveLength(2);
    expect(fetchMock.mock.calls[0][0]).toBe('/api/scans');
    expect(fetchMock.mock.calls[1][0]).toBe('/api/scans/upload');
  });

  it('getConfig and updateConfig hit /api/config', async () => {
    const responses = [
      jsonResponse(vulnerableConfig),
      jsonResponse({ ...vulnerableConfig, block_egress: true }),
    ];
    let i = 0;
    const fetchMock = fetchMockOf(() => responses[i++]);
    vi.stubGlobal('fetch', fetchMock);

    expect(await getConfig()).toEqual(vulnerableConfig);

    const updated = await updateConfig({ block_egress: true });
    expect(updated.block_egress).toBe(true);
    const [url, init] = fetchMock.mock.calls[1];
    expect(url).toBe('/api/config');
    expect(init?.method).toBe('PUT');
  });

  it('applyPreset POSTs to /api/config/preset/{name}', async () => {
    const fetchMock = fetchMockOf(() => jsonResponse(hardenedConfig));
    vi.stubGlobal('fetch', fetchMock);

    const cfg = await applyPreset('hardened');
    expect(cfg).toEqual(hardenedConfig);
    expect(fetchMock.mock.calls[0][0]).toBe('/api/config/preset/hardened');
  });

  it('listBeacons appends filter query params', async () => {
    const fetchMock = fetchMockOf(() => jsonResponse([]));
    vi.stubGlobal('fetch', fetchMock);

    await listBeacons({ scan_token: 'ab12cd34ef56', vector: 'symlink_traversal' });
    const url = fetchMock.mock.calls[0][0] as string;
    expect(url).toContain('/api/beacons?');
    expect(url).toContain('scan_token=ab12cd34ef56');
    expect(url).toContain('vector=symlink_traversal');
  });

  it('throws ApiError on non-2xx', async () => {
    const fetchMock = vi.fn(async () => jsonResponse({ detail: 'bad module' }, 422));
    vi.stubGlobal('fetch', fetchMock);

    await expect(getConfig()).rejects.toBeInstanceOf(ApiError);
  });
});
