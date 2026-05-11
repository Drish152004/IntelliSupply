import { Navigate, Route, Routes } from 'react-router';
import Home from './pages/Home';
import Inventory from './pages/Inventory';
import Overview from './pages/Overview';
import CopilotPage from './pages/CopilotPage';

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/routes" replace />} />
      <Route path="/routes" element={<Home />} />
      <Route path="/inventory" element={<Inventory />} />
      <Route path="/overview" element={<Overview />} />
      <Route path="/copilot" element={<CopilotPage />} />
    </Routes>
  );
}
