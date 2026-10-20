/** Native composer helpers: bytes stay transient; saved state contains references only. */
export const IMAGE_LIMIT = 6 * 1024 * 1024;
export function persistentDraft(input: any) {
	return { ...input, files: (input.files ?? []).filter((file: any) => file.type !== 'image') };
}
export function imageDraft(files: any[], arena: boolean): Blob | null {
	const images = files.filter((file) => file.type === 'image');
	if (!images.length) return null;
	if (arena || images.length !== 1 || files.length !== 1) throw new Error('Use one PNG/JPEG image without Arena.');
	const match = /^data:(image\/(?:png|jpeg));base64,([A-Za-z0-9+/]*={0,2})$/.exec(images[0].url ?? '');
	if (!match || match[2].length > 4 * Math.ceil(IMAGE_LIMIT / 3)) throw new Error('Invalid or oversized image.');
	let decoded: string;
	try { decoded = atob(match[2]); } catch { throw new Error('Invalid image.'); }
	if (!decoded.length || decoded.length > IMAGE_LIMIT) throw new Error('Invalid or oversized image.');
	const bytes = Uint8Array.from(decoded, (c) => c.charCodeAt(0));
	const png = [137,80,78,71,13,10,26,10];
	if (!(match[1] === 'image/png' ? png.every((b,i) => bytes[i] === b) : bytes[0] === 255 && bytes[1] === 216 && bytes[2] === 255)) throw new Error('Invalid image.');
	return new Blob([bytes], { type: match[1] });
}
export async function uploadImage(token: string, chat: string, message: string, blob: Blob, signal: AbortSignal) {
	const response = await fetch(`/api/v1/files/corvus-image/${chat}/${message}`, {
		method: 'POST', signal, headers: { Authorization: `Bearer ${token}`, 'Content-Type': blob.type, 'X-Corvus-Arena': 'false' }, body: blob
	});
	if (!response.ok) throw new Error('Image upload not confirmed. Check this turn before retrying.');
	const reference = await response.json();
	if (reference.type !== 'image' || !/^[a-f0-9-]{36}$/.test(reference.corvus_ref) || reference.url !== `/api/v1/files/${reference.corvus_ref}/content`) throw new Error('Invalid image reference.');
	return reference;
}

export async function reconcileImage(token: string, chat: string, message: string) {
    const response = await fetch(`/api/v1/files/corvus-image/${chat}/${message}`, {
        headers: { Authorization: `Bearer ${token}` }, cache: 'no-store'
    });
    if (!response.ok) return null;
    const result = await response.json();
    if (result.state !== 'READY') return null;
    const reference = result.reference;
    if (reference?.type !== 'image' || !/^[a-f0-9-]{36}$/.test(reference.corvus_ref)
            || reference.url !== `/api/v1/files/${reference.corvus_ref}/content`) return null;
    return reference;
}
