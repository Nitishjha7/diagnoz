import { useEffect, useState } from "react";
import { api } from "../lib/api";
import AudioTriageWidget from "../components/AudioTriageWidget";
import AnnotationCanvas from "../components/AnnotationCanvas";

export default function CustomerRoom() {
  const [session, setSession] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.createSession().then(setSession).catch((err) => setError(err.message));
  }, []);

  if (error) return <p className="error">{error}</p>;
  if (!session) return <p>Starting session...</p>;

  return (
    <div className="room">
      <h1>Customer Room</h1>
      <p className="session-id">Session: {session.id}</p>
      <div className="room-grid">
        <AudioTriageWidget sessionId={session.id} />
        <div>
          <h2>Live Annotation</h2>
          <p className="hint">Click on the canvas to drop a marker for the technician.</p>
          <AnnotationCanvas sessionId={session.id} />
        </div>
      </div>
    </div>
  );
}
