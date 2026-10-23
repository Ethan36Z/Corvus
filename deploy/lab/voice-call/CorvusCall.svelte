<script lang="ts">
  import { onMount, onDestroy, createEventDispatcher } from 'svelte';
  import { config } from '$lib/stores';
  import { synthesizeOpenAISpeech } from '$lib/apis/audio';
  import VoiceRecording from './VoiceRecording.svelte';
  import { callSession, type CallLoop, type CallState, type CallHistory } from '$lib/utils/corvus-call';
  export let eventTarget: EventTarget;
  export let submitPrompt: Function;
  export let history: CallHistory;
  export let modelId: string;
  export let files: unknown[] = [];
  const dispatch = createEventDispatcher();
  let loop: CallLoop;
  let view: CallState = { phase: 'Idle', draft: '', reply: '', notice: '', pending: false };
  let draft = '';
  let recording = false;
  let audio: HTMLAudioElement;
  let url: string | null = null;
  let finishPlayback: (() => void) | null = null;
  let detach = () => {};
  const ready = () => Boolean(modelId === 'corvus_pipe' && !(files?.length)
    && $config?.audio?.tts?.engine === 'corvus-kokoro'
    && (!history?.currentId || (history.messages?.[history.currentId]?.done
      && !history.messages?.[history.currentId]?.error)));
  const stopAudio = () => {
    if (audio) { audio.onended = null; audio.onerror = null; audio.pause(); audio.removeAttribute('src'); audio.load(); }
    if (url) { URL.revokeObjectURL(url); url = null; }
    finishPlayback?.(); finishPlayback = null;
  };
  const play = (blob: Blob, started: () => void) => new Promise<void>((resolve, reject) => {
    stopAudio(); url = URL.createObjectURL(blob); audio.src = url;
    finishPlayback = resolve;
    audio.onended = () => resolve();
    audio.onerror = () => reject(new Error('playback'));
    audio.play().then(started).catch(reject);
  });
  onMount(() => {
    loop = callSession(eventTarget);
    detach = loop.attach({ history: () => history, ready,
      submit: (text) => submitPrompt(text, { _raw: true }),
      synthesize: (text, signal) => synthesizeOpenAISpeech(localStorage.token, 'af_mica', text, 'kokoro', signal),
      play, stopAudio
    }, (next) => { view = next; if (next.phase === 'Review') draft = next.draft; });
  });
  onDestroy(() => { recording = false; detach(); stopAudio(); });
  $: if (loop && history) loop.observe();
  const start = () => { if (loop?.listening()) recording = true; };
  const close = () => { recording = false; loop?.close(); dispatch('close'); };
</script>

<div class="w-full max-w-lg p-5 flex flex-col gap-4" aria-label="Corvus Voice Call">
  <h2 class="text-lg font-semibold">Corvus Voice Call</h2>
  <p role="status" aria-live="polite">{view.phase}</p>
  {#if view.notice}<p class="text-sm">{view.notice}</p>{/if}
  {#if recording}
    <VoiceRecording bind:recording callMode={true}
      on:callphase={() => loop.transcribing()}
      on:callerror={() => loop.mediaFailed('Transcription failed. Record again or use text chat.')}
      on:confirm={(e) => { loop.transcribed(e.detail.text); recording = false; }}
      on:cancel={() => { loop.cancelRecording(); recording = false; }} />
  {/if}
  {#if view.phase === 'Review'}
    <label class="flex flex-col gap-2">Review transcript
      <textarea class="border rounded p-2 bg-transparent" bind:value={draft} rows="4" />
    </label>
    <button type="button" disabled={!draft.trim()} on:click={() => loop.send(draft)}>Send this turn</button>
  {/if}
  {#if ['Idle', 'Review', 'Error'].includes(view.phase) && !view.pending}
    <button type="button" on:click={start}>Record a turn</button>
  {/if}
  {#if ['Listening', 'Transcribing'].includes(view.phase)}
    <button type="button" on:click={() => { recording = false; loop.cancelRecording(); }}>Cancel recording</button>
  {/if}
  {#if ['Synthesizing', 'Speaking'].includes(view.phase)}
    <button type="button" on:click={() => loop.stopSpeaking()}>Stop speaking</button>
  {/if}
  {#if view.reply && ['Idle', 'Error'].includes(view.phase) && !view.pending}
    <button type="button" on:click={() => loop.speak()}>Replay saved reply</button>
  {/if}
  {#if view.phase === 'Unknown'}
    <p>Check the conversation history. This call will not resend the turn.</p>
  {/if}
  <button type="button" on:click={close}>End call</button>
  <audio bind:this={audio} hidden />
</div>
