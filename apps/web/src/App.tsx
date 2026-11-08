import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import Analysis from "./pages/Analysis";
import ProtectedRoute from "./components/ProtectedRoute";
import Dashboard from "./pages/Dashboard";
import ForgotPassword from "./pages/ForgotPassword";
import Login from "./pages/Login";
import ResetPassword from "./pages/ResetPassword";
import MultiTimeframe from "./pages/MultiTimeframe";
import AIAnalyst from "./pages/AIAnalyst";
import AnalysisHistory from "./pages/AnalysisHistory";
import AnalysisHistoryDetail from "./pages/AnalysisHistoryDetail";
import UnifiedAnalysis from "./pages/UnifiedAnalysis";
function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/reset-password" element={<ResetPassword />} />

        <Route element={<ProtectedRoute />}></Route>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/analysis" element={<Analysis />} />
        <Route path="/multi-timeframe" element={<MultiTimeframe />} />
        <Route path="/ai-analyst" element={<AIAnalyst />} />
        <Route path="/analysis-history" element={<AnalysisHistory />} />
        <Route path="/unified-analysis" element={<UnifiedAnalysis />} />
        <Route
          path="/analysis-history/:id"
          element={<AnalysisHistoryDetail />}
        />

        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
