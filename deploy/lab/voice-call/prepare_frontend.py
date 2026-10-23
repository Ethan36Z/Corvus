"""Opt-in Voice V1 overlay on exact deployed 0.6.5 + existing dictation sources.

Writes only a fresh isolated overlay. Never edits a live checkout or builds/deploys.
"""
import hashlib
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
CALL = 'src/lib/components/chat/MessageInput/CallOverlay.svelte'
VOICE = 'src/lib/components/chat/MessageInput/VoiceRecording.svelte'
API = 'src/lib/apis/audio/index.ts'
CONTROLS = 'src/lib/components/chat/ChatControls.svelte'
COMPOSER = 'src/lib/components/chat/MessageInput.svelte'
PINS = {
    COMPOSER: '16985bb74b2d30623a600386e49cb2b2dc10a33b19e09450d78bd711c0cec00c',
    CALL: 'd701324a7e4a3b669d0fb746e05fbddf93a79eb2d6b158a9ab15b9798a459671',
    VOICE: '557fd96cc2fa0ec3f7556897d81a4180446dd95339f0b00aad6044d883e1338c',
    API: '9c6ec8c1d15b1fd78b89f06996279ec891cd2caf7df3ec9557d04a013ce1c895',
    CONTROLS: '6f534b7fa71772d04aed474c5397907fca5aa0e9cb1ecac66ca27dacb900b221',
}

def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('Unexpected pinned source seam')
    return text.replace(old, new, 1)

def patch_sources(sources):
    for name, digest in PINS.items():
        if hashlib.sha256(sources[name].encode()).hexdigest() != digest:
            raise ValueError('Unreviewed Voice V1 input: ' + name)
    call = sources[CALL]
    call = replace_once(call, "\tconst dispatch = createEventDispatcher();", "\tconst dispatch = createEventDispatcher();\n\timport CorvusCall from './CorvusCall.svelte';\n\texport let history;\n\tconst corvusMode = modelId === 'corvus_pipe';")
    # modelId is initialized by its exported prop before derived constants execute.
    call = call.replace("\tconst corvusMode = modelId === 'corvus_pipe';", '')
    call = replace_once(call, '\texport let modelId;', "\texport let modelId;\n\tconst corvusMode = modelId === 'corvus_pipe';")
    for seam in ('\tonMount(async () => {', '\tonDestroy(async () => {'):
        call = replace_once(call, seam, seam + '\n\t\tif (corvusMode) return;')
    branch = '''{#if $showCallOverlay}
  {#if corvusMode}
    {#if import.meta.env.VITE_CORVUS_VOICE_CALL === 'true'}
      <CorvusCall {eventTarget} {submitPrompt} {history} {modelId} {files}
        on:close={() => { showCallOverlay.set(false); dispatch('close'); }} />
    {:else}
      <div class="p-5" role="status">
        <p>Corvus Voice Call is disabled. Dictation remains available.</p>
        <button type="button" on:click={() => { showCallOverlay.set(false); dispatch('close'); }}>Close</button>
      </div>
    {/if}
  {:else}'''
    call = replace_once(call, '{#if $showCallOverlay}\n', branch + '\n')
    assert call.rstrip().endswith('{/if}')
    call = call.rstrip()[:-5] + '  {/if}\n{/if}\n'

    voice = replace_once(sources[VOICE], '\texport let recording = false;', '\texport let recording = false;\n\texport let callMode = false;')
    voice = replace_once(voice, '\t\tconfirmed = true;\n\t\tmediaRecorder.stop();', "\t\tconfirmed = true;\n\t\tif (callMode) dispatch('callphase');\n\t\tmediaRecorder.stop();")
    voice = replace_once(voice, "\t\t\t\tdispatch('confirm', { text: res.text });\n\t\t\t}", "\t\t\t\tdispatch('confirm', { text: res.text });\n\t\t\t} else if (callMode && !cancelled && take === generation && !controller.signal.aborted) {\n\t\t\t\tdispatch('callerror');\n\t\t\t}")
    voice = replace_once(voice, "\t\t\t\ttoast.error($i18n.t('Dictation is unavailable for this recording.'));", "\t\t\t\ttoast.error($i18n.t('Dictation is unavailable for this recording.'));\n\t\t\t\tif (callMode) dispatch('callerror');")

    api = sources[API]
    start, end = api.index('export const synthesizeOpenAISpeech ='), api.index('interface AvailableModelsResponse')
    speech = api[start:end]
    speech = replace_once(speech, '\tmodel?: string\n', '\tmodel?: string,\n\tsignal?: AbortSignal\n')
    speech = replace_once(speech, "\t\tmethod: 'POST',", "\t\tsignal,\n\t\tmethod: 'POST',")
    api = api[:start] + speech + api[end:]

    # Native layout switches must remount when model identity changes; pass existing history.
    controls = sources[CONTROLS]
    pattern = r'(?P<indent>\t+)<CallOverlay\n(?P<body>.*?)\n(?P=indent)/>'
    def wrapped(match):
        indent = match['indent']; body = match['body']
        return indent + '{#key modelId}\n' + indent + '<CallOverlay\n' + indent + '\t{history}\n' + body + '\n' + indent + '/>\n' + indent + '{/key}'
    controls, count = re.subn(pattern, wrapped, controls, flags=re.S)
    if count != 2:
        raise ValueError('Expected both native Call layouts')
    # Corvus enters the opt-in panel without legacy mic preflight/browser-model loading.
    indent = '\t' * 14
    seam = indent + "if ($config.audio.stt.engine === 'web') {"
    guard = '''if (selectedModelIds.at(0) === 'corvus_pipe') {
  if (import.meta.env.VITE_CORVUS_VOICE_CALL !== 'true') {
    toast.error($i18n.t('Corvus Voice Call is disabled. Use dictation instead.'));
    return;
  }
  showCallOverlay.set(true);
  showControls.set(true);
  return;
}
'''
    composer = replace_once(sources[COMPOSER], seam, '\n'.join(indent + line for line in guard.splitlines()) + '\n' + seam)
    return {CALL: call, VOICE: voice, API: api, CONTROLS: controls, COMPOSER: composer,
            'src/lib/components/chat/MessageInput/CorvusCall.svelte': (HERE/'CorvusCall.svelte').read_text(),
            'src/lib/utils/corvus-call.ts': (HERE/'call-loop.ts').read_text()}

def prepare(source, output):
    source, output = Path(source).resolve(), Path(output).resolve()
    if output.exists() or source == output or source in output.parents or output in source.parents:
        raise ValueError('Require a fresh, separate output directory')
    files = patch_sources({p: (source/p).read_text() for p in PINS})
    for name, text in files.items():
        path = output/name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(text)
    proof = {'input_sha256': PINS, 'output_sha256': {p:hashlib.sha256(t.encode()).hexdigest() for p,t in files.items()},
             'default_enabled': False, 'gate': 'VITE_CORVUS_VOICE_CALL=true', 'model_id':'corvus_pipe',
             'scope':'frontend overlay only; no build, backend change, runtime activation or memory migration'}
    (output/'voice-v1-proof.json').write_text(json.dumps(proof, indent=2)+'\n')
    return proof

if __name__ == '__main__':
    print(json.dumps(prepare(*sys.argv[1:]), indent=2))
