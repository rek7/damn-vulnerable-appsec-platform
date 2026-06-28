// Test helpers: a JSON-fetch mock router and provider wrappers.
import type { ReactElement } from 'react';
import { render } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { vi } from 'vitest';

/**
 * Install a fetch mock that dispatches on a `METHOD path` key. Each handler
 * receives the RequestInit and returns the JSON body to respond with. Unmatched
 * routes reject so missing stubs surface loudly.
 */
export type FetchHandler = (init: RequestInit | undefined) => unknown;

export function mockFetch(routes: Record<string, FetchHandler>): ReturnType<typeof vi.fn> {
  const fn = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === 'string' ? input : input.toString();
    const method = (init?.method ?? 'GET').toUpperCase();
    const key = `${method} ${url}`;
    const handler = routes[key] ?? routes[url];
    if (!handler) {
      throw new Error(`unmocked fetch: ${key}`);
    }
    const body = handler(init);
    return new Response(JSON.stringify(body), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  });
  vi.stubGlobal('fetch', fn);
  return fn;
}

export function renderWithRouter(ui: ReactElement, initialEntries: string[] = ['/']) {
  return render(<MemoryRouter initialEntries={initialEntries}>{ui}</MemoryRouter>);
}
