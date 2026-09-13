import { useCallback, useRef, useState } from "react";

const TARGET_SAMPLE_RATE = 16000;

function floatTo16BitPCM(float32Array) {
  const buffer = new ArrayBuffer(float32Array.length * 2);
  const view = new DataView(buffer);
  for (let i = 0; i < float32Array.length; i++) {
    const s = Math.max(-1, Math.min(1, float32Array[i]));
    view.setInt16(i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }
  return buffer;
}

/** Captures mic audio, downsamples to 16kHz mono PCM16, and hands raw ArrayBuffers to
 * onAudioChunk - matching the /ws/audio/triage binary contract (no base64). */
export function useAudioRecorder(onAudioChunk) {
  const [recording, setRecording] = useState(false);
  const audioContextRef = useRef(null);
  const streamRef = useRef(null);
  const processorRef = useRef(null);

  const start = useCallback(async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    streamRef.current = stream;

    const audioContext = new AudioContext();
    audioContextRef.current = audioContext;
    const source = audioContext.createMediaStreamSource(stream);

    const processor = audioContext.createScriptProcessor(4096, 1, 1);
    processorRef.current = processor;

    processor.onaudioprocess = (event) => {
      const input = event.inputBuffer.getChannelData(0);
      const ratio = audioContext.sampleRate / TARGET_SAMPLE_RATE;
      const downsampled = new Float32Array(Math.floor(input.length / ratio));
      for (let i = 0; i < downsampled.length; i++) {
        downsampled[i] = input[Math.floor(i * ratio)];
      }
      onAudioChunk?.(floatTo16BitPCM(downsampled));
    };

    source.connect(processor);
    processor.connect(audioContext.destination);
    setRecording(true);
  }, [onAudioChunk]);

  const stop = useCallback(() => {
    processorRef.current?.disconnect();
    streamRef.current?.getTracks().forEach((track) => track.stop());
    audioContextRef.current?.close();
    setRecording(false);
  }, []);

  return { recording, start, stop };
}
