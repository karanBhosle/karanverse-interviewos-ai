import { loadWhisper } from "@/features/speech/live-mic";
import { isIsolatedSpeech, openIsolatedMic, voiceBandScore } from "@/features/speech/voice-isolation";

const JUNK = [
  /^[\s.,!?]*$/,
  /thank you for watching/i,
  /thanks for watching/i,
  /please subscribe/i,
  /like and subscribe/i,
  /see you next time/i,
  /\[music\]/i,
  /the following is/i,
  /transcri(be|ption) the audio/i,
  /^(you|the|a|um|uh|thanks|thank you|thank you\.|you\.)\.?$/i,
];

function normalize(text: string) {
  return text.toLowerCase().replace(/[^\w\s]/g, " ").replace(/\s+/g, " ").trim();
}

export function isHallucination(text: string) {
  const cleaned = text.replace(/\s+/g, " ").trim();
  if (!cleaned) return true;
  if (JUNK.some((pattern) => pattern.test(cleaned))) return true;
  const words = cleaned.toLowerCase().split(/\s+/);
  if (words.length >= 8) {
    const unique = new Set(words);
    if (unique.size / words.length < 0.4) return true;
  }
  return false;
}


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

function mergePcm(chunks: Float32Array[]) {
  const total = chunks.reduce((sum, chunk) => sum + chunk.length, 0);
  const merged = new Float32Array(total);
  let offset = 0;
  for (const chunk of chunks) {
    merged.set(chunk, offset);
    offset += chunk.length;
  }
  return merged;
}

function pcmRms(buffer: Float32Array) {
  let total = 0;
  for (let index = 0; index < buffer.length; index += 1) total += buffer[index] * buffer[index];
  return Math.sqrt(total / buffer.length);
}

export async function transcribePcm(pcm: Float32Array) {
  if (pcm.length < 16_000 * 0.65 || pcmRms(pcm) < 0.012) return "";
  const transcriber = await loadWhisper();
  const result = await transcriber(pcm, {
    sampling_rate: 16_000,
    language: "english",
    task: "transcribe",
    temperature: 0,
    condition_on_previous_text: false,
  });
  const text = cleanHeard(typeof result === "string" ? result : result.text || "");
  return isHallucination(text) ? "" : text;
}

export async function transcribeLocal(blob: Blob) {
  const context = new AudioContext();
  try {
    const audio = await context.decodeAudioData(await blob.arrayBuffer());
    return transcribePcm(downsample(audio.getChannelData(0), audio.sampleRate, 16_000));
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
  const heard = normalize(text);
  const source = normalize(spoken);
  if (!heard || !source) return false;
  const heardWords = heard.split(" ").filter((word) => word.length > 2);
  if (heardWords.length < 8) return false;
  if (source.includes(heard) && heardWords.length >= 10) return true;
  const unique = new Set(heardWords);
  let overlap = 0;
  for (const word of unique) {
    if (source.includes(word)) overlap += 1;
  }
  return unique.size >= 8 && overlap / unique.size >= 0.92;
}

export { isFinishedUtterance } from "./browser-stt";

export function cleanHeard(text: string) {
  const cleaned = text.replace(/\s+/g, " ").trim();
  if (cleaned.length < 1) return "";
  if (JUNK.some((pattern) => pattern.test(cleaned))) return "";
  return cleaned;
}

export function mergeUtterance(prev: string, next: string) {
  const left = prev.replace(/\s+/g, " ").trim();
  const right = next.replace(/\s+/g, " ").trim();
  if (!right) return left;
  if (!left) return right;
  if (isHallucination(right)) return left;
  const leftNorm = normalize(left);
  const rightNorm = normalize(right);
  if (leftNorm === rightNorm) return left;
  if (leftNorm.includes(rightNorm)) return left;
  if (rightNorm.includes(leftNorm)) {
    const extraWords = right.split(" ").length - left.split(" ").length;
    return extraWords > 0 && extraWords <= 6 ? right : left;
  }
  const wordsA = left.split(" ");
  const wordsB = right.split(" ");
  let overlap = 0;
  for (let count = Math.min(6, wordsA.length, wordsB.length); count > 1; count -= 1) {
    if (normalize(wordsA.slice(-count).join(" ")) === normalize(wordsB.slice(0, count).join(" "))) {
      overlap = count;
      break;
    }
  }
  if (overlap >= 2) return [...wordsA, ...wordsB.slice(overlap)].join(" ");
  return `${left} ${right}`;
}

export async function transcribeClip(blob: Blob) {
  return transcribeLocal(blob);
}

export function createAnswerMic(onLevel: (rms: number, speech: boolean) => void) {
  let stream: MediaStream | null = null;
  let context: AudioContext | null = null;
  let analyser: AnalyserNode | null = null;
  let processor: ScriptProcessorNode | null = null;
  let gated = false;
  let capturing = false;
  let lastSpeech = 0;
  let startedAt = 0;
  const chunks: Float32Array[] = [];

  const resetBuffer = () => {
    chunks.length = 0;
    capturing = false;
    lastSpeech = 0;
    startedAt = 0;
  };

  return {
    get open() {
      return Boolean(stream);
    },
    setGate(value: boolean) {
      gated = value;
      if (value) resetBuffer();
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
      processor = context.createScriptProcessor(4096, 1, 1);
      const mute = context.createGain();
      mute.gain.value = 0;
      processor.onaudioprocess = (event) => {
        const input = event.inputBuffer.getChannelData(0);
        let total = 0;
        for (let index = 0; index < input.length; index += 1) total += input[index] * input[index];
        const rms = Math.sqrt(total / input.length);
        const voice = analyser ? voiceBandScore(analyser) : 0;
        const speech = !gated && isIsolatedSpeech(rms, voice);
        onLevel(speech ? rms : 0, speech);
        if (!speech || !context) return;
        if (!capturing) {
          capturing = true;
          startedAt = Date.now();
        }
        chunks.push(new Float32Array(input));
        lastSpeech = Date.now();
      };
      source.connect(analyser);
      source.connect(processor);
      processor.connect(mute);
      mute.connect(context.destination);
    },
    takeUtterance() {
      if (!context || !capturing || !chunks.length || !lastSpeech) return null;
      const quietFor = Date.now() - lastSpeech;
      const spokenFor = Date.now() - startedAt;
      if (quietFor < 750 && spokenFor < 8000) return null;
      const pcm = downsample(mergePcm(chunks), context.sampleRate, 16_000);
      resetBuffer();
      if (pcm.length < 16_000 * 0.65) return null;
      return pcm;
    },
    async stop() {
      processor?.disconnect();
      await context?.close();
      stream?.getTracks().forEach((track) => track.stop());
      analyser = null;
      processor = null;
      context = null;
      stream = null;
      gated = false;
      resetBuffer();
    },
  };
}
