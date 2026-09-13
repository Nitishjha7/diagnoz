import { useCallback, useRef, useState } from "react";
import { api } from "../lib/api";
import { useAudioRecorder } from "../hooks/useAudioRecorder";

export default function AudioTriageWidget({ sessionId }) {
  const wsRef = useRef(null);
  const [transcriptChunks, setTranscriptChunks] = useState([]);
  const [diagnosis, setDiagnosis] = useState(null);
  const [connected, setConnected] = useState(false);

  const handleAudioChunk = useCallback((pcmBuffer) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(pcmBuffer);
    }
  }, []);

  const { recording, start, stop } = useAudioRecorder(handleAudioChunk);

  function connect() {
    const ws = new WebSocket(`${api.wsBase}/ws/audio/triage/${sessionId}`);
    ws.binaryType = "arraybuffer";
    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onmessage = (event) => {
      if (typeof event.data === "string") {
        const msg = JSON.parse(event.data);
        if (msg.type === "TRANSCRIPT_CHUNK") {
          setTranscriptChunks((prev) => [...prev, msg.text]);
        } else if (msg.type === "DIAGNOSIS_COMPLETE") {
          setDiagnosis(msg.payload);
        }
      }
      // binary messages here would be synthesized TTS audio - play via AudioContext in a
      // fuller build; out of scope for this demo widget.
    };
    wsRef.current = ws;
  }

  function finishSpeaking() {
    stop();
    wsRef.current?.send("done speaking");
  }

  return (
    <div className="widget">
      <h2>Voice Triage</h2>
      {!connected && <button onClick={connect}>Connect</button>}
      {connected && !recording && !diagnosis && <button onClick={start}>Start Talking</button>}
      {recording && <button onClick={finishSpeaking}>Finish Speaking</button>}

      <div className="transcript">
        {transcriptChunks.map((chunk, i) => (
          <p key={i}>{chunk}</p>
        ))}
      </div>

      {diagnosis && (
        <div className="diagnosis-card">
          <h3>Diagnosis</h3>
          <p>Appliance: {diagnosis.appliance_type}</p>
          <p>Issue: {diagnosis.suspected_issue}</p>
          <p>Urgency: {diagnosis.urgency}</p>
          <p>{diagnosis.voice_summary}</p>
        </div>
      )}
    </div>
  );
}
