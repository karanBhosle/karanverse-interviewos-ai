const SPEECH_RMS = 0.05;
const JUNK = [
  /^[\s.,!?]*$/,
  /thank you for watching/i,
  /thanks for watching/i,
  /please subscribe/i,
  /like and subscribe/i,
  /see you next time/i,
  /^(you|the|a|um|uh|yeah|yes|okay|ok|bye|hello|hi|thanks|thank you)\.?$/i,
];

type Transcriber = (audio: Float32Array, options?: { sampling_rate?: number }) => Promise<{ text?: string } | string>;

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

export async function loadWhisper(): Promise<Transcriber> {
  if (!transcriberPromise) {
    transcriberPromise = import("@huggingface/transformers").then(async ({ pipeline, env }) => {
      env.allowLocalModels = false;
      const pipe = await pipeline("automatic-speech-recognition", "Xenova/whisper-tiny.en", {
        dtype: "q8",
      });
      return async (audio: Float32Array) => {
        const result = await pipe(audio, {
          sampling_rate: 16_000,
          // Avoid looping invented phrases on noise.
          return_timestamps: false,
        });
        return result as { text?: string };
      };
    });
  }
  return transcriberPromise;
}

function frameRms(input: Float32Array) {
  let total = 0;
  for (let index = 0; index < input.length; index += 1) total += input[index] * input[index];
  return Math.sqrt(total / input.length);
}

function looksLikeSpeech(input: Float32Array, rms: number) {
  if (rms < SPEECH_RMS) return false;
  let crossings = 0;
  for (let index = 1; index < input.length; index += 1) {
    if (input[index - 1] >= 0 !== input[index] >= 0) crossings += 1;
  }
  const rate = crossings / input.length;
  return rate > 0.01 && rate < 0.28;
}

export function cleanTranscript(text: string) {
  const cleaned = text.replace(/\s+/g, " ").trim();
  if (cleaned.length < 8) return "";
  if (cleaned.split(/\s+/).length < 4) return "";
  if (JUNK.some((pattern) => pattern.test(cleaned))) return "";
  return cleaned;
}

export function createMicCapture(onLevel: (rms: number, speech: boolean) => void) {
  let stream: MediaStream | null = null;
  let context: AudioContext | null = null;
  let processor: ScriptProcessorNode | null = null;
  let capturing = false;
  const chunks: Float32Array[] = [];
  let voicedSamples = 0;

  return {
    async start() {
      stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
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
        const speech = looksLikeSpeech(input, rms);
        onLevel(rms, speech);
        if (capturing && speech) {
          chunks.push(new Float32Array(input));
          voicedSamples += input.length;
        }
      };
      source.connect(processor);
      processor.connect(mute);
      mute.connect(context.destination);
    },
    beginTurn() {
      chunks.length = 0;
      voicedSamples = 0;
      capturing = true;
    },
    pauseTurn() {
      capturing = false;
    },
    snapshot(sampleRate = 16_000) {
      if (!context || !chunks.length) return null;
      const voicedSeconds = voicedSamples / context.sampleRate;
      if (voicedSeconds < 0.8) return null;
      return downsample(merge(chunks), context.sampleRate, sampleRate);
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
    },
  };
}

export async function transcribePcm(audio: Float32Array) {
  const transcriber = await loadWhisper();
  const result = await transcriber(audio);
  return cleanTranscript(typeof result === "string" ? result : result.text || "");
}
