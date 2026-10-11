"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import {
  cleanHeard,
  createAnswerMic,
  isEcho,
  isFinishedUtterance,
  mergeUtterance,
  transcribeClip,
} from "@/features/speech/answer-mic";
import { isIsolatedSpeech } from "@/features/speech/voice-isolation";
import { loadWhisper } from "@/features/speech/live-mic";
import { readSpeechResult, speechEngine, type SpeechRec } from "@/features/speech/browser-stt";
import {
  interviewerIsSpeaking,
  muteSystemVoices,
  playInterviewerVoice,
  stopInterviewerVoice,
  subscribeInterviewerVoice,
} from "@/features/speech/interviewer-voice";

type AnswerMic = ReturnType<typeof createAnswerMic>;

function isElectron() {
  return typeof navigator !== "undefined" && /Electron/i.test(navigator.userAgent);
}

export function useSpeechInterview() {
  const recRef = useRef<SpeechRec | null>(null);
  const micRef = useRef<AnswerMic | null>(null);
  const listeningRef = useRef(false);
  const loopRef = useRef(false);
  const lastHeardRef = useRef(0);
  const committedRef = useRef("");
  const liveRef = useRef("");
  const silenceFiredRef = useRef(false);
  const silenceTimerRef = useRef<number | null>(null);
  const onSilenceRef = useRef<(() => void) | null>(null);
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
    if (!SR || isElectron()) return false;
    stopWebSpeech();
    const rec = new SR();
    rec.lang = "en-IN";
    rec.interimResults = true;
    rec.continuous = false;
    rec.onstart = () => {
      setRecording(true);
      setListenStatus("Listening… speak now.");
    };
    rec.onresult = (event) => {
      if (interviewerIsSpeaking()) return;
      const result = readSpeechResult(event);
      const live = result.interim;
      const finals = cleanHeard(result.finals);
      if (finals) {
        if (isEcho(finals, interviewerTextRef.current)) return;
        const next = mergeUtterance(committedRef.current, finals);
        markHeard(next, "");
        finishIfComplete(next);
        return;
      }
      if (live && !isEcho(live, interviewerTextRef.current)) markHeard(committedRef.current, live);
    };
    rec.onerror = (event) => {
      if (event.error === "not-allowed") {
        setError("Microphone permission is blocked. Allow the mic, then click Yes, start the interview.");
        setNeedsTap(true);
        setRecording(false);
      }
    };
    rec.onend = () => {
      recRef.current = null;
      if (!listeningRef.current || silenceFiredRef.current) return;
      window.setTimeout(() => {
        if (listeningRef.current && !silenceFiredRef.current) startElsaaListen();
      }, 80);
    };
    recRef.current = rec;
    try {
      rec.start();
      return true;
    } catch {
      recRef.current = null;
      return false;
    }
  }, [finishIfComplete, markHeard, stopWebSpeech]);

  const loopClips = useCallback(async () => {
    if (loopRef.current || !micRef.current) return;
    loopRef.current = true;
    let next = micRef.current.recordClip(1600);
    while (listeningRef.current && micRef.current) {
      const clip = await next;
      if (!listeningRef.current || !micRef.current) break;
      next = micRef.current.recordClip(1600);
      if (interviewerIsSpeaking()) continue;
      if (clip.blob.size < 800 || !isIsolatedSpeech(clip.peak, clip.voice)) continue;
      try {
        setListenStatus("Transcribing your voice…");
        const text = await transcribeClip(clip.blob);
        if (!listeningRef.current || !text) continue;
        if (isEcho(text, interviewerTextRef.current)) continue;
        const next = mergeUtterance(committedRef.current, text);
        markHeard(next);
        finishIfComplete(next);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Could not transcribe the microphone audio.");
        setListenStatus("Transcription failed. Keep speaking, or pause and I will continue.");
      }
    }
    loopRef.current = false;
  }, [finishIfComplete, markHeard]);

  const startSpeaking = useCallback(async () => {
    setError(null);
    stopInterviewerVoice();
    listeningRef.current = true;
    silenceFiredRef.current = false;
    watchSilence();
    setListenStatus("Opening the isolated microphone…");
    void loadWhisper();
    try {
      if (!micRef.current) {
        micRef.current = createAnswerMic((rms) => {
          setMicLevel(rms);
        });
      }
      await new Promise((resolve) => window.setTimeout(resolve, 220));
      if (!listeningRef.current) return;
      await micRef.current.start();
      micRef.current.setGate(false);
      setMicReady(true);
      setRecording(true);
      setNeedsTap(false);
      setListenStatus("Listening… speak now.");
      startElsaaListen();
      void loopClips();
    } catch (err) {
      listeningRef.current = false;
      setRecording(false);
      setNeedsTap(true);
      setError(
        err instanceof DOMException && (err.name === "NotAllowedError" || err.name === "PermissionDeniedError")
          ? "Allow the microphone, then click Yes, start the interview."
          : err instanceof Error
            ? err.message
            : "Allow the microphone, then click Yes, start the interview.",
      );
    }
  }, [loopClips, startElsaaListen, watchSilence]);

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
      micRef.current?.setGate(state.speaking || state.loading);
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
      interviewerTextRef.current = text;
      micRef.current?.setGate(true);
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
    setListenStatus("Requesting the microphone…");
    if (!micRef.current) {
        micRef.current = createAnswerMic((rms) => {
          setMicLevel(rms);
        });
      }
    await micRef.current.start();
    micRef.current.setGate(true);
    void loadWhisper();
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
