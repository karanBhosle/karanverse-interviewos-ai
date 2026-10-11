import { loadWhisper } from "@/features/speech/live-mic";
import { isIsolatedSpeech, openIsolatedMic, voiceBandScore } from "@/features/speech/voice-isolation";

const JUNK = [
  /^[\s.,!?]*$/,
  /thank you for watching/i,
  /thanks for watching/i,
  /please subscribe/i,
  /like and subscribe/i,
  /^(you|the|a|um|uh|thanks|thank you|thank you\.|you\.)\.?$/i,
];


function downsample(buffer: Float32Array, fromRate: number, toRate: number) {
  if (fromRate === toRate) return buffer;
  const ratio = fromRate / toRate;
  const length = Math.max(1, Math.round(buffer.length / ratio));
  const output = new Float32Array(length);
  for (let index = 0; index < length; index += 1) {
    output[index] = buffer[Math.min(buffer.length - 1, Math.round(index * ratio))];
  }
  return output;
}

export async function transcribeLocal(blob: Blob) {
  const context = new AudioContext();
  try {
    const audio = await context.decodeAudioData(await blob.arrayBuffer());
    const pcm = downsample(audio.getChannelData(0), audio.sampleRate, 16_000);
    const transcriber = await loadWhisper();
    const result = await transcriber(pcm);
    return cleanHeard(typeof result === "string" ? result : result.text || "");
  } finally {
    await context.close();
  }
}

export function preferredMime() {
  if (typeof MediaRecorder === "undefined") return "";
  for (const type of ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg"]) {
    if (MediaRecorder.isTypeSupported(type)) return type;
  }
  return "";
}

export function extensionFor(mime: string) {
  if (mime.includes("mp4") || mime.includes("m4a")) return "m4a";
  if (mime.includes("ogg")) return "ogg";
  if (mime.includes("wav")) return "wav";
  return "webm";
}

export function isEcho(text: string, spoken: string) {
  const heard = text.toLowerCase().replace(/[^\w\s]/g, " ").replace(/\s+/g, " ").trim();
  const source = spoken.toLowerCase().replace(/[^\w\s]/g, " ").replace(/\s+/g, " ").trim();
  if (!heard || !source) return false;
  if (source.includes(heard) && heard.split(" ").length <= 12) return true;
  return false;
}

export function isFinishedUtterance(text: string) {
  const value = text.toLowerCase().replace(/[’']/g, "'").replace(/\s+/g, " ").trim();
  return /\b(i don't know|i do not know|no idea|not sure|no clue|skip( this)?|pass|next question|that's all|i'm done|i am done)\b/.test(
    value,
  );
}

export function cleanHeard(text: string) {
  const cleaned = text.replace(/\s+/g, " ").trim();
  if (cleaned.length < 2) return "";
  if (JUNK.some((pattern) => pattern.test(cleaned))) return "";
  return cleaned;
}

export function mergeUtterance(prev: string, next: string) {
  const left = prev.replace(/\s+/g, " ").trim();
  const right = next.replace(/\s+/g, " ").trim();
  if (!right) return left;
  if (!left) return right;
  if (left.includes(right)) return left;
  if (right.includes(left)) return right;
  const wordsA = left.split(" ");
  const wordsB = right.split(" ");
  let overlap = 0;
  for (let count = Math.min(8, wordsA.length, wordsB.length); count > 0; count -= 1) {
    if (wordsA.slice(-count).join(" ") === wordsB.slice(0, count).join(" ")) {
      overlap = count;
      break;
    }
  }
  return [...wordsA, ...wordsB.slice(overlap)].join(" ");
}

export async function transcribeClip(blob: Blob) {
  return transcribeLocal(blob);
}

export function createAnswerMic(onLevel: (rms: number, speech: boolean) => void) {
  let stream: MediaStream | null = null;
  let context: AudioContext | null = null;
  let analyser: AnalyserNode | null = null;
  let raf = 0;
  let clipPeak = 0;
  let clipVoice = 0;
  let gated = false;

  const tick = () => {
    if (!analyser) return;
    const data = new Uint8Array(analyser.fftSize);
    analyser.getByteTimeDomainData(data);
    let total = 0;
    for (const sample of data) {
      const value = (sample - 128) / 128;
      total += value * value;
    }
    const rms = Math.sqrt(total / data.length);
    const voice = voiceBandScore(analyser);
    const speech = !gated && isIsolatedSpeech(rms, voice);
    if (speech) {
      if (rms > clipPeak) clipPeak = rms;
      if (voice > clipVoice) clipVoice = voice;
    }
    onLevel(speech ? rms : 0, speech);
    raf = window.requestAnimationFrame(tick);
  };

  return {
    get open() {
      return Boolean(stream);
    },
    setGate(value: boolean) {
      gated = value;
    },
    async start() {
      if (stream) {
        if (context?.state === "suspended") await context.resume();
        return;
      }
      stream = await openIsolatedMic();
      context = new AudioContext();
      if (context.state === "suspended") await context.resume();
      const source = context.createMediaStreamSource(stream);
      analyser = context.createAnalyser();
      analyser.fftSize = 2048;
      analyser.smoothingTimeConstant = 0.35;
      source.connect(analyser);
      tick();
    },
    recordClip(ms: number) {
      return new Promise<{ blob: Blob; peak: number; voice: number }>((resolve, reject) => {
        if (!stream) {
          reject(new Error("Microphone is not open"));
          return;
        }
        clipPeak = 0;
        clipVoice = 0;
        const mime = preferredMime();
        const recorder = mime ? new MediaRecorder(stream, { mimeType: mime }) : new MediaRecorder(stream);
        const chunks: BlobPart[] = [];
        recorder.ondataavailable = (event) => {
          if (event.data.size) chunks.push(event.data);
        };
        recorder.onerror = () => reject(new Error("Recording failed"));
        recorder.onstop = () => {
          resolve({
            blob: new Blob(chunks, { type: recorder.mimeType || "audio/webm" }),
            peak: clipPeak,
            voice: clipVoice,
          });
        };
        recorder.start();
        window.setTimeout(() => {
          if (recorder.state !== "inactive") recorder.stop();
        }, ms);
      });
    },
    async stop() {
      window.cancelAnimationFrame(raf);
      raf = 0;
      await context?.close();
      stream?.getTracks().forEach((track) => track.stop());
      analyser = null;
      context = null;
      stream = null;
      clipPeak = 0;
      clipVoice = 0;
      gated = false;
    },
  };
}
