import { Link } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import HeroBanner from "../components/HeroBanner";

export default function Dashboard() {
  const { user } = useAuth();

  return (
    <div className="room">
      <HeroBanner />

      <div className="panel">
        <h2>Welcome back, {user?.full_name?.split(" ")[0] || "there"} {"\u{1F44B}"}</h2>
        <p className="hint">
          Logged in as <strong>{user?.full_name}</strong> ({user?.role}). Jump into a live
          diagnosis, track a dispatch, or manage your technician profile below.
        </p>
      </div>

      <div className="stat-cards">
        <div className="stat-card">
          <div className="stat-card-label">Start a new session</div>
          <div className="stat-card-value">
            <Link to="/customer">New Diagnosis &rarr;</Link>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-card-label">Track a technician</div>
          <div className="stat-card-value">
            <Link to="/dispatch">Dispatch Tracker &rarr;</Link>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-card-label">Technician tools</div>
          <div className="stat-card-value">
            <Link to="/technician">Technician Console &rarr;</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
