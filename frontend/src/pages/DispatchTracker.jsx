import { useState } from "react";
import { api } from "../lib/api";

export default function DispatchTracker() {
  const [latitude, setLatitude] = useState("28.6150");
  const [longitude, setLongitude] = useState("77.2100");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  async function requestDispatch() {
    setError("");
    setResult(null);
    try {
      const data = await api.createDispatch(parseFloat(latitude), parseFloat(longitude));
      setResult(data);
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="room">
      <h1>Dispatch Tracker</h1>
      <p className="hint">
        Requests the nearest available technician (PostGIS KNN, 5km radius) and returns
        one-time start/end OTPs for the dual-OTP verification flow.
      </p>

      <label>
        Latitude
        <input value={latitude} onChange={(e) => setLatitude(e.target.value)} />
      </label>
      <label>
        Longitude
        <input value={longitude} onChange={(e) => setLongitude(e.target.value)} />
      </label>
      <button onClick={requestDispatch}>Request Technician</button>

      {error && <p className="error">{error}</p>}

      {result && (
        <div className="diagnosis-card">
          <p>Dispatch ID: {result.dispatch.id}</p>
          <p>Status: {result.dispatch.dispatch_status}</p>
          <p>Start OTP (share with technician on arrival): {result.start_otp}</p>
          <p>End OTP (share on job completion): {result.end_otp}</p>
        </div>
      )}
    </div>
  );
}
