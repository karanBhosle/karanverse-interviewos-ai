type IsolatedConstraints = MediaTrackConstraints & {
  voiceIsolation?: boolean;
};

const ISOLATED_AUDIO: IsolatedConstraints = {
  channelCount: 1,
  echoCancellation: true,
  noiseSuppression: true,
  autoGainControl: true,
  voiceIsolation: true,
};

const BASIC_AUDIO: MediaTrackConstraints = {
  channelCount: 1,
  echoCancellation: true,
  noiseSuppression: true,
  autoGainControl: true,
};

export async function openIsolatedMic() {
  if (!navigator.mediaDevices?.getUserMedia) {
    throw new Error("This browser cannot open the microphone.");
  }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: ISOLATED_AUDIO,
      video: false,
    });
    await applyVoiceIsolation(stream);
    return stream;
  } catch {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: BASIC_AUDIO,
      video: false,
    });
    await applyVoiceIsolation(stream);
    return stream;
  }
}

export async function applyVoiceIsolation(stream: MediaStream) {
  await Promise.all(
    stream.getAudioTracks().map(async (track) => {
      try {
        await track.applyConstraints(ISOLATED_AUDIO);
      } catch {
        try {
          await track.applyConstraints(BASIC_AUDIO);
        } catch {
          /* keep the opened track */
        }
      }
    }),
  );
}

/** Share of energy in the human-speech band (about 250–3500 Hz). */
export function voiceBandScore(analyser: AnalyserNode) {
  const bins = new Uint8Array(analyser.frequencyBinCount);
  analyser.getByteFrequencyData(bins);
  const hzPerBin = analyser.context.sampleRate / analyser.fftSize;
  let voice = 0;
  let other = 0;
  for (let index = 0; index < bins.length; index += 1) {
    const hz = index * hzPerBin;
    const energy = bins[index];
    if (hz >= 250 && hz <= 3500) voice += energy;
    else other += energy;
  }
  const total = voice + other;
  if (total < 80) return 0;
  return voice / total;
}

export function isIsolatedSpeech(rms: number, voiceScore: number) {
  return rms >= 0.02 && voiceScore >= 0.52;
}
