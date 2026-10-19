"""Pinned 0.6.5 native dictation source edits; output only into an isolated tree."""
import hashlib
from pathlib import Path
import sys

VOICE = 'src/lib/components/chat/MessageInput/VoiceRecording.svelte'
COMPOSER = 'src/lib/components/chat/MessageInput.svelte'
API = 'src/lib/apis/audio/index.ts'
HELPER = 'src/lib/utils/corvus-dictation.ts'
PINS = {
    VOICE: '91713f5f7ec32cb1382cd735362f4f3da7389e6c85e1b38f28a2cbb62cd275d6',
    COMPOSER: 'adf077a8cb5806dfe5b6ecc3fecdf53c70ddc623e63637a1104f8406997f5cb0',
    API: '47f9b585a019c13d98f1559c674d81e1b14c943a217f072bb0695b7407e379e1',
}

VOICE_LOGIC = '''	let cancelled = false;
	let generation = 0;
	let transcriptionController;
	let audioContext;

	const releaseMedia = () => {
		stopDurationCounter();
		stream?.getTracks().forEach((track) => track.stop());
		stream = null;
		if (audioContext) {
			const context = audioContext;
			audioContext = null;
			void context.close().catch(() => {});
		}
	};

	const transcribeHandler = async ({ blob, filename }) => {
		const take = generation;
		if (!(await validateDictationWav(blob))) {
			if (!cancelled && take === generation) {
				toast.error($i18n.t('This recording format is not supported for private dictation.'));
				dispatch('cancel');
			}
			return;
		}
		if (cancelled || take !== generation) return;
		const controller = new AbortController();
		transcriptionController = controller;
		try {
			const file = blobToFile(blob, filename);
			const res = await transcribeAudio(localStorage.token, file, controller.signal);
			if (!cancelled && take === generation && !controller.signal.aborted
				&& typeof res?.text === 'string' && res.text.trim()) {
				dispatch('confirm', { text: res.text });
			}
		} catch {
			if (!cancelled && take === generation && !controller.signal.aborted) {
				toast.error($i18n.t('Dictation is unavailable.'));
			}
		} finally {
			if (transcriptionController === controller) transcriptionController = null;
		}
	};

	const startRecording = async () => {
		loading = true;
		cancelled = false;
		confirmed = false;
		const take = ++generation;
		// Private dictation must not switch to a browser/vendor speech engine.
		if ($config.audio.stt.engine === 'web' || ($settings?.audio?.stt?.engine ?? '') === 'web') {
			toast.error($i18n.t('Browser speech recognition is unavailable for private dictation.'));
			loading = false;
			recording = false;
			dispatch('cancel');
			return;
		}
		try {
			const acquired = await navigator.mediaDevices.getUserMedia({
				audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true }
			});
			if (cancelled || take !== generation || !recording) {
				acquired.getTracks().forEach((track) => track.stop());
				return;
			}
			stream = acquired;
			mediaRecorder = new MediaRecorder(stream);
			mediaRecorder.onstart = () => {
				if (cancelled || take !== generation) return;
				loading = false;
				audioChunks = [];
				startDurationCounter();
				analyseAudio(stream);
			};
			mediaRecorder.ondataavailable = (event) => {
				if (!cancelled && take === generation && event.data.size) audioChunks.push(event.data);
			};
			mediaRecorder.onstop = async () => {
				if (take !== generation) return;
				const chunks = audioChunks;
				audioChunks = [];
				const accept = confirmed && !cancelled && take === generation;
				confirmed = false;
				releaseMedia();
				try {
					if (accept) await transcribeHandler(recordingBlob(chunks, mediaRecorder.mimeType));
				} catch {
					if (!cancelled && take === generation) {
						toast.error($i18n.t('This recording format is not supported for private dictation.'));
						dispatch('cancel');
					}
				} finally {
					if (take === generation) { loading = false; recording = false; }
				}
			};
			mediaRecorder.start();
		} catch {
			if (take === generation) {
				releaseMedia();
				loading = false;
				recording = false;
				toast.error($i18n.t('Microphone is unavailable.'));
				dispatch('cancel');
			}
		}
	};

	const stopRecording = async () => {
		cancelled = true;
		confirmed = false;
		generation++;
		transcriptionController?.abort();
		transcriptionController = null;
		if (mediaRecorder && mediaRecorder.state !== 'inactive') mediaRecorder.stop();
		audioChunks = [];
		releaseMedia();
		recording = false;
		loading = false;
	};

	const confirmRecording = async () => {
		if (cancelled || !recording || !mediaRecorder || mediaRecorder.state === 'inactive') return;
		loading = true;
		confirmed = true;
		mediaRecorder.stop();
		releaseMedia();
	};

'''

API_LOGIC = '''export const transcribeAudio = async (token: string, file: File, signal?: AbortSignal) => {
	const data = new FormData();
	data.append('file', file);
	let response;
	try {
		response = await fetch(`${AUDIO_API_BASE_URL}/transcriptions`, {
			method: 'POST',
			headers: { Accept: 'application/json', authorization: `Bearer ${token}` },
			body: data, signal, redirect: 'error', cache: 'no-store'
		});
		if (!response.ok) throw new Error('Dictation is unavailable.');
		return await response.json();
	} catch (error) {
		if (signal?.aborted) throw error;
		throw new Error('Dictation is unavailable.');
	}
};

'''


def patch_sources(sources):
    for path, digest in PINS.items():
        if hashlib.sha256(sources[path].encode()).hexdigest() != digest:
            raise ValueError('Expected exact reviewed 0.6.5 source: '+path)
    voice = sources[VOICE]
    voice = voice.replace("\timport { transcribeAudio } from '$lib/apis/audio';", "\timport { transcribeAudio } from '$lib/apis/audio';\n\timport { recordingBlob, validateDictationWav } from '$lib/utils/corvus-dictation';")
    voice = voice.replace('const audioContext = new AudioContext();', 'audioContext = new AudioContext();')
    a, b = voice.index('\tconst transcribeHandler ='), voice.index('\tlet resizeObserver;')
    voice = voice[:a]+VOICE_LOGIC+voice[b:]
    voice = voice.replace('resizeObserver.disconnect();', 'stopRecording();\n\t\tresizeObserver?.disconnect();')
    composer = sources[COMPOSER]
    auto = "\t\t\t\t\t\t\t\tif ($settings?.speechAutoSend ?? false) {\n\t\t\t\t\t\t\t\t\tdispatch('submit', prompt);\n\t\t\t\t\t\t\t\t}"
    if composer.count(auto) != 1:
        raise ValueError('Expected one dictation auto-submit block')
    composer = composer.replace(auto, '\t\t\t\t\t\t\t\t// Dictation stays editable; retain speechAutoSend for future voice modes.')
    api = sources[API]
    a, b = api.index('export const transcribeAudio ='), api.index('export const synthesizeOpenAISpeech =')
    api = api[:a]+API_LOGIC+api[b:]
    return {VOICE: voice, COMPOSER: composer, API: api,
            HELPER: Path(__file__).with_name('dictation.ts').read_text()}


if __name__ == '__main__':
    source, output = (Path(arg).resolve() for arg in sys.argv[1:])
    if source == output or source in output.parents or output in source.parents:
        raise ValueError('Use a separate isolated output tree')
    prepared = patch_sources({p: (source/p).read_text() for p in PINS})
    for name in prepared:
        if (output/name).exists(): raise ValueError('Refusing to overwrite existing output')
    for name, text in prepared.items():
        target = output/name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
