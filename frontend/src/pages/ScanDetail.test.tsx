import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { ScanDetail } from './ScanDetail';
import { StreamProvider } from '../stream-context';
import { mockFetch } from '../test/utils';
import { emptyExfilBeacon, sampleBeacon, sampleScan } from '../test/fixtures';

// StreamProvider opens a websocket on mount; a no-op stub keeps it quiet.
class NoopWebSocket {
  onopen: (() => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  onmessage: ((ev: MessageEvent) => void) | null = null;
  close = vi.fn();
}

function renderDetail(scanId = 'scan-1') {
  return render(
    <MemoryRouter initialEntries={[`/scans/${scanId}`]}>
      <StreamProvider>
        <Routes>
          <Route path="/scans/:scanId" element={<ScanDetail />} />
        </Routes>
      </StreamProvider>
    </MemoryRouter>,
  );
}

describe('ScanDetail', () => {
  beforeEach(() => {
    vi.stubGlobal('WebSocket', NoopWebSocket as unknown as typeof WebSocket);
    vi.stubGlobal('location', { protocol: 'http:', host: 'localhost:5173' });
  });
  afterEach(() => vi.restoreAllMocks());

  it('renders analyzers, result, and step log', async () => {
    mockFetch({
      'GET /api/scans/scan-1': () => sampleScan,
      'GET /api/beacons?scan_token=ab12cd34ef56': () => [sampleBeacon],
    });
    renderDetail();

    await waitFor(() =>
      expect(
        screen.getByText(/IaC policy assessment completed and generated correlated evidence/i),
      ).toBeInTheDocument(),
    );

    const analyzers = screen.getByTestId('analyzer-list');
    expect(within(analyzers).getByText('checkov')).toBeInTheDocument();
    expect(within(analyzers).getByText('ok')).toBeInTheDocument();

    const log = screen.getByTestId('step-log');
    expect(within(log).getByText(/running IaC policy assessment/)).toBeInTheDocument();
  });

  it('renders the signal timeline with masked sensitive values', async () => {
    mockFetch({
      'GET /api/scans/scan-1': () => sampleScan,
      'GET /api/beacons?scan_token=ab12cd34ef56': () => [sampleBeacon],
    });
    renderDetail();

    const timeline = await screen.findByTestId('signal-timeline');
    expect(within(timeline).queryByText(/AKIA_FAKE_DVSEXAMPLE000/)).not.toBeInTheDocument();
    const maskedLabels = within(timeline).getAllByText('MASKED');
    expect(maskedLabels.length).toBeGreaterThanOrEqual(2);
  });

  it('shows the empty signal note when details are not recorded', async () => {
    mockFetch({
      'GET /api/scans/scan-1': () => sampleScan,
      'GET /api/beacons?scan_token=ab12cd34ef56': () => [emptyExfilBeacon],
    });
    renderDetail();

    await waitFor(() => expect(screen.getByTestId('signal-empty')).toBeInTheDocument());
  });

  it('shows the no-signals note when nothing correlated', async () => {
    const blockedScan = { ...sampleScan, beacon_count: 0 };
    mockFetch({
      'GET /api/scans/scan-1': () => blockedScan,
      'GET /api/beacons?scan_token=ab12cd34ef56': () => [],
    });
    renderDetail();

    await waitFor(() => expect(screen.getByTestId('no-signals')).toBeInTheDocument());
  });
});
