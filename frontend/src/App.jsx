import { Routes, Route, Navigate } from "react-router-dom";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import Dashboard from "./pages/Dashboard";
import CustomerRoom from "./pages/CustomerRoom";
import TechnicianConsole from "./pages/TechnicianConsole";
import DispatchTracker from "./pages/DispatchTracker";
import ProtectedRoute from "./components/ProtectedRoute";
import AppShell from "./components/AppShell";

function Shell({ children }) {
  return (
    <ProtectedRoute>
      <AppShell>{children}</AppShell>
    </ProtectedRoute>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route
        path="/"
        element={
          <Shell>
            <Dashboard />
          </Shell>
        }
      />
      <Route
        path="/customer"
        element={
          <Shell>
            <CustomerRoom />
          </Shell>
        }
      />
      <Route
        path="/technician"
        element={
          <Shell>
            <TechnicianConsole />
          </Shell>
        }
      />
      <Route
        path="/dispatch"
        element={
          <Shell>
            <DispatchTracker />
          </Shell>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
