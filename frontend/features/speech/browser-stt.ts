/** ELSAA listen engine from the portfolio Assistant: Chrome SpeechRecognition only. */

export type SpeechRec = {
  lang: string;
  interimResults: boolean;
  continuous: boolean;
  maxAlternatives?: number;
  start: () => void;
  stop: () => void;
  abort?: () => void;
  onstart: (() => void) | null;
  onend: (() => void) | null;
  onresult: ((event: SpeechEvent) => void) | null;
  onerror: ((event: { error?: string }) => void) | null;
};

export type SpeechAlternative = { transcript: string; confidence?: number };

export type SpeechResult = {
  isFinal: boolean;
  length?: number;
  [index: number]: SpeechAlternative;
};

export type SpeechEvent = {
  resultIndex: number;
  results: {
    length: number;
    [index: number]: SpeechResult;
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

export function isEmbeddedBrowser() {
  if (typeof navigator === "undefined") return false;
  return /Electron|Cursor/i.test(navigator.userAgent);
}

/** Same as ELSAA armVoice: ask once, then release so SpeechRecognition owns the mic. */
export async function requestMicPermission() {
  if (!navigator.mediaDevices?.getUserMedia) {
    throw new Error("This browser cannot open the microphone.");
  }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    stream.getTracks().forEach((track) => track.stop());
  } catch (error) {
    const name = error instanceof DOMException ? error.name : "";
    if (name === "NotAllowedError" || name === "PermissionDeniedError") {
      throw new Error("Allow the microphone in this browser, then click Yes, start the interview.");
    }
    throw error;
  }
}

function pieceText(result: SpeechResult) {
  return result[0]?.transcript ?? "";
}

/** Exact ELSAA onresult loop: every result from 0, first alternative, no rewrite. */
export function readElsaaResult(event: SpeechEvent) {
  let finalText = "";
  let interim = "";
  for (let index = 0; index < event.results.length; index += 1) {
    const piece = pieceText(event.results[index]);
    if (event.results[index].isFinal) finalText += piece;
    else interim += piece;
  }
  const finals = finalText.trim();
  const live = interim.trim();
  return {
    finals,
    interim: live,
    shown: (finals || live).trim(),
    heard: [finals, live].filter(Boolean).join(" ").replace(/\s+/g, " ").trim(),
  };
}

export function readSpeechResult(event: SpeechEvent) {
  return readElsaaResult(event);
}

/** Join Chrome fragments without dropping words or repeating an overlapping tail. */
export function joinHeard(prev: string, next: string) {
  const left = prev.replace(/\s+/g, " ").trim();
  const right = next.replace(/\s+/g, " ").trim();
  if (!right) return left;
  if (!left) return right;
  const leftFold = left.toLowerCase();
  const rightFold = right.toLowerCase();
  if (leftFold === rightFold) return left;
  if (rightFold.startsWith(leftFold)) return right;
  if (leftFold.startsWith(rightFold) && right.split(" ").length < left.split(" ").length) return left;
  if (leftFold.endsWith(` ${rightFold}`) || leftFold.endsWith(rightFold)) return left;
  if (rightFold.endsWith(` ${leftFold}`)) return right;

  const leftWords = left.split(" ");
  const rightWords = right.split(" ");
  const max = Math.min(leftWords.length, rightWords.length);
  for (let count = max; count >= 1; count -= 1) {
    if (leftWords.slice(-count).join(" ").toLowerCase() === rightWords.slice(0, count).join(" ").toLowerCase()) {
      return [...leftWords, ...rightWords.slice(count)].join(" ");
    }
  }
  return `${left} ${right}`;
}

/** Frozen previous sessions plus this Chrome event, exact words only. */
export function heardFromChrome(frozen: string, event: SpeechEvent) {
  return joinHeard(frozen, readElsaaResult(event).heard);
}

export function growHeard(prev: string, next: string) {
  const joined = joinHeard(prev, next);
  return joined.length >= prev.trim().length ? joined : prev.trim();
}

export function isFinishedUtterance(text: string) {
  const value = text.toLowerCase().replace(/[’']/g, "'").replace(/\s+/g, " ").trim();
  if (!value || value.split(" ").length > 14) return false;
  return /^(um+|uh+|so|well|actually|sorry[,.]?\s+|can you |please )*(i don't know|i do not know|i have no idea|no idea|i'm not sure|i am not sure|no clue|skip( the| this| that)?( question)?|next question|that's all|that is all|i'm done|i am done)[.!?]*$/.test(
    value,
  );
}
