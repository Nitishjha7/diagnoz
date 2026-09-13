import { useEffect, useRef } from "react";
import { api } from "../lib/api";

/** Live annotation overlay - normalizes click coords to [0,1] before sending, and
 * re-draws whatever normalized coords arrive from the /ws/canvas/sync Redis relay so
 * the same drawing lands correctly regardless of each peer's canvas resolution. */
export default function AnnotationCanvas({ sessionId }) {
  const canvasRef = useRef(null);
  const wsRef = useRef(null);

  useEffect(() => {
    const ws = new WebSocket(`${api.wsBase}/ws/canvas/sync/${sessionId}`);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      const { norm_x, norm_y, color } = JSON.parse(event.data);
      drawDot(norm_x, norm_y, color);
    };

    return () => ws.close();
  }, [sessionId]);

  function drawDot(normX, normY, color) {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    ctx.fillStyle = color || "#ff3b30";
    ctx.beginPath();
    ctx.arc(normX * canvas.width, normY * canvas.height, 8, 0, Math.PI * 2);
    ctx.fill();
  }

  function handleClick(event) {
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const normX = (event.clientX - rect.left) / rect.width;
    const normY = (event.clientY - rect.top) / rect.height;
    const color = "#ff3b30";

    drawDot(normX, normY, color);
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ action: "DRAW", norm_x: normX, norm_y: normY, color }));
    }
  }

  return (
    <canvas
      ref={canvasRef}
      width={640}
      height={360}
      className="annotation-canvas"
      onClick={handleClick}
    />
  );
}
