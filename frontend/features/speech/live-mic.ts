type Transcriber = (
  audio: Float32Array,
  options?: Record<string, unknown>,
) => Promise<{ text?: string } | string>;

let transcriberPromise: Promise<Transcriber> | null = null;

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

function merge(chunks: Float32Array[]) {
  const total = chunks.reduce((sum, chunk) => sum + chunk.length, 0);
  const merged = new Float32Array(total);
  let offset = 0;
  for (const chunk of chunks) {
    merged.set(chunk, offset);
    offset += chunk.length;
  }
  return merged;
}

function frameRms(input: Float32Array) {
  let total = 0;
  for (let index = 0; index < input.length; index += 1) total += input[index] * input[index];
  return Math.sqrt(total / input.length);
}

export async function loadWhisper(): Promise<Transcriber> {
  if (!transcriberPromise) {
    transcriberPromise = import("@huggingface/transformers").then(async ({ pipeline, env }) => {
      env.allowLocalModels = false;
      const pipe = await pipeline("automatic-speech-recognition", "Xenova/whisper-base.en", {
        dtype: "q8",
      });
      return async (audio: Float32Array, options?: Record<string, unknown>) =>
        pipe(audio, {
          sampling_rate: 16_000,
          language: "english",
          task: "transcribe",
          return_timestamps: false,
          temperature: 0,
          condition_on_previous_text: false,
          ...options,
        }) as Promise<{ text?: string }>;
    });
  }
  return transcriberPromise;
}

const JUNK = [
  /^[\s.,!?]*$/,
  /thank you for watching/i,
  /thanks for watching/i,
  /please subscribe/i,
  /^(you|the|a|um|uh|yeah|yes|okay|ok|bye|hello|hi|thanks|thank you|thank you\.|you\.)\.?$/i,
];

export function cleanTranscript(text: string) {
  const cleaned = text.replace(/\s+/g, " ").trim();
  if (cleaned.length < 8) return "";
  if (cleaned.split(/\s+/).length < 3) return "";
  if (JUNK.some((pattern) => pattern.test(cleaned))) return "";
  return cleaned;
}

export function isInterviewerEcho(text: string, interviewerText: string) {
  const heard = text.toLowerCase().replace(/[^\w\s]/g, " ").replace(/\s+/g, " ").trim();
  const spoken = interviewerText.toLowerCase().replace(/[^\w\s]/g, " ").replace(/\s+/g, " ").trim();
  if (!heard || !spoken) return false;
  if (spoken.includes(heard) && heard.split(" ").length <= 12) return true;
  const heardWords = new Set(heard.split(" ").filter((word) => word.length > 3));
  if (heardWords.size < 3) return false;
  let overlap = 0;
  for (const word of heardWords) {
    if (spoken.includes(word)) overlap += 1;
  }
  return overlap / heardWords.size >= 0.7;
}

export async function transcribePcm(audio: Float32Array) {
  const transcriber = await loadWhisper();
  const result = await transcriber(audio);
  return cleanTranscript(typeof result === "string" ? result : result.text || "");
}

export function createLiveMic(onLevel: (rms: number, speech: boolean) => void) {
  let stream: MediaStream | null = null;
  let context: AudioContext | null = null;
  let processor: ScriptProcessorNode | null = null;
  let capturing = false;
  const chunks: Float32Array[] = [];
  let samples = 0;

  return {
    get open() {
      return Boolean(stream);
    },
    async start() {
      if (stream) {
        if (context?.state === "suspended") await context.resume();
        return;
      }
      stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
        video: false,
      });
      context = new AudioContext();
      if (context.state === "suspended") await context.resume();
      const source = context.createMediaStreamSource(stream);
      processor = context.createScriptProcessor(4096, 1, 1);
      const mute = context.createGain();
      mute.gain.value = 0;
      processor.onaudioprocess = (event) => {
        const input = event.inputBuffer.getChannelData(0);
        const rms = frameRms(input);
        const speech = rms >= 0.04;
        onLevel(rms, speech);
        if (capturing && speech) {
          chunks.push(new Float32Array(input));
          samples += input.length;
        }
      };
      source.connect(processor);
      processor.connect(mute);
      mute.connect(context.destination);
    },
    beginTurn() {
      chunks.length = 0;
      samples = 0;
      capturing = true;
    },
    pauseTurn() {
      capturing = false;
    },
    snapshot(minSeconds = 0.7) {
      if (!context || !chunks.length) return null;
      if (samples / context.sampleRate < minSeconds) return null;
      const max = Math.round(context.sampleRate * 20);
      const merged = merge(chunks);
      const clipped = merged.length > max ? merged.subarray(merged.length - max) : merged;
      return downsample(clipped, context.sampleRate, 16_000);
    },
    async stop() {
      capturing = false;
      processor?.disconnect();
      await context?.close();
      stream?.getTracks().forEach((track) => track.stop());
      processor = null;
      context = null;
      stream = null;
      chunks.length = 0;
      samples = 0;
    },
  };
}
