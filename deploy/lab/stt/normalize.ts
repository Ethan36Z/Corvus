// Browser-only normalization. Native decoder allocations are NOT hard-bounded.
const INPUT_LIMIT = 8 * 1024 * 1024;
const OUTPUT_LIMIT = 44 + 120 * 16000 * 2;
let decoding = false;
const invalid = () => new Error('This recording cannot be normalized for private dictation.');
const cancelled = (signal?: AbortSignal) => { if (signal?.aborted) throw new DOMException('Cancelled', 'AbortError'); };
const typeOf = (type: string) => type.split(';', 1)[0].trim().toLowerCase();

// Container-boundary checks catch declared-size truncation before decoder tolerance
// can conceal it. They are not checksums or complete codec/bitstream validators.
function checkContainer(buffer: ArrayBuffer, mime: string) {
 const v = new DataView(buffer), bytes = new Uint8Array(buffer), length = bytes.length;
 const tag = (at: number, n = 4) => String.fromCharCode(...bytes.subarray(at, at + n));
 if (['audio/wav', 'audio/x-wav'].includes(mime)) {
  if (length < 44 || tag(0) !== 'RIFF' || tag(8) !== 'WAVE' || v.getUint32(4, true) !== length - 8) throw invalid();
  let at = 12, fmt = false, data = false, alignment = 0;
  while (at + 8 <= length) {
   const size = v.getUint32(at + 4, true), end = at + 8 + size;
   if (end > length) throw invalid();
   if (tag(at) === 'fmt ') {
    if (fmt || size !== 16 || v.getUint16(at + 8, true) !== 1 || v.getUint16(at + 22, true) !== 16) throw invalid();
    const channels = v.getUint16(at + 10, true), rate = v.getUint32(at + 12, true);
    if (![1, 2].includes(channels) || rate < 8000 || rate > 96000 || v.getUint16(at + 20, true) !== channels * 2
      || v.getUint32(at + 16, true) !== rate * channels * 2) throw invalid();
    alignment = channels * 2; fmt = true;
   } else if (tag(at) === 'data') {
    if (!fmt || data || !size || size % alignment) throw invalid();
    data = true;
   }
   at = end + size % 2;
  }
  if (at !== length || !fmt || !data) throw invalid();
 } else if (mime === 'audio/mp4') {
  let at = 0; const found = new Set<string>();
  while (at + 8 <= length) {
   let size = v.getUint32(at), header = 8;
   if (size === 1) {
    if (at + 16 > length) throw invalid();
    size = Number(v.getBigUint64(at + 8)); header = 16;
   }
   if (!Number.isSafeInteger(size) || size < header || at + size > length) throw invalid();
   found.add(tag(at + 4)); at += size;
  }
  if (at !== length || !['ftyp', 'moov', 'mdat'].every(t => found.has(t))) throw invalid();
 } else if (mime === 'audio/webm') {
  if (length < 16 || tag(0) !== '\x1a\x45\xdf\xa3') throw invalid();
  const masters = new Set([0x1a45dfa3, 0x18538067, 0x1549a966, 0x1654ae6b, 0xae, 0xe1, 0x1f43b675, 0xa0]);
  let elements = 0, blocks = 0;
  const vint = (at: number, id: boolean) => {
   if (at >= length || !bytes[at]) throw invalid();
   let n = 1, mask = 128;
   while (!(bytes[at] & mask)) { n++; mask >>= 1; }
   if (n > (id ? 4 : 8) || at + n > length) throw invalid();
   let value = id ? bytes[at] : bytes[at] & (mask - 1);
   let unknown = !id && value === mask - 1;
   for (let i = 1; i < n; i++) { value = value * 256 + bytes[at + i]; unknown = unknown && bytes[at + i] === 255; }
   return { n, value, unknown };
  };
  const scan = (start: number, end: number, depth: number) => {
   if (depth > 8) throw invalid();
   let at = start;
   while (at < end) {
    if (++elements > 100000) throw invalid();
    const id = vint(at, true), size = vint(at + id.n, false), begin = at + id.n + size.n;
    // Recorder WebM uses an unknown-length Segment. Other unknown sizes fail closed.
    if (size.unknown && id.value !== 0x18538067) throw invalid();
    const stop = size.unknown ? end : begin + size.value;
    if (!Number.isSafeInteger(stop) || stop > end || begin > stop) throw invalid();
    if (masters.has(id.value)) scan(begin, stop, depth + 1);
    if (id.value === 0xa3 || id.value === 0xa1) { if (stop - begin < 4) throw invalid(); blocks++; }
    at = stop;
   }
  };
  scan(0, length, 0); if (!blocks) throw invalid();
 } else throw invalid();
}

// Exported separately to test PCM frame math and the allocation guard.
export async function encodePcmWav(audio: AudioBuffer, signal?: AbortSignal, maxBytes = OUTPUT_LIMIT): Promise<Blob> {
 cancelled(signal);
 const frames = audio.length, channels = audio.numberOfChannels;
 if (audio.sampleRate !== 16000 || !Number.isSafeInteger(frames) || frames <= 0 || frames > 120 * 16000
   || ![1, 2].includes(channels) || 44 + frames * 2 > Math.min(maxBytes, OUTPUT_LIMIT)) throw invalid();
 const buffer = new ArrayBuffer(44 + frames * 2), v = new DataView(buffer);
 const tag = (at: number, value: string) => [...value].forEach((c, i) => v.setUint8(at + i, c.charCodeAt(0)));
 tag(0, 'RIFF'); v.setUint32(4, buffer.byteLength - 8, true); tag(8, 'WAVE'); tag(12, 'fmt ');
 v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true);
 v.setUint32(24, 16000, true); v.setUint32(28, 32000, true); v.setUint16(32, 2, true); v.setUint16(34, 16, true);
 tag(36, 'data'); v.setUint32(40, frames * 2, true);
 const left = audio.getChannelData(0), right = channels === 2 ? audio.getChannelData(1) : left;
 for (let at = 0; at < frames; at += 16384) {
  cancelled(signal);
  for (let i = at; i < Math.min(frames, at + 16384); i++) {
   const sample = (left[i] + right[i]) / 2;
   if (!Number.isFinite(sample)) throw invalid();
   const clipped = Math.max(-1, Math.min(1, sample));
   v.setInt16(44 + i * 2, Math.round(clipped * (clipped < 0 ? 32768 : 32767)), true);
  }
  await new Promise(resolve => setTimeout(resolve, 0));
 }
 cancelled(signal);
 return new Blob([buffer], { type: 'audio/wav' });
}

export async function normalizeRecording(blob: Blob, signal?: AbortSignal): Promise<Blob> {
 cancelled(signal);
 const mime = typeOf(blob.type);
 if (decoding || !blob.size || blob.size > INPUT_LIMIT || !['audio/webm', 'audio/mp4', 'audio/wav', 'audio/x-wav'].includes(mime)) throw invalid();
 decoding = true;
 const operation = new AbortController();
 // Keep the single-operation latch until the native decoder actually settles,
 // including after logical cancellation/timeout; abort cannot stop its allocations.
 const work = (async () => {
  try {
   const bytes = await blob.arrayBuffer(); cancelled(operation.signal); checkContainer(bytes, mime);
   const context = new OfflineAudioContext(1, 1, 16000);
   const decoded = await context.decodeAudioData(bytes); cancelled(operation.signal);
   return await encodePcmWav(decoded, operation.signal);
  } catch { cancelled(operation.signal); throw invalid(); }
  finally { decoding = false; }
 })();
 let timer: ReturnType<typeof setTimeout>;
 let onAbort: () => void;
 const interrupted = new Promise<never>((_, reject) => {
  onAbort = () => { operation.abort(); reject(new DOMException('Cancelled', 'AbortError')); };
  signal?.addEventListener('abort', onAbort, { once: true });
  timer = setTimeout(() => { operation.abort(); reject(invalid()); }, 15000);
 });
 try { return await Promise.race([work, interrupted]); }
 finally { clearTimeout(timer!); signal?.removeEventListener('abort', onAbort!); }
}
