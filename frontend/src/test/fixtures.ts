// Shared test fixtures mirroring API scan/beacon shapes.
import type { Beacon, Scan } from '../types';

export const sampleBeacon: Beacon = {
  id: 'beacon-1',
  scan_id: 'scan-1',
  scan_token: 'ab12cd34ef56',
  vector: 'checkov_external_checks',
  raw: '4157535f4143434553535f4b45595f49443d414b49415f46414b455f445653',
  decoded:
    'AWS_ACCESS_KEY_ID=AKIA_FAKE_DVSEXAMPLE000\nGITHUB_TOKEN=ghp_FAKE0000dvsExampleToken0000000000',
  received_at: '2026-06-25T12:00:01.000Z',
  method: 'GET',
  path: '/b/ab12cd34ef56/checkov_external_checks',
  remote: '172.18.0.4',
};

export const emptyExfilBeacon: Beacon = {
  id: 'beacon-2',
  scan_id: 'scan-1',
  scan_token: 'ab12cd34ef56',
  vector: 'checkov_external_checks',
  raw: '',
  decoded: '',
  received_at: '2026-06-25T12:00:02.000Z',
  method: 'GET',
  path: '/b/ab12cd34ef56/checkov_external_checks',
  remote: '172.18.0.4',
};

export const sampleScan: Scan = {
  id: 'scan-1',
  scan_token: 'ab12cd34ef56',
  module: 'iac',
  vector: 'checkov_external_checks',
  source: { type: 'sample', ref: 'sample' },
  status: 'completed',
  result: 'checkov loaded external check; assessment signal generated.',
  analyzers: [
    {
      name: 'checkov',
      vector: 'checkov_external_checks',
      triggered: true,
      status: 'ok',
      summary: 'external-checks-dir loaded; extra_check.py imported',
      duration_ms: 842,
    },
  ],
  steps: [
    { ts: '2026-06-25T12:00:00.000Z', level: 'info', message: 'fetched sample repo' },
    { ts: '2026-06-25T12:00:00.500Z', level: 'warn', message: 'running checkov on unsafe path' },
  ],
  beacon_count: 1,
  created_at: '2026-06-25T12:00:00.000Z',
  updated_at: '2026-06-25T12:00:01.000Z',
};
