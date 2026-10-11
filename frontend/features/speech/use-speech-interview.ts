"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import {
  growHeard,
  isEmbeddedBrowser,
  isFinishedUtterance,
  readElsaaResult,
  requestMicPermission,
  speechEngine,
  speechSupported,
  type SpeechRec,
} from "@/features/speech/browser-stt";
import {
  muteSystemVoices,
  playInterviewerVoice,
  stopInterviewerVoice,
  subscribeInterviewerVoice,
} from "@/features/speech/interviewer-voice";

export function useSpeechInterview() {
  const recRef = useRef<SpeechRec | null>(null);
  const listeningRef = useRef(false);
  const lastHeardRef = useRef(0);
  const frozenRef = useRef("");
  const sessionFinalRef = useRef("");
  const committedRef = useRef("");
  const liveRef = useRef("");
  const silenceFiredRef = useRef(false);
  const silenceTimerRef = useRef<number | null>(null);
  const onSilenceRef = useRef<(() => void) | null>(null);
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
  const [supported] = useState({ tts: true, stt: speechSupported() });

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
      frozenRef.current = next;
      return next;
    });
  }, []);

  const resetAnswerAudio = useCallback(() => {
    lastHeardRef.current = 0;
    frozenRef.current = "";
    sessionFinalRef.current = "";
    committedRef.current = "";
    liveRef.current = "";
    silenceFiredRef.current = false;
    setTranscriptState("");
    setInterim("");
    setSilenceLeft(null);
    setMicLevel(0);
  }, []);

  const paintHeard = useCallback((heard: string, live = "") => {
    const next = heard.trim() || committedRef.current;
    if (!next) return;
    committedRef.current = next;
    liveRef.current = live;
    frozenRef.current = next;
    setTranscriptState(next);
    setInterim("");
    lastHeardRef.current = Date.now();
    silenceFiredRef.current = false;
    setSilenceLeft(null);
    setMicLevel(0.14);
    setListenStatus("Heard you. Keep talking, or pause when you are done.");
  }, []);

  const clearSilenceWatch = useCallback(() => {
    if (silenceTimerRef.current) window.clearInterval(silenceTimerRef.current);
    silenceTimerRef.current = null;
    setSilenceLeft(null);
  }, []);

  const stopListening = useCallback(() => {
    listeningRef.current = false;
    stopWebSpeech();
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

  const finishIfComplete = useCallback(
    (text: string) => {
      if (!isFinishedUtterance(text)) return;
      window.setTimeout(() => {
        if (!listeningRef.current || silenceFiredRef.current) return;
        silenceFiredRef.current = true;
        setSilenceLeft(null);
        stopListening();
        onSilenceRef.current?.();
      }, 700);
    },
    [stopListening],
  );

  const startElsaaListen = useCallback(() => {
    const SR = speechEngine();
    if (!SR) return false;
    stopWebSpeech();
    sessionFinalRef.current = "";
    liveRef.current = "";
    const rec = new SR();
    rec.lang = "en-IN";
    rec.interimResults = true;
    rec.continuous = true;
    rec.maxAlternatives = 1;
    rec.onstart = () => {
      setRecording(true);
      setListenStatus("Listening… speak now.");
    };
    rec.onresult = (event) => {
      const result = readElsaaResult(event);
      sessionFinalRef.current = result.finals;
      liveRef.current = result.interim;
      const stable = result.finals
        ? growHeard(frozenRef.current, result.finals)
        : frozenRef.current;
      if (result.finals) frozenRef.current = stable;
      const next = growHeard(stable, result.interim);
      paintHeard(next, result.interim);
      finishIfComplete(next);
    };
    rec.onerror = (event) => {
      if (event.error === "not-allowed") {
        setError("Microphone permission is blocked. Allow the mic, then click Yes, start the interview.");
        setNeedsTap(true);
        setRecording(false);
        listeningRef.current = false;
      }
    };
    rec.onend = () => {
      if (recRef.current !== rec) return;
      recRef.current = null;
      if (!listeningRef.current || silenceFiredRef.current) return;
      const sealed = growHeard(
        frozenRef.current,
        sessionFinalRef.current || liveRef.current || committedRef.current,
      );
      if (sealed) {
        frozenRef.current = sealed;
        committedRef.current = sealed;
        setTranscriptState(sealed);
        sessionFinalRef.current = "";
        liveRef.current = "";
      }
      window.setTimeout(() => {
        if (listeningRef.current && !silenceFiredRef.current) startElsaaListen();
      }, 40);
    };
    recRef.current = rec;
    try {
      rec.start();
      return true;
    } catch {
      recRef.current = null;
      return false;
    }
  }, [finishIfComplete, paintHeard, stopWebSpeech]);

  const startSpeaking = useCallback(async () => {
    setError(null);
    stopInterviewerVoice();
    listeningRef.current = true;
    silenceFiredRef.current = false;
    watchSilence();
    setListenStatus("Listening… speak now.");
    try {
      if (isEmbeddedBrowser() || !speechEngine()) {
        throw new Error("Open this page in Google Chrome — the same browser where ELSAA transcripts work.");
      }
      setMicReady(true);
      setRecording(true);
      setNeedsTap(false);
      if (!startElsaaListen()) {
        throw new Error("Could not start Chrome speech recognition. Reload in Google Chrome and allow the microphone.");
      }
    } catch (err) {
      listeningRef.current = false;
      setRecording(false);
      setNeedsTap(true);
      setError(err instanceof Error ? err.message : "Allow the microphone, then click Yes, start the interview.");
    }
  }, [startElsaaListen, watchSilence]);

  const stopRecording = useCallback(() => {
    listeningRef.current = false;
    stopWebSpeech();
    clearSilenceWatch();
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

  const speak = useCallback(
    async (text: string) => {
      listeningRef.current = false;
      stopListening();
      setError(null);
      try {
        await playInterviewerVoice(text);
      } catch {
        setError("The interviewer voice could not be generated.");
      }
    },
    [stopListening],
  );

  const armMicrophone = useCallback(async () => {
    setError(null);
    muteSystemVoices();
    if (isEmbeddedBrowser() || !speechEngine()) {
      throw new Error("Open this page in Google Chrome — the same browser where ELSAA transcripts work.");
    }
    setListenStatus("Requesting the microphone…");
    await requestMicPermission();
    setMicReady(true);
    setListenStatus("Microphone is ready.");
  }, []);

  const beginAnswerTurn = useCallback(() => {
    resetAnswerAudio();
    void startSpeaking();
  }, [resetAnswerAudio, startSpeaking]);

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
