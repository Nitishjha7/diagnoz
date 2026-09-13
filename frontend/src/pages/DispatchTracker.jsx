import { useState } from "react";
import { api } from "../lib/api";

export default function DispatchTracker() {
  const [latitude, setLatitude] = useState("28.6150");
  const [longitude, setLongitude] = useState("77.2100");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function requestDispatch() {
    setError("");
    setResult(null);
    setLoading(true);
    try {
      const data = await api.createDispatch(parseFloat(latitude), parseFloat(longitude));
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="room">
      <h1>Dispatch Tracker</h1>
      <p className="hint" style={{ marginBottom: 20 }}>
        Requests the nearest available technician (PostGIS KNN, 5km radius) and returns
        one-time start/end OTPs for the dual-OTP verification flow.
      </p>

      <div className="panel" style={{ maxWidth: 420 }}>
        <label>
          Latitude
          <input value={latitude} onChange={(e) => setLatitude(e.target.value)} />
        </label>
        <label>
          Longitude
          <input value={longitude} onChange={(e) => setLongitude(e.target.value)} />
        </label>
        <button onClick={requestDispatch} disabled={loading} style={{ width: "100%" }}>
          {loading ? "Finding nearest technician..." : "Request Technician"}
        </button>

        {error && <p className="error" style={{ marginTop: 10 }}>{error}</p>}
      </div>

      {result && (
        <div className="panel" style={{ maxWidth: 420, marginTop: 16 }}>
          <div className="panel-header">
            <h3>Dispatch Matched</h3>
            <span className="badge badge-warning">{result.dispatch.dispatch_status}</span>
          </div>
          <dl className="kv-list">
            <div className="kv-row">
              <dt>Dispatch ID</dt>
              <dd style={{ fontFamily: "var(--mono)", fontSize: 12 }}>{result.dispatch.id}</dd>
            </div>
            <div className="kv-row">
              <dt>Start OTP</dt>
              <dd>{result.start_otp}</dd>
            </div>
            <div className="kv-row">
              <dt>End OTP</dt>
              <dd>{result.end_otp}</dd>
            </div>
          </dl>
          <p className="hint" style={{ marginTop: 10 }}>
            Share the start OTP with the technician on arrival, and the end OTP once the job
            is complete.
          </p>
        </div>
      )}
    </div>
  );
}
