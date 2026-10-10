/** Same listen engine as ELSAA on the portfolio: browser SpeechRecognition, no held mic stream. */

export type SpeechRec = {
  lang: string;
  interimResults: boolean;
  continuous: boolean;
  maxAlternatives?: number;
  start: () => void;
  stop: () => void;
  abort?: () => void;
  onstart: (() => void) | null;
  onresult: ((event: SpeechEvent) => void) | null;
  onend: (() => void) | null;
  onerror: ((event: { error?: string }) => void) | null;
};

export type SpeechEvent = {
  resultIndex: number;
  results: {
    length: number;
    [index: number]: { isFinal: boolean; [index: number]: { transcript: string } };
  };
};

export function speechEngine(): (new () => SpeechRec) | null {
  if (typeof window === "undefined") return null;
  const win = window as unknown as {
    webkitSpeechRecognition?: new () => SpeechRec;
    SpeechRecognition?: new () => SpeechRec;
  };
  return win.SpeechRecognition || win.webkitSpeechRecognition || null;
}

export function speechSupported() {
  return Boolean(speechEngine());
}

/** Ask for the mic, then release it so SpeechRecognition can own the device. */
export async function requestMicPermission() {
  if (!navigator.mediaDevices?.getUserMedia) {
    throw new Error("This browser cannot open the microphone.");
  }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
      video: false,
    });
    stream.getTracks().forEach((track) => track.stop());
  } catch (error) {
    const name = error instanceof DOMException ? error.name : "";
    if (name === "NotAllowedError" || name === "PermissionDeniedError") {
      throw new Error("Allow the microphone in this browser, then click Yes, start the interview.");
    }
    throw error;
  }
}

export function readSpeechResult(event: SpeechEvent) {
  let finals = "";
  let interim = "";
  const start = typeof event.resultIndex === "number" ? event.resultIndex : 0;
  for (let index = start; index < event.results.length; index += 1) {
    const piece = event.results[index][0]?.transcript ?? "";
    if (event.results[index].isFinal) finals += piece;
    else interim += piece;
  }
  return {
    finals: finals.replace(/\s+/g, " ").trim(),
    interim: interim.replace(/\s+/g, " ").trim(),
  };
}
