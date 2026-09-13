import { useState } from "react";
import { api } from "../lib/api";
import AnnotationCanvas from "../components/AnnotationCanvas";

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

      <section>
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
        {profileStatus && <p>{profileStatus}</p>}
      </section>

      <section>
        <h2>Dispatch Lifecycle</h2>
        <label>
          Dispatch ID
          <input value={dispatchId} onChange={(e) => setDispatchId(e.target.value)} />
        </label>
        <button onClick={loadDispatch}>Load</button>
        {dispatch && (
          <div className="diagnosis-card">
            <p>Status: {dispatch.dispatch_status}</p>
            <p>Technician earnings: {dispatch.technician_earnings}</p>

            {dispatch.dispatch_status === "PENDING" && <button onClick={accept}>Accept</button>}

            {dispatch.dispatch_status === "ACCEPTED" && (
              <div>
                <input placeholder="Start OTP" value={startOtp} onChange={(e) => setStartOtp(e.target.value)} />
                <button onClick={verifyStart}>Verify Start OTP</button>
              </div>
            )}

            {dispatch.dispatch_status === "IN_PROGRESS" && (
              <div>
                <input placeholder="End OTP" value={endOtp} onChange={(e) => setEndOtp(e.target.value)} />
                <button onClick={verifyEnd}>Verify End OTP</button>
              </div>
            )}
          </div>
        )}
        {error && <p className="error">{error}</p>}
      </section>

      <section>
        <h2>Draw for Customer</h2>
        <label>
          Session ID
          <input value={sessionId} onChange={(e) => setSessionId(e.target.value)} />
        </label>
        {sessionId && <AnnotationCanvas sessionId={sessionId} />}
      </section>
    </div>
  );
}
