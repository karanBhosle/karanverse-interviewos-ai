"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import {
  requestMicPermission,
  speechEngine,
  speechSupported,
  type SpeechEvent,
  type SpeechRec,
} from "@/features/speech/browser-stt";
import {
  muteSystemVoices,
  playInterviewerVoice,
  stopInterviewerVoice,
  subscribeInterviewerVoice,
} from "@/features/speech/interviewer-voice";
import { createLiveMic, isInterviewerEcho, loadWhisper, transcribePcm } from "@/features/speech/live-mic";

type LiveMic = ReturnType<typeof createLiveMic>;

function isElectron() {
  return typeof navigator !== "undefined" && /Electron/i.test(navigator.userAgent);
}

export function useSpeechInterview() {
  const recRef = useRef<SpeechRec | null>(null);
  const micRef = useRef<LiveMic | null>(null);
  const listeningRef = useRef(false);
  const loopRef = useRef(false);
  const busyRef = useRef(false);
  const lastHeardRef = useRef(0);
  const committedRef = useRef("");
  const liveRef = useRef("");
  const silenceFiredRef = useRef(false);
  const silenceTimerRef = useRef<number | null>(null);
  const onSilenceRef = useRef<(() => void) | null>(null);
  const fallbackRef = useRef<(reason?: string) => void>(() => undefined);
  const interviewerTextRef = useRef("");
  const [micReady, setMicReady] = useState(false);
  const [recording, setRecording] = useState(false);
  const [needsTap, setNeedsTap] = useState(true);
  const [silenceLeft, setSilenceLeft] = useState<number | null>(null);
  const [speaking, setSpeaking] = useState(false);
  const [voiceLoading, setVoiceLoading] = useState(false);
  const [transcript, setTranscriptState] = useState("");
  const [interim, setInterim] = useState("");
  const [listenStatus, setListenStatus] = useState("Microphone is off");
  const [micLevel, setMicLevel] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [voiceName] = useState("Neerja · Indian English");
  const [supported] = useState({ tts: true, stt: true });

  const stopWebSpeech = useCallback(() => {
    const rec = recRef.current;
    recRef.current = null;
    if (!rec) return;
    rec.onresult = null;
    rec.onerror = null;
    rec.onend = null;
    rec.onstart = null;
    try {
      rec.stop();
    } catch {
      /* already stopped */
    }
  }, []);

  const stopSpeaking = useCallback(() => {
    stopInterviewerVoice();
    setSpeaking(false);
    setVoiceLoading(false);
  }, []);

  const setTranscript = useCallback((value: string | ((prev: string) => string)) => {
    setTranscriptState((prev) => {
      const next = typeof value === "function" ? value(prev) : value;
      committedRef.current = next;
      return next;
    });
  }, []);

  const resetAnswerAudio = useCallback(() => {
    lastHeardRef.current = 0;
    committedRef.current = "";
    liveRef.current = "";
    silenceFiredRef.current = false;
    setTranscriptState("");
    setInterim("");
    setSilenceLeft(null);
    setMicLevel(0);
  }, []);

  const markHeard = useCallback((text: string, live = "") => {
    if (text) {
      committedRef.current = text;
      setTranscriptState(text);
    }
    liveRef.current = live;
    setInterim(live);
    lastHeardRef.current = Date.now();
    silenceFiredRef.current = false;
    setSilenceLeft(null);
    setListenStatus("Heard you. Keep talking, or pause when you are done.");
  }, []);

  const clearSilenceWatch = useCallback(() => {
    if (silenceTimerRef.current) window.clearInterval(silenceTimerRef.current);
    silenceTimerRef.current = null;
    setSilenceLeft(null);
  }, []);

  const stopListening = useCallback(() => {
    listeningRef.current = false;
    loopRef.current = false;
    stopWebSpeech();
    micRef.current?.pauseTurn();
    setRecording(false);
    setMicLevel(0);
  }, [stopWebSpeech]);

  const watchSilence = useCallback(() => {
    if (silenceTimerRef.current) return;
    silenceTimerRef.current = window.setInterval(() => {
      if (!listeningRef.current || silenceFiredRef.current) return;
      const heard = committedRef.current || liveRef.current;
      if (!heard || !lastHeardRef.current) {
        setSilenceLeft(null);
        return;
      }
      const idle = Date.now() - lastHeardRef.current;
      if (idle < 800) {
        setSilenceLeft(null);
        return;
      }
      const left = Math.ceil((5000 - idle) / 1000);
      if (left > 0) {
        setSilenceLeft(left);
        setListenStatus(`If you are finished, I will continue in ${left}s.`);
        return;
      }
      silenceFiredRef.current = true;
      setSilenceLeft(null);
      stopListening();
      onSilenceRef.current?.();
    }, 200);
  }, [stopListening]);

  const loopMic = useCallback(async () => {
    if (loopRef.current) return;
    loopRef.current = true;
    while (listeningRef.current && micRef.current) {
      await new Promise((resolve) => window.setTimeout(resolve, 1100));
      if (!listeningRef.current || busyRef.current) continue;
      const audio = micRef.current.snapshot(0.6);
      if (!audio) continue;
      busyRef.current = true;
      try {
        setListenStatus("Transcribing your voice…");
        const text = await transcribePcm(audio);
        if (!text || !listeningRef.current) continue;
        if (isInterviewerEcho(text, interviewerTextRef.current)) continue;
        markHeard(text);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Could not transcribe the microphone audio.");
      } finally {
        busyRef.current = false;
      }
    }
    loopRef.current = false;
  }, [markHeard]);

  const startMicListen = useCallback(async () => {
    stopWebSpeech();
    setListenStatus("Opening the microphone transcriber…");
    await loadWhisper();
    if (!micRef.current) {
      micRef.current = createLiveMic((rms, speech) => {
        setMicLevel(rms);
        if (listeningRef.current && speech) {
          lastHeardRef.current = lastHeardRef.current || Date.now();
          silenceFiredRef.current = false;
          setSilenceLeft(null);
        }
      });
    }
    await micRef.current.start();
    micRef.current.beginTurn();
    setMicReady(true);
    setRecording(true);
    setNeedsTap(false);
    setError(null);
    setListenStatus("Listening… speak now.");
    void loopMic();
  }, [loopMic, stopWebSpeech]);

  useEffect(() => {
    fallbackRef.current = (reason?: string) => {
      if (!listeningRef.current || micRef.current?.open) return;
      setListenStatus(reason || "Chrome speech did not hear you. Switching to the microphone transcriber…");
      void startMicListen().catch((err) => {
        setError(err instanceof Error ? err.message : "Allow the microphone, then tap Start speaking.");
        setRecording(false);
        setNeedsTap(true);
      });
    };
  }, [startMicListen]);

  const startElsaaListen = useCallback(() => {
    const SR = speechEngine();
    if (!SR) return false;
    stopWebSpeech();
    const rec = new SR();
    rec.lang = "en-IN";
    rec.interimResults = true;
    rec.continuous = false;
    rec.onstart = () => {
      setRecording(true);
      setNeedsTap(false);
      setError(null);
      setListenStatus("Listening… speak now.");
    };
    rec.onresult = (event: SpeechEvent) => {
      let finalText = "";
      let live = "";
      for (let index = 0; index < event.results.length; index += 1) {
        const piece = event.results[index][0]?.transcript ?? "";
        if (event.results[index].isFinal) finalText += piece;
        else live += piece;
      }
      const shown = (finalText || live).trim();
      if (!shown) return;
      if (finalText.trim()) {
        markHeard(`${committedRef.current} ${finalText}`.replace(/\s+/g, " ").trim(), "");
      } else {
        markHeard(committedRef.current, shown);
      }
    };
    rec.onerror = (event) => {
      if (event.error === "aborted") return;
      if (event.error === "not-allowed") {
        setError("Microphone permission is blocked. Allow the mic, then tap Start speaking.");
        setNeedsTap(true);
        setRecording(false);
        return;
      }
      fallbackRef.current("Chrome speech did not hear you. Switching to the microphone transcriber…");
    };
    rec.onend = () => {
      recRef.current = null;
      if (!listeningRef.current || silenceFiredRef.current) return;
      if (committedRef.current || liveRef.current) {
        window.setTimeout(() => {
          if (listeningRef.current && !silenceFiredRef.current && !micRef.current?.open) startElsaaListen();
        }, 80);
        return;
      }
      fallbackRef.current();
    };
    recRef.current = rec;
    try {
      rec.start();
      setRecording(true);
      setListenStatus("Listening… speak now.");
      return true;
    } catch {
      recRef.current = null;
      return false;
    }
  }, [markHeard, stopWebSpeech]);

  const startSpeaking = useCallback(async () => {
    setError(null);
    stopInterviewerVoice();
    listeningRef.current = true;
    silenceFiredRef.current = false;
    watchSilence();
    void loadWhisper();
    if (!isElectron() && speechSupported()) {
      const started = startElsaaListen();
      if (started) return;
    }
    try {
      await new Promise((resolve) => window.setTimeout(resolve, 400));
      if (!listeningRef.current) return;
      await startMicListen();
    } catch (err) {
      listeningRef.current = false;
      setRecording(false);
      setNeedsTap(true);
      setError(
        err instanceof DOMException && (err.name === "NotAllowedError" || err.name === "PermissionDeniedError")
          ? "Allow the microphone, then tap Start speaking."
          : err instanceof Error
            ? err.message
            : "Allow the microphone, then tap Start speaking.",
      );
    }
  }, [startElsaaListen, startMicListen, watchSilence]);

  const stopRecording = useCallback(() => {
    listeningRef.current = false;
    stopWebSpeech();
    clearSilenceWatch();
    void micRef.current?.stop();
    micRef.current = null;
    setMicReady(false);
    setRecording(false);
    setNeedsTap(true);
    setMicLevel(0);
    setListenStatus("Microphone is off");
  }, [clearSilenceWatch, stopWebSpeech]);

  useEffect(() => {
    muteSystemVoices();
    const unsubscribe = subscribeInterviewerVoice((state) => {
      setSpeaking(state.speaking);
      setVoiceLoading(state.loading);
    });
    return () => {
      unsubscribe();
      stopInterviewerVoice();
      stopRecording();
    };
  }, [stopRecording]);

  const speak = useCallback(async (text: string) => {
    listeningRef.current = false;
    interviewerTextRef.current = text;
    stopListening();
    setError(null);
    try {
      await playInterviewerVoice(text);
    } catch {
      setError("The interviewer voice could not be generated.");
    }
  }, [stopListening]);

  const armMicrophone = useCallback(async () => {
    setError(null);
    muteSystemVoices();
    setListenStatus("Requesting the microphone…");
    await requestMicPermission();
    void loadWhisper();
    setMicReady(true);
    setListenStatus("Microphone is ready. Tap Start speaking after the question.");
  }, []);

  const beginAnswerTurn = useCallback(() => {
    resetAnswerAudio();
    listeningRef.current = false;
    stopListening();
    setNeedsTap(true);
    setListenStatus("Tap Start speaking, then answer out loud.");
  }, [resetAnswerAudio, stopListening]);

  const pauseAnswerTurn = useCallback(() => {
    listeningRef.current = false;
    stopListening();
    clearSilenceWatch();
    setListenStatus("Waiting for the next question.");
  }, [clearSilenceWatch, stopListening]);

  return {
    supported,
    micReady,
    recording,
    needsTap,
    speaking,
    voiceLoading,
    voiceName,
    transcript,
    interim,
    playbackUrl: null as string | null,
    silenceLeft,
    listenStatus,
    micLevel,
    error,
    setOnSilence: (handler: (() => void) | null) => {
      onSilenceRef.current = handler;
    },
    speak,
    stopSpeaking,
    armMicrophone,
    beginAnswerTurn,
    startSpeaking,
    pauseAnswerTurn,
    startRecording: startSpeaking,
    stopRecording,
    resetAnswerAudio,
    setTranscript,
  };
}
