// Browser audio I/O for the Gemini Live counter.
// Mic: getUserMedia (browser AEC + noise suppression) -> AudioWorklet -> 16 kHz mono PCM16 frames (~50 ms).
// Speaker: gapless scheduling of 24 kHz PCM16 chunks; flush() stops instantly on barge-in.

const CAPTURE_WORKLET = `
class PcmCapture extends AudioWorkletProcessor {
  constructor() {
    super();
    this.ratio = sampleRate / 16000;
    this.t = 0; this.acc = 0; this.n = 0;
    this.out = new Int16Array(800); this.idx = 0; this.energy = 0; this.count = 0;
  }
  process(inputs) {
    const ch = inputs[0] && inputs[0][0];
    if (!ch) return true;
    for (let i = 0; i < ch.length; i++) {
      const s = ch[i];
      this.energy += s * s; this.count++;
      this.acc += s; this.n++; this.t += 1;
      if (this.t >= this.ratio) {           // box-filter downsample (anti-alias) to 16 kHz
        this.t -= this.ratio;
        let v = this.acc / this.n; this.acc = 0; this.n = 0;
        v = v > 1 ? 1 : v < -1 ? -1 : v;
        this.out[this.idx++] = v < 0 ? v * 0x8000 : v * 0x7fff;
        if (this.idx === this.out.length) {
          const rms = Math.sqrt(this.energy / Math.max(1, this.count));
          this.port.postMessage({ pcm: this.out.buffer, rms }, [this.out.buffer]);
          this.out = new Int16Array(800); this.idx = 0; this.energy = 0; this.count = 0;
        }
      }
    }
    return true;
  }
}
registerProcessor('pcm-capture', PcmCapture);
`;

export interface MicFrame {
  pcm: ArrayBuffer;
  rms: number;
}

export class MicStreamer {
  private ctx: AudioContext | null = null;
  private stream: MediaStream | null = null;
  private node: AudioWorkletNode | null = null;

  async start(onFrame: (f: MicFrame) => void): Promise<void> {
    this.stream = await navigator.mediaDevices.getUserMedia({
      audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true },
    });
    this.ctx = new AudioContext();
    const url = URL.createObjectURL(new Blob([CAPTURE_WORKLET], { type: 'application/javascript' }));
    await this.ctx.audioWorklet.addModule(url);
    URL.revokeObjectURL(url);
    const src = this.ctx.createMediaStreamSource(this.stream);
    this.node = new AudioWorkletNode(this.ctx, 'pcm-capture');
    this.node.port.onmessage = (e) => onFrame(e.data as MicFrame);
    src.connect(this.node);
  }

  stop(): void {
    this.node?.port.close();
    this.node?.disconnect();
    this.stream?.getTracks().forEach((t) => t.stop());
    this.ctx?.close().catch(() => undefined);
    this.node = null; this.stream = null; this.ctx = null;
  }
}

export class PcmPlayer {
  private ctx: AudioContext;
  private nextStart = 0;
  private sources = new Set<AudioBufferSourceNode>();
  private gain: GainNode;

  constructor(private sampleRate = 24000) {
    this.ctx = new AudioContext({ sampleRate });
    this.gain = this.ctx.createGain();
    this.gain.connect(this.ctx.destination);
  }

  get playing(): boolean {
    return this.sources.size > 0;
  }

  async resume(): Promise<void> {
    if (this.ctx.state === 'suspended') await this.ctx.resume();
  }

  playPcm16(data: ArrayBuffer): void {
    const int16 = new Int16Array(data);
    const buf = this.ctx.createBuffer(1, int16.length, this.sampleRate);
    const ch = buf.getChannelData(0);
    for (let i = 0; i < int16.length; i++) ch[i] = int16[i] / 0x8000;
    this.schedule(buf);
  }

  async playEncoded(bytes: ArrayBuffer): Promise<void> {
    const buf = await this.ctx.decodeAudioData(bytes);
    this.schedule(buf);
  }

  private schedule(buf: AudioBuffer): void {
    const src = this.ctx.createBufferSource();
    src.buffer = buf;
    src.connect(this.gain);
    const startAt = Math.max(this.ctx.currentTime + 0.03, this.nextStart);
    src.start(startAt);
    this.nextStart = startAt + buf.duration;
    this.sources.add(src);
    src.onended = () => this.sources.delete(src);
  }

  /** Barge-in: drop everything queued or playing, immediately. */
  flush(): void {
    this.sources.forEach((s) => { try { s.stop(); } catch { /* already stopped */ } });
    this.sources.clear();
    this.nextStart = 0;
  }

  close(): void {
    this.flush();
    this.ctx.close().catch(() => undefined);
  }
}

export function base64ToArrayBuffer(b64: string): ArrayBuffer {
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return bytes.buffer;
}

// Web Speech API (fallback mode only, when Gemini Live is unavailable)
export function createBrowserRecognizer(lang: string, onFinal: (text: string) => void): any | null {
  const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
  if (!SR) return null;
  const rec = new SR();
  rec.lang = lang;
  rec.continuous = true;
  rec.interimResults = false;
  rec.onresult = (e: any) => {
    for (let i = e.resultIndex; i < e.results.length; i++) {
      if (e.results[i].isFinal) onFinal(e.results[i][0].transcript);
    }
  };
  return rec;
}
