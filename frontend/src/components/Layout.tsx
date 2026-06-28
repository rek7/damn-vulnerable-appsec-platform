// Enterprise app shell: persistent product navigation and outlet.
import { NavLink, Outlet } from 'react-router-dom';

const NAV = [
  { to: '/', label: 'Dashboard', end: true },
  { to: '/findings', label: 'Findings', end: false },
  { to: '/scans', label: 'Assessments', end: false },
  { to: '/live', label: 'Activity', end: false },
  { to: '/docs', label: 'Documentation', end: false },
];

export function Layout() {
  return (
    <div className="min-h-full bg-bg">
      <aside className="border-b border-edge bg-nav text-white lg:fixed lg:inset-y-0 lg:left-0 lg:w-64 lg:border-b-0 lg:border-r">
        <div className="flex h-full flex-col">
          <NavLink to="/" className="flex items-center gap-3 px-5 py-4">
            <span className="flex h-9 w-9 items-center justify-center rounded-md bg-white/10 text-sm font-black text-white ring-1 ring-white/20">
              D
            </span>
            <span className="min-w-0">
              <span className="block text-sm font-bold tracking-tight">DVAP</span>
              <span className="block text-xs text-white/60">Assessment workspace</span>
            </span>
          </NavLink>
          <nav className="flex flex-wrap gap-1 px-3 pb-3 lg:flex-col lg:gap-1">
            {NAV.map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                end={n.end}
                className={({ isActive }) => `nav-link ${isActive ? 'nav-link-active' : ''}`}
              >
                {n.label}
              </NavLink>
            ))}
          </nav>
          <div className="mt-auto hidden border-t border-white/10 p-4 lg:block">
            <p className="rounded-md border border-white/10 bg-white/5 px-3 py-2 text-xs leading-relaxed text-white/70">
              Workspace policy: Standard. Assessments preserve findings, evidence, and review
              history.
            </p>
          </div>
        </div>
      </aside>

      <div className="lg:pl-64">
        <header className="sticky top-0 z-20 border-b border-edge bg-panel/95 backdrop-blur">
          <div className="flex min-h-14 flex-wrap items-center justify-between gap-3 px-4 py-3 lg:px-8">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-dim">
                Security operations workspace
              </p>
              <p className="text-sm font-semibold text-ink">
                Assessments, findings, policy decisions, and evidence
              </p>
            </div>
            <div className="flex items-center gap-3">
              <span className="tag border-cyan/60 bg-cyan/10 text-cyan">Standard</span>
            </div>
          </div>
        </header>

        <main className="mx-auto w-full max-w-7xl px-4 py-6 lg:px-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
