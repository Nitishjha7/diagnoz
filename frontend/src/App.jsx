import { Routes, Route, Link, Navigate } from "react-router-dom";
import { useAuth } from "./hooks/useAuth";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import CustomerRoom from "./pages/CustomerRoom";
import TechnicianConsole from "./pages/TechnicianConsole";
import DispatchTracker from "./pages/DispatchTracker";
import ProtectedRoute from "./components/ProtectedRoute";

function Home() {
  const { user, logout } = useAuth();

  return (
    <div className="home">
      <h1>DiagnoZ</h1>
      <p>Logged in as {user?.full_name} ({user?.role})</p>
      <nav>
        <Link to="/customer">Customer Room</Link>
        <Link to="/technician">Technician Console</Link>
        <Link to="/dispatch">Dispatch Tracker</Link>
      </nav>
      <button onClick={logout}>Logout</button>
    </div>
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
          <ProtectedRoute>
            <Home />
          </ProtectedRoute>
        }
      />
      <Route
        path="/customer"
        element={
          <ProtectedRoute>
            <CustomerRoom />
          </ProtectedRoute>
        }
      />
      <Route
        path="/technician"
        element={
          <ProtectedRoute>
            <TechnicianConsole />
          </ProtectedRoute>
        }
      />
      <Route
        path="/dispatch"
        element={
          <ProtectedRoute>
            <DispatchTracker />
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
