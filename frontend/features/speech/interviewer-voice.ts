import { api } from "@/lib/api/client";

type VoiceListener = (state: { speaking: boolean; loading: boolean }) => void;

const listeners = new Set<VoiceListener>();

const player = {
  gen: 0,
  busy: false,
  abort: null as AbortController | null,
  audio: null as HTMLAudioElement | null,
  url: null as string | null,
  speaking: false,
  loading: false,
};

function emit() {
  const snapshot = { speaking: player.speaking, loading: player.loading };
  listeners.forEach((listener) => listener(snapshot));
}

function ensureAudio() {
  if (!player.audio) player.audio = new Audio();
  return player.audio;
}

let originalSpeak: ((utterance: SpeechSynthesisUtterance) => void) | null = null;

export function muteSystemVoices() {
  if (typeof window === "undefined" || !window.speechSynthesis) return;
  window.speechSynthesis.cancel();
  if (originalSpeak) return;
  originalSpeak = window.speechSynthesis.speak.bind(window.speechSynthesis);
  window.speechSynthesis.speak = () => {
    window.speechSynthesis.cancel();
  };
}

export function unmuteSystemVoices() {
  if (typeof window === "undefined" || !window.speechSynthesis) return;
  window.speechSynthesis.cancel();
  if (originalSpeak) {
    window.speechSynthesis.speak = originalSpeak;
    originalSpeak = null;
  }
}

export function subscribeInterviewerVoice(listener: VoiceListener) {
  listeners.add(listener);
  listener({ speaking: player.speaking, loading: player.loading });
  return () => {
    listeners.delete(listener);
  };
}

export function stopInterviewerVoice() {
  player.gen += 1;
  player.busy = false;
  player.abort?.abort();
  player.abort = null;
  if (typeof window !== "undefined") window.speechSynthesis?.cancel();
  const audio = player.audio;
  if (audio) {
    audio.onended = null;
    audio.onerror = null;
    audio.pause();
    audio.currentTime = 0;
    audio.removeAttribute("src");
    audio.src = "";
    try {
      audio.load();
    } catch {
      /* ignore */
    }
  }
  if (player.url) {
    URL.revokeObjectURL(player.url);
    player.url = null;
  }
  player.speaking = false;
  player.loading = false;
  emit();
}

export async function playInterviewerVoice(text: string) {
  const cleaned = text.trim();
  if (!cleaned) return;
  if (player.busy) return;
  player.busy = true;
  const gen = ++player.gen;
  player.abort?.abort();
  player.abort = null;
  if (typeof window !== "undefined") window.speechSynthesis?.cancel();
  const existing = player.audio;
  if (existing) {
    existing.onended = null;
    existing.onerror = null;
    existing.pause();
    existing.currentTime = 0;
  }
  if (player.url) {
    URL.revokeObjectURL(player.url);
    player.url = null;
  }
  player.loading = true;
  player.speaking = true;
  emit();
  const controller = new AbortController();
  player.abort = controller;
  try {
    const blob = await api.postBlob("/api/v1/tts", { text: cleaned }, controller.signal);
    if (gen !== player.gen) return;
    const url = URL.createObjectURL(blob);
    player.url = url;
    const audio = ensureAudio();
    audio.src = url;
    player.loading = false;
    emit();
    await new Promise<void>((resolve, reject) => {
      audio.onended = () => {
        if (gen === player.gen) {
          player.busy = false;
          player.speaking = false;
          player.loading = false;
          if (player.url) {
            URL.revokeObjectURL(player.url);
            player.url = null;
          }
          emit();
        }
        resolve();
      };
      audio.onerror = () => {
        if (gen === player.gen) {
          player.busy = false;
          player.speaking = false;
          player.loading = false;
          emit();
        }
        resolve();
      };
      audio.play().catch(reject);
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") return;
    if (gen !== player.gen) return;
    player.busy = false;
    player.speaking = false;
    player.loading = false;
    emit();
    throw error;
  }
}
