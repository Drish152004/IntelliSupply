import { Navigate, Route, Routes, useLocation } from 'react-router';
import Home from './pages/Home';
import Inventory from './pages/Inventory';
import Overview from './pages/Overview';
import FloatingCopilot from './components/FloatingCopilot';

export default function App() {
  const location = useLocation();
  const showFloatingCopilot = location.pathname === '/overview';

  return (
    <>
      <Routes>
        <Route path="/" element={<Navigate to="/routes" replace />} />
        <Route path="/routes" element={<Home />} />
        <Route path="/inventory" element={<Inventory />} />
        <Route path="/overview" element={<Overview />} />
      </Routes>
      {showFloatingCopilot && <FloatingCopilot />}
    </>
  );
}
