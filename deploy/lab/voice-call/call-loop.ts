// Presentation-only coordinator around native submitPrompt/chat events. No HTTP or storage.
export type Phase = 'Idle' | 'Listening' | 'Transcribing' | 'Review' | 'Thinking' | 'Synthesizing' | 'Speaking' | 'Error' | 'Unknown';
export type CallState = { phase: Phase; draft: string; reply: string; notice: string; pending: boolean };
export type CallMessage = { id: string; parentId?: string; model?: string; role?: string; content?: string; done?: boolean; error?: unknown };
export type CallHistory = { currentId: string | null; messages: Record<string, CallMessage> };
type Ports = {
  history: () => CallHistory | undefined;
  ready: () => boolean;
  submit: (text: string) => unknown;
  synthesize: (text: string, signal: AbortSignal) => Promise<Response | null | undefined>;
  play: (blob: Blob, started: () => void) => Promise<void>;
  stopAudio: () => void;
};
type Timers = { setTimer?: (fn: () => void, ms: number) => unknown; clearTimer?: (id: any) => void };
const sessions = new WeakMap<EventTarget, CallLoop>();
export const WAIT_MS = 300000;
export class CallLoop {
  target: EventTarget;
  setTimer: (fn: () => void, ms: number) => unknown;
  clearTimer: (id: any) => void;
  state: CallState;
  closed: boolean;
  epoch: number;
  ports!: Ports;
  notify: ((state: CallState) => void) | null = null;
  before = new Set<string>();
  sent = '';
  messageId: string | null = null;
  submission: symbol | null = null;
  timer: unknown;
  audioController: AbortController | null = null;
  startHandler: (event: Event) => void;
  finishHandler: (event: Event) => void;
  constructor(target: EventTarget, { setTimer = (fn, ms) => globalThis.setTimeout(fn, ms), clearTimer = (id) => globalThis.clearTimeout(id) }: Timers = {}) {
    this.target = target;
    this.setTimer = setTimer; this.clearTimer = clearTimer;
    this.state = { phase: 'Idle', draft: '', reply: '', notice: '', pending: false };
    this.closed = true; this.epoch = 0;
    this.startHandler = (e) => this.started((e as CustomEvent).detail?.id);
    this.finishHandler = (e) => queueMicrotask(() => this.finished((e as CustomEvent).detail));
    target.addEventListener('chat:start', this.startHandler);
    target.addEventListener('chat:finish', this.finishHandler);
  }
  attach(ports: Ports, notify: (state: CallState) => void) {
    this.ports = ports; this.notify = notify; this.closed = false;
    this.emit();
    return () => { this.close(); this.notify = null; };
  }
  emit() { this.notify?.({ ...this.state }); }
  change(phase: Phase, notice = '') { this.state.phase = phase; this.state.notice = notice; this.emit(); }
  listening() {
    if (this.state.pending || !['Idle', 'Review', 'Error'].includes(this.state.phase)) return false;
    if (!this.ports.ready()) { this.change('Error', 'Use one Corvus text conversation with no attachments; finish any active reply first.'); return false; }
    this.state.draft = ''; this.change('Listening'); return true;
  }
  transcribing() { if (this.state.phase === 'Listening') this.change('Transcribing'); }
  transcribed(text: unknown) {
    if (!['Listening', 'Transcribing'].includes(this.state.phase) || this.closed) return;
    if (typeof text !== 'string' || !text.trim()) return this.mediaFailed('Transcription returned no text. Record again.');
    this.state.draft = text.trim(); this.change('Review', 'Edit the transcript, then send this turn.');
    // Future automatic submission can call send here; dictation remains separate.
  }
  cancelRecording() {
    if (['Listening', 'Transcribing'].includes(this.state.phase)) this.change('Idle', 'Recording cancelled. Nothing was sent.');
  }
  mediaFailed(notice = 'Audio is unavailable. Try recording again or use text chat.') {
    if (!this.state.pending && !this.closed) this.change('Error', notice);
  }
  send(text = this.state.draft) {
    if (this.closed || this.state.pending || this.state.phase !== 'Review' || !text.trim()) return false;
    if (!this.ports.ready()) { this.change('Review', 'The chat is busy or unavailable. Nothing was sent; check the conversation.'); return false; }
    const history = this.ports.history();
    this.before = new Set(Object.keys(history?.messages || {}));
    this.sent = text.trim(); this.messageId = null;
    this.state.draft = this.sent; this.state.reply = ''; this.state.pending = true;
    this.change('Thinking', 'Waiting for the saved reply. Ending the call will not cancel submitted chat work.');
    const attempt = Symbol('submitted turn'); this.submission = attempt;
    const uncertain = () => { if (this.submission === attempt) this.unknown(); };
    this.timer = this.setTimer(uncertain, WAIT_MS);
    try {
      // Exactly once. No AbortSignal, retry, stopResponse or backend cancellation.
      Promise.resolve(this.ports.submit(this.sent)).catch(uncertain);
    } catch { uncertain(); }
    return true;
  }
  started(id: unknown) {
    if (!this.state.pending || this.messageId || typeof id !== 'string' || this.before.has(id)) return;
    const h = this.ports.history(), row = h?.messages?.[id], parent = h?.messages?.[row?.parentId || ''];
    if (row?.model === 'corvus_pipe' && parent?.role === 'user' && parent.content === this.sent
        && !this.before.has(parent.id) && h?.currentId === id) this.messageId = id;
  }
  observe() {
    const row = this.ports?.history()?.messages?.[this.messageId || ''];
    if (this.state.pending && row?.error) this.unknown();
  }
  unknown() {
    if (!this.state.pending) return;
    this.clearTimer(this.timer);
    this.change('Unknown', 'The result could not be confirmed. Do not resend automatically. Check this conversation before deciding what to do next.');
  }
  finished(detail: { id?: string; content?: string }) {
    if (!this.state.pending || !this.messageId || detail?.id !== this.messageId) return;
    const row = this.ports.history()?.messages?.[this.messageId || ''];
    // Native events alone are not success. The Corvus Pipe rejects uncommitted replies.
    if (!row?.done || row.error || row.model !== 'corvus_pipe' || typeof row.content !== 'string'
        || !row.content.trim() || row.content !== detail.content) return this.unknown();
    const wasUnknown = this.state.phase === 'Unknown';
    this.clearTimer(this.timer); this.state.pending = false; this.state.reply = row.content;
    if (this.closed || wasUnknown) this.change('Idle', 'The reply arrived and is saved. It was not played automatically.');
    else void this.speak();
  }
  async speak() {
    if (this.closed || this.state.pending || !this.state.reply || !['Idle', 'Error', 'Thinking'].includes(this.state.phase)) return;
    const epoch = ++this.epoch; const controller = new AbortController(); this.audioController = controller;
    this.change('Synthesizing', 'The reply is saved. Preparing speech.');
    try {
      const response = await this.ports.synthesize(this.state.reply, controller.signal);
      if (this.closed || epoch !== this.epoch || controller.signal.aborted) return;
      if (!response?.ok) throw new Error('speech');
      const blob = await response.blob();
      if (this.closed || epoch !== this.epoch || controller.signal.aborted) return;
      if (!blob.size || blob.size > 8 * 1024 * 1024 || blob.type.split(';')[0] !== 'audio/wav') throw new Error('speech');
      await this.ports.play(blob, () => {
        if (!this.closed && epoch === this.epoch) this.change('Speaking');
      });
      if (!this.closed && epoch === this.epoch) this.change('Idle', 'Ready for the next turn.');
    } catch {
      if (!this.closed && epoch === this.epoch && !controller.signal.aborted)
        this.change('Error', 'The reply is saved, but speech failed. Replay it or continue with text.');
    } finally {
      if (epoch === this.epoch) { this.ports.stopAudio(); this.audioController = null; }
    }
  }
  stopSpeaking() {
    ++this.epoch; this.audioController?.abort(); this.audioController = null;
    this.ports?.stopAudio();
    if (['Synthesizing', 'Speaking'].includes(this.state.phase)) this.change('Idle', 'Speech stopped. The saved reply and memory processing are unchanged.');
  }
  close() {
    this.closed = true; this.stopSpeaking();
    this.cancelRecording();
    // Keep correlation and timeout alive for submitted work across layout remount/hangup.
  }
}
export function callSession(target: EventTarget, timers?: Timers): CallLoop {
  if (!sessions.has(target)) sessions.set(target, new CallLoop(target, timers));
  return sessions.get(target)!;
}
