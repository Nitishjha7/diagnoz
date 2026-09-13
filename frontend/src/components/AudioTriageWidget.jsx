import { useCallback, useRef, useState } from "react";
import { api } from "../lib/api";
import { useAudioRecorder } from "../hooks/useAudioRecorder";

export default function AudioTriageWidget({ sessionId, onDiagnosis }) {
  const wsRef = useRef(null);
  const [messages, setMessages] = useState([
    { from: "assistant", text: "Hi! Describe the issue with your appliance and I'll help diagnose it." },
  ]);
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
          setMessages((prev) => [...prev, { from: "user", text: msg.text }]);
        } else if (msg.type === "DIAGNOSIS_COMPLETE") {
          setDiagnosis(msg.payload);
          onDiagnosis?.(msg.payload);
          setMessages((prev) => [...prev, { from: "assistant", text: msg.payload.voice_summary }]);
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
    <div className="assistant-panel">
      <div className="assistant-tabs">
        <button className="assistant-tab active">AI Assistant</button>
        <button className="assistant-tab">Session Details</button>
      </div>

      <div className="chat-log">
        {messages.map((msg, i) => (
          <div key={i} className={`chat-bubble ${msg.from}`}>
            {msg.text}
          </div>
        ))}
      </div>

      <div className="mic-cta">
        {!connected && <button onClick={connect}>Connect</button>}
        {connected && !recording && !diagnosis && (
          <>
            <button className="mic-button" onClick={start} title="Tap to speak">
              &#127908;
            </button>
            <span className="mic-status">Tap to speak</span>
          </>
        )}
        {recording && (
          <>
            <button className="mic-button recording" onClick={finishSpeaking} title="Finish speaking">
              &#9632;
            </button>
            <span className="mic-status">Listening... tap to finish</span>
          </>
        )}
        {diagnosis && <span className="mic-status">Diagnosis complete</span>}
      </div>
    </div>
  );
}
