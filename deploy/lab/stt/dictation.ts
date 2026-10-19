// Metadata/validation only. This is not a decoder, resampler or WAV encoder.
const MAX_AUDIO = 8 * 1024 * 1024;
const extensions: Record<string, string> = {
	'audio/wav': 'wav', 'audio/x-wav': 'wav', 'audio/webm': 'webm',
	'audio/mp4': 'm4a', 'audio/ogg': 'ogg', 'audio/mpeg': 'mp3', 'audio/flac': 'flac'
};
const baseType = (type: string) => type.split(';', 1)[0].trim().toLowerCase();

export function recordingBlob(chunks: Blob[], recorderMime: string) {
	const observed = chunks.filter((chunk) => chunk.size > 0).map((chunk) => chunk.type).filter(Boolean);
	const mime = observed[0] || recorderMime;
	const base = baseType(mime || '');
	if (!extensions[base] || (recorderMime && baseType(recorderMime) !== base)
		|| observed.some((type) => baseType(type) !== base)) throw new Error('Unsupported recording format.');
	const blob = new Blob(chunks, { type: mime });
	if (!blob.size || blob.size > MAX_AUDIO) throw new Error('Unsupported recording size.');
	return { blob, filename: `recording.${extensions[base]}` };
}

export async function validateDictationWav(blob: Blob): Promise<boolean> {
	if (!['audio/wav', 'audio/x-wav'].includes(baseType(blob.type)) || !blob.size || blob.size > MAX_AUDIO) return false;
	const buffer = await blob.arrayBuffer();
	const view = new DataView(buffer);
	const tag = (at: number) => String.fromCharCode(...new Uint8Array(buffer, at, 4));
	if (buffer.byteLength < 44 || tag(0) !== 'RIFF' || tag(8) !== 'WAVE'
		|| view.getUint32(4, true) !== buffer.byteLength - 8) return false;
	let offset = 12;
	let alignment = 0;
	let samples = 0;
	let format = false;
	let data = false;
	while (offset + 8 <= buffer.byteLength) {
		const size = view.getUint32(offset + 4, true);
		const end = offset + 8 + size;
		if (end > buffer.byteLength) return false;
		if (tag(offset) === 'fmt ') {
			if (format || size !== 16 || view.getUint16(offset + 8, true) !== 1) return false;
			const channels = view.getUint16(offset + 10, true);
			alignment = channels * 2;
			if (![1, 2].includes(channels) || view.getUint32(offset + 12, true) !== 16000
				|| view.getUint32(offset + 16, true) !== 16000 * alignment
				|| view.getUint16(offset + 20, true) !== alignment
				|| view.getUint16(offset + 22, true) !== 16) return false;
			format = true;
		} else if (tag(offset) === 'data') {
			if (!format || data || !size || size % alignment) return false;
			samples = size / alignment;
			data = true;
		}
		offset = end + size % 2;
	}
	return offset === buffer.byteLength && format && data && samples <= 120 * 16000;
}
