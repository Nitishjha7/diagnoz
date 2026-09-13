import { useEffect, useRef, useState } from "react";

/** Opens a WebSocket to `url` and keeps a ref that stays stable across re-renders. */
export function useWebSocket(url, { onMessage, onOpen, onClose, binaryType } = {}) {
  const wsRef = useRef(null);
  const [status, setStatus] = useState("connecting");

  useEffect(() => {
    if (!url) return undefined;

    const ws = new WebSocket(url);
    if (binaryType) ws.binaryType = binaryType;
    wsRef.current = ws;

    ws.onopen = (event) => {
      setStatus("open");
      onOpen?.(event);
    };
    ws.onmessage = (event) => {
      onMessage?.(event);
    };
    ws.onclose = (event) => {
      setStatus("closed");
      onClose?.(event);
    };
    ws.onerror = () => setStatus("error");

    return () => {
      ws.close();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [url]);

  return { wsRef, status };
}
