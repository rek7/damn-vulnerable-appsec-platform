// Router and shared activity provider for assessment updates.
import { Navigate, Route, Routes } from 'react-router-dom';
import { Layout } from './components/Layout';
import { StreamProvider } from './stream-context';
import { Home } from './pages/Home';
import { ModulePage } from './pages/ModulePage';
import { Scans } from './pages/Scans';
import { ScanDetail } from './pages/ScanDetail';
import { LiveFeed } from './pages/LiveFeed';
import { Findings } from './pages/Findings';
import { Docs } from './pages/Docs';

export default function App() {
  return (
    <StreamProvider>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Home />} />
          <Route path="findings" element={<Findings />} />
          <Route path="module/:moduleId" element={<ModulePage />} />
          <Route path="scans" element={<Scans />} />
          <Route path="scans/:scanId" element={<ScanDetail />} />
          <Route path="live" element={<LiveFeed />} />
          <Route path="docs" element={<Docs />} />
          <Route path="docs/:docId" element={<Docs />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </StreamProvider>
  );
}
