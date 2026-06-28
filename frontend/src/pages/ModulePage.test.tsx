import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { ModulePage } from './ModulePage';
import { StreamProvider } from '../stream-context';
import { mockFetch } from '../test/utils';
import { sampleBeacon, sampleScan } from '../test/fixtures';

class NoopWebSocket {
  onopen: (() => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  onmessage: ((ev: MessageEvent) => void) | null = null;
  close = vi.fn();
}

function renderModule(moduleId: string) {
  return render(
    <MemoryRouter initialEntries={[`/module/${moduleId}`]}>
      <StreamProvider>
        <Routes>
          <Route path="/module/:moduleId" element={<ModulePage />} />
        </Routes>
      </StreamProvider>
    </MemoryRouter>,
  );
}

describe('ModulePage', () => {
  beforeEach(() => {
    vi.stubGlobal('WebSocket', NoopWebSocket as unknown as typeof WebSocket);
    vi.stubGlobal('location', { protocol: 'http:', host: 'localhost:5173' });
  });
  afterEach(() => vi.restoreAllMocks());

  it('renders the SCA module with a run button per vector', async () => {
    renderModule('sca');

    expect(
      await screen.findByRole('heading', { name: 'SCA / Dependency Analysis' }),
    ).toBeInTheDocument();
    expect(screen.getByTestId('run-sample-setup_py_exec')).toBeInTheDocument();
    expect(screen.getByTestId('run-sample-gemspec_eval')).toBeInTheDocument();
    expect(screen.getByTestId('run-sample-npm_lifecycle')).toBeInTheDocument();
  });

  it('shows assessment context instead of settings controls', async () => {
    renderModule('iac');

    await screen.findByRole('heading', { name: 'IaC Scanning' });
    expect(screen.getByText(/assessment context/i)).toBeInTheDocument();
    expect(screen.getByText(/assessment profile/i)).toBeInTheDocument();
    expect(screen.queryByText(/protected mode/i)).not.toBeInTheDocument();
  });

  it('runs a validation scenario: POSTs the right body and renders the inline result', async () => {
    const user = userEvent.setup();
    const fetchMock = mockFetch({
      'GET /api/beacons': () => [],
      'POST /api/scans': () => sampleScan,
      'GET /api/beacons?scan_token=ab12cd34ef56': () => [sampleBeacon],
    });
    renderModule('iac');

    const runBtn = await screen.findByTestId('run-sample-checkov_external_checks');
    await user.click(runBtn);

    await waitFor(() => {
      const postCall = fetchMock.mock.calls.find(
        ([url, init]) =>
          url === '/api/scans' && (init as RequestInit | undefined)?.method === 'POST',
      );
      expect(postCall).toBeTruthy();
      expect(JSON.parse((postCall?.[1] as RequestInit).body as string)).toEqual({
        module: 'iac',
        vector: 'checkov_external_checks',
        source_type: 'sample',
      });
    });

    const result = await screen.findByTestId('inline-result');
    expect(
      within(result).getByText(
        /IaC policy assessment completed and generated correlated evidence/i,
      ),
    ).toBeInTheDocument();
    expect(within(result).getByText(/full detail/i)).toBeInTheDocument();
    expect(await within(result).findAllByText('MASKED')).toHaveLength(2);
    expect(within(result).queryByText(/AKIA_FAKE_DVSEXAMPLE000/)).not.toBeInTheDocument();
  });

  it('renders an unknown-module fallback', async () => {
    renderModule('bogus');
    expect(await screen.findByText(/unknown module/i)).toBeInTheDocument();
  });
});
