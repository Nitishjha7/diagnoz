import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import AudioTriageWidget from "../components/AudioTriageWidget";
import AnnotationCanvas from "../components/AnnotationCanvas";

const URGENCY_BADGE = {
  HIGH: "badge-warning",
  MEDIUM: "badge-neutral",
  LOW: "badge-success",
};

export default function CustomerRoom() {
  const [session, setSession] = useState(null);
  const [error, setError] = useState("");
  const [diagnosis, setDiagnosis] = useState(null);
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    api.createSession().then(setSession).catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    if (!session) return undefined;
    const timer = setInterval(() => setElapsed((s) => s + 1), 1000);
    return () => clearInterval(timer);
  }, [session]);

  if (error) return <p className="error">{error}</p>;
  if (!session) return <p className="hint">Starting session...</p>;

  const mm = String(Math.floor(elapsed / 60)).padStart(2, "0");
  const ss = String(elapsed % 60).padStart(2, "0");

  return (
    <div className="room">
      <div className="session-topline">
        <Link to="/" className="back-link">
          &larr;
        </Link>
        <h2 style={{ margin: 0 }}>Live Diagnostic Session</h2>
        <span className="badge badge-live">Live</span>
        <span className="timer">{mm}:{ss}</span>
      </div>

      <div className="session-grid">
        <div>
          <div className="video-stage">
            <div className="video-peer-chip">
              <span className="avatar">RE</span>
              Remote Engineer
            </div>
            <AnnotationCanvas sessionId={session.id} />
            <div className="video-controls">
              <button title="Mute">&#127908;</button>
              <button title="Camera">&#128247;</button>
              <button className="end-call" title="End session">
                &#9742;
              </button>
            </div>
          </div>
          <p className="hint" style={{ marginTop: 10 }}>
            Click on the video canvas to drop an annotation marker — coordinates are
            normalized so it lands correctly on the technician's screen too.
          </p>
          <p className="session-id">Session: {session.id}</p>
        </div>

        <div className="panel">
          <AudioTriageWidget sessionId={session.id} onDiagnosis={setDiagnosis} />
        </div>
      </div>

      <div className="summary-grid">
        <div className="panel">
          <div className="panel-header">
            <h3>Triage Summary</h3>
            {diagnosis && <span className="badge badge-success">Detected</span>}
          </div>
          {diagnosis ? (
            <dl className="kv-list">
              <div className="kv-row">
                <dt>Appliance Type</dt>
                <dd>{diagnosis.appliance_type}</dd>
              </div>
              <div className="kv-row">
                <dt>Suspected Issue</dt>
                <dd>{diagnosis.suspected_issue}</dd>
              </div>
              <div className="kv-row">
                <dt>Urgency</dt>
                <dd>
                  <span className={`badge ${URGENCY_BADGE[diagnosis.urgency] || "badge-neutral"}`}>
                    {diagnosis.urgency}
                  </span>
                </dd>
              </div>
            </dl>
          ) : (
            <p className="hint">Talk to the AI assistant to see the triage summary here.</p>
          )}
        </div>

        <div className="panel">
          <h3>If Remote Fix Isn't Possible</h3>
          <p className="hint">
            We'll dispatch the nearest available technician with the right spare part.
          </p>
          <Link to="/dispatch">
            <button style={{ width: "100%", marginTop: 10 }}>Dispatch Technician</button>
          </Link>
        </div>

        <div className="panel">
          <h3>Impact</h3>
          <div className="impact-list">
            <div className="impact-row">
              <span className="impact-row-label">Estimated Truck Rolls Avoided</span>
              <span className="impact-row-value">1</span>
            </div>
            <div className="impact-row">
              <span className="impact-row-label">Time Saved</span>
              <span className="impact-row-value">~2 hours</span>
            </div>
            <div className="impact-row">
              <span className="impact-row-label">CO&#8322; Emissions Reduced</span>
              <span className="impact-row-value">~12 kg</span>
            </div>
            <div className="impact-row highlight">
              <span className="impact-row-label">Your Repair Cost</span>
              <span className="impact-row-value">{diagnosis ? "₹0 (Remote Fix)" : "TBD"}</span>
            </div>
          </div>
          <div className="impact-footer">Small fixes. A bigger tomorrow. {"\u{1F331}"}</div>
        </div>
      </div>
    </div>
  );
}
