import { useState } from "react";
import { api } from "../lib/api";
import AnnotationCanvas from "../components/AnnotationCanvas";

const STATUS_BADGE = {
  PENDING: "badge-warning",
  ACCEPTED: "badge-neutral",
  IN_PROGRESS: "badge-neutral",
  COMPLETED: "badge-success",
};

export default function TechnicianConsole() {
  const [latitude, setLatitude] = useState("28.6139");
  const [longitude, setLongitude] = useState("77.2090");
  const [profileStatus, setProfileStatus] = useState("");
  const [dispatchId, setDispatchId] = useState("");
  const [dispatch, setDispatch] = useState(null);
  const [startOtp, setStartOtp] = useState("");
  const [endOtp, setEndOtp] = useState("");
  const [error, setError] = useState("");
  const [sessionId, setSessionId] = useState("");

  async function saveLocation() {
    setError("");
    try {
      await api.createTechnicianProfile(parseFloat(latitude), parseFloat(longitude));
      setProfileStatus("Location saved.");
    } catch (err) {
      setError(err.message);
    }
  }

  async function loadDispatch() {
    setError("");
    try {
      const d = await api.getDispatch(dispatchId);
      setDispatch(d);
    } catch (err) {
      setError(err.message);
    }
  }

  async function accept() {
    setError("");
    try {
      setDispatch(await api.acceptDispatch(dispatchId));
    } catch (err) {
      setError(err.message);
    }
  }

  async function verifyStart() {
    setError("");
    try {
      setDispatch(await api.verifyStartOtp(dispatchId, startOtp));
    } catch (err) {
      setError(err.message);
    }
  }

  async function verifyEnd() {
    setError("");
    try {
      setDispatch(await api.verifyEndOtp(dispatchId, endOtp));
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="room">
      <h1>Technician Console</h1>
      <p className="hint" style={{ marginBottom: 20 }}>
        Manage your location, work through an assigned dispatch's dual-OTP lifecycle, and
        draw annotations for a customer's live session.
      </p>

      <div className="panel">
        <h2>My Location</h2>
        <label>
          Latitude
          <input value={latitude} onChange={(e) => setLatitude(e.target.value)} />
        </label>
        <label>
          Longitude
          <input value={longitude} onChange={(e) => setLongitude(e.target.value)} />
        </label>
        <button onClick={saveLocation}>Save Location</button>
        {profileStatus && <p className="hint" style={{ marginTop: 8 }}>{profileStatus}</p>}
      </div>

      <div className="panel">
        <h2>Dispatch Lifecycle</h2>
        <label>
          Dispatch ID
          <input value={dispatchId} onChange={(e) => setDispatchId(e.target.value)} />
        </label>
        <button onClick={loadDispatch}>Load</button>

        {dispatch && (
          <div className="diagnosis-card">
            <div className="kv-row" style={{ marginBottom: 8 }}>
              <dt>Status</dt>
              <dd>
                <span className={`badge ${STATUS_BADGE[dispatch.dispatch_status] || "badge-neutral"}`}>
                  {dispatch.dispatch_status}
                </span>
              </dd>
            </div>
            <div className="kv-row">
              <dt>Technician Earnings</dt>
              <dd>&#8377;{dispatch.technician_earnings}</dd>
            </div>

            {dispatch.dispatch_status === "PENDING" && (
              <button style={{ marginTop: 12, width: "100%" }} onClick={accept}>
                Accept
              </button>
            )}

            {dispatch.dispatch_status === "ACCEPTED" && (
              <div style={{ marginTop: 12, display: "flex", gap: 8 }}>
                <input placeholder="Start OTP" value={startOtp} onChange={(e) => setStartOtp(e.target.value)} />
                <button onClick={verifyStart}>Verify Start OTP</button>
              </div>
            )}

            {dispatch.dispatch_status === "IN_PROGRESS" && (
              <div style={{ marginTop: 12, display: "flex", gap: 8 }}>
                <input placeholder="End OTP" value={endOtp} onChange={(e) => setEndOtp(e.target.value)} />
                <button onClick={verifyEnd}>Verify End OTP</button>
              </div>
            )}
          </div>
        )}
        {error && <p className="error" style={{ marginTop: 8 }}>{error}</p>}
      </div>

      <div className="panel">
        <h2>Draw for Customer</h2>
        <label>
          Session ID
          <input value={sessionId} onChange={(e) => setSessionId(e.target.value)} />
        </label>
        {sessionId && (
          <div className="video-stage" style={{ marginTop: 10 }}>
            <AnnotationCanvas sessionId={sessionId} />
          </div>
        )}
      </div>
    </div>
  );
}
