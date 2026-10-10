"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export type VisualFeature = {
  feature_type: string;
  value: number | null;
  usable_frames: number;
  processing_status: string;
  algorithm_version: string;
  notes?: string;
};

export function useWebcam(enabled: boolean) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [permission, setPermission] = useState<"idle" | "granted" | "denied" | "stopped">("idle");
  const [error, setError] = useState<string | null>(null);
  const [active, setActive] = useState(false);

  const stop = useCallback(() => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    setActive(false);
    setPermission("stopped");
  }, []);

  const start = useCallback(async () => {
    if (!enabled) return;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
      streamRef.current = stream;
      if (videoRef.current) videoRef.current.srcObject = stream;
      setPermission("granted");
      setActive(true);
      setError(null);
    } catch {
      setPermission("denied");
      setError("Camera permission was denied. The interview continues in text-only mode.");
    }
  }, [enabled]);

  useEffect(() => {
    return () => stop();
  }, [stop]);

  const sampleLocalFeatures = useCallback((): VisualFeature[] => {
    const video = videoRef.current;
    if (!video || !active || video.readyState < 2) {
      return [
        {
          feature_type: "face_visibility",
          value: null,
          usable_frames: 0,
          processing_status: "insufficient_data",
          algorithm_version: "browser-preview-v1",
          notes: "No local frames were sampled. This is not a poor score.",
        },
      ];
    }
    const canvas = document.createElement("canvas");
    canvas.width = 160;
    canvas.height = 120;
    const ctx = canvas.getContext("2d");
    if (!ctx) return [];
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    const pixels = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
    let brightness = 0;
    for (let i = 0; i < pixels.length; i += 4) brightness += (pixels[i] + pixels[i + 1] + pixels[i + 2]) / 3;
    brightness /= pixels.length / 4;
    return [
      {
        feature_type: "mean_brightness",
        value: Number(brightness.toFixed(2)),
        usable_frames: 1,
        processing_status: brightness < 40 ? "quality" : "ok",
        algorithm_version: "browser-preview-v1",
        notes:
          brightness < 40
            ? "The local preview looks dark. This is a recording-quality observation, not a behavior label."
            : "Local preview brightness was sampled. Frames were not uploaded.",
      },
    ];
  }, [active]);

  return { videoRef, permission, error, active, start, stop, sampleLocalFeatures };
}
