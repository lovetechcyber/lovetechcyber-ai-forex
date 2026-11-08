
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import Analysis from "./pages/Analysis";
import Dashboard from "./pages/Dashboard";
import ForgotPassword from "./pages/ForgotPassword";
import Login from "./pages/Login";
import ResetPassword from "./pages/ResetPassword";
import MultiTimeframe from "./pages/MultiTimeframe";
import AIAnalyst from "./pages/AIAnalyst";
import AnalysisHistory from "./pages/AnalysisHistory";
import AnalysisHistoryDetail from "./pages/AnalysisHistoryDetail";
import UnifiedAnalysis from "./pages/UnifiedAnalysis";

import ProtectedRoute from "./components/ProtectedRoute";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public routes */}
        <Route path="/login" element={<Login />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/reset-password" element={<ResetPassword />} />

        {/* Protected routes */}
        <Route element={<ProtectedRoute />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/analysis" element={<Analysis />} />
          <Route path="/multi-timeframe" element={<MultiTimeframe />} />
          <Route path="/ai-analyst" element={<AIAnalyst />} />
          <Route path="/analysis-history" element={<AnalysisHistory />} />
          <Route
            path="/analysis-history/:id"
            element={<AnalysisHistoryDetail />}
          />
          <Route path="/unified-analysis" element={<UnifiedAnalysis />} />
        </Route>

        {/* Default routes */}
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
