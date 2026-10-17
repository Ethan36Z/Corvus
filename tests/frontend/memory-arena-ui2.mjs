/** Run against a checksum-verified --arena-ui2 source tree; all HTTP is mocked. */
import assert from 'node:assert/strict';
import { test } from 'node:test';
import vm from 'node:vm';
import { createRequire } from 'node:module';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { resolve, join } from 'node:path';
import { pathToFileURL } from 'node:url';

const root = resolve(process.argv[2]);
const require = createRequire(join(root, 'package.json'));
const ts = require('typescript');
const svelte = require('svelte/compiler');
const output = join(root, '.arena-ui2-tests');
await mkdir(output, { recursive: true });
const read = (p) => readFile(join(root, p), 'utf8');
const transpile = (source) => ts.transpileModule(source, {
  compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext,
    verbatimModuleSyntax: true }
}).outputText;
const helper = (await read('src/lib/corvus-arena.ts'))
  .replace("import { WEBUI_BASE_URL } from './constants';", "const WEBUI_BASE_URL = ''; ");
await writeFile(join(output, 'arena.mjs'), transpile(helper));
const { recordArenaPreference, savedArenaEligible, arenaMetadata, arenaTrialIdsFromSavedHistory,
  createArenaSaveQueue, acceptArenaEvent, preserveArena } =
  await import(pathToFileURL(join(output, 'arena.mjs')));
const trial = '25415702-8bac-4f1a-9dd8-5eba47de0ff4';
const fixture = () => ({ version: 1, trial_id: trial, fairness: 'BEST_EFFORT_PRE_TURN',
  main: { status: 'OK', retrieval_status: 'OK', retrieval_ms: 1, generation_ms: 1, evidence: [] },
  shadow: { status: 'OK', recall_status: 'OK', reply: 'Candidate', error_code: null,
    retrieval_ms: 1, generation_ms: 1, evidence: [] },
  evaluation: { status: 'STORED', votable: true } });
const history = () => ({ messages: { assistant: { id: 'assistant', role: 'assistant',
  model: 'corvus_pipe', content: 'Canonical answer', done: true,
  corvus_arena_requested: true, corvus_arena: fixture() } } });
const copy = (v) => JSON.parse(JSON.stringify(v));

for (const choice of ['rag', 'hindsight']) {
  test(`${choice} sends exactly one Action request and selected choice survives refresh`, async () => {
    const h = history(), calls = [];
    globalThis.fetch = async (url, init) => {
      calls.push([url, init]);
      return { ok: true, json: async () => ({ trial_id: trial, choice, marker_persisted: true }) };
    };
    const result = await recordArenaPreference('token', 'chat', 'assistant',
      h.messages.assistant.corvus_arena, h, choice);
    assert.equal(result.persisted, true);
    assert.equal(calls.length, 1);
    assert.equal(calls[0][0], '/api/chat/actions/corvus_arena_vote');
    assert.equal(calls[0][1].method, 'POST');
    assert.deepEqual(JSON.parse(calls[0][1].body), { chat_id: 'chat', message_id: 'assistant',
      trial_id: trial, choice });
    assert.equal(h.messages.assistant.corvus_arena.vote, choice);
    assert.equal(copy(h).messages.assistant.corvus_arena.vote, choice);
    assert.equal(h.messages.assistant.content, 'Canonical answer');
    assert.ok(!calls.some(([url]) => url.includes('/api/arena/chat')));
    assert.deepEqual(arenaMetadata(), {});
  });
}

test('failed vote leaves selected state and chat untouched; no save', async () => {
  const h = history(), before = copy(h); let requests = 0;
  globalThis.fetch = async () => { requests++; return { ok: false }; };
  await assert.rejects(recordArenaPreference('token', 'chat', 'assistant',
    h.messages.assistant.corvus_arena, h, 'rag'));
  assert.equal(requests, 1); assert.deepEqual(h, before);
});

test('no vote is absent; a re-vote saves the latest confirmed choice', async () => {
  const h = history(); assert.equal(h.messages.assistant.corvus_arena.vote, undefined);
  const saves = [];
  for (const choice of ['rag', 'hindsight']) {
    globalThis.fetch = async () => ({ ok: true, json: async () =>
      ({ trial_id: trial, choice, marker_persisted: true }) });
    await recordArenaPreference('token', 'chat', 'assistant', h.messages.assistant.corvus_arena,
      h, choice);
    saves.push(copy(h));
  }
  assert.equal(saves.length, 2);
  assert.equal(saves.at(-1).messages.assistant.corvus_arena.vote, 'hindsight');
});

test('saved eligibility excludes local-only and incomplete Arena messages', () => {
  const h = history(), arena = h.messages.assistant.corvus_arena;
  assert.equal(savedArenaEligible(new Set(), arena), false);
  assert.equal(savedArenaEligible(arenaTrialIdsFromSavedHistory(h), arena), true);
  h.messages.assistant.done = false;
  assert.equal(savedArenaEligible(arenaTrialIdsFromSavedHistory(h), arena), false);
  h.messages.assistant.done = true;
  delete h.messages.assistant.corvus_arena;
  assert.equal(savedArenaEligible(arenaTrialIdsFromSavedHistory(h), arena), false);
});

test('confirmed vote remains tied to original IDs after navigation', async () => {
  const h = history(); let activeChat = 'chat', request;
  globalThis.fetch = async (_, init) => {
    request = JSON.parse(init.body); activeChat = 'other';
    return { ok: true, json: async () => ({ trial_id: trial, choice: 'rag', marker_persisted: true }) };
  };
  const result = await recordArenaPreference('token', 'chat', 'assistant',
    h.messages.assistant.corvus_arena, h, 'rag');
  assert.equal(activeChat, 'other');
  assert.deepEqual([request.chat_id, request.message_id], ['chat', 'assistant']);
  assert.equal(result.persisted, true);
});

test('durable vote with failed marker persistence reports failure separately', async () => {
  const h = history(); let requests = 0;
  globalThis.fetch = async () => { requests++; return { ok: true, json: async () =>
    ({ trial_id: trial, choice: 'rag', marker_persisted: false }) }; };
  const result = await recordArenaPreference('token', 'chat', 'assistant',
    h.messages.assistant.corvus_arena, h, 'rag');
  assert.equal(requests, 1);
  assert.equal(result.persisted, false);
  assert.equal(result.arena.vote, 'rag');
});

test('marker persistence has no chat-list refresh dependency', async () => {
  const h = history();
  globalThis.fetch = async () => ({ ok: true, json: async () =>
    ({ trial_id: trial, choice: 'rag', marker_persisted: true }) });
  globalThis.getChatList = () => { throw Error('chat list unavailable'); };
  const result = await recordArenaPreference('token', 'chat', 'assistant',
    h.messages.assistant.corvus_arena, h, 'rag');
  assert.equal(result.persisted, true);
  delete globalThis.getChatList;
});

// Compile the actual panel once; integration assertions below render its real controls.
const panelSource = (await read('src/lib/components/chat/Messages/ArenaPanel.svelte'))
  .replace("'./ContentRenderer.svelte'", "'./StubContentRenderer.mjs'")
  .replace("'$lib/corvus-arena'", "'./arena.mjs'")
  .replace("'svelte-sonner'", "'./StubToast.mjs'");
await writeFile(join(output, 'StubContentRenderer.mjs'),
  `import {create_ssr_component,escape} from 'svelte/internal'; export default create_ssr_component(($$result,props)=>escape(props.content));`);
await writeFile(join(output, 'StubToast.mjs'), 'export const toast = {error:()=>{}};');
const processed = await svelte.preprocess(panelSource, { script: ({ content, attributes }) =>
  attributes.lang === 'ts' ? { code: transpile(content) } : undefined });
const compiled = svelte.compile(processed.code, { generate: 'ssr', filename: 'ArenaPanel' });
await writeFile(join(output, 'ArenaPanel.mjs'), compiled.js.code);
const Panel = (await import(pathToFileURL(join(output, 'ArenaPanel.mjs')))).default;
const renderPanel = (h, persistedArenaTrialIds) => Panel.render({
  arena: h.messages.assistant.corvus_arena, id: 'assistant', chatId: 'chat', history: h,
  readOnly: !h.messages.assistant.done, persistedArenaTrialIds }).html;

test('panel renders only votable choices, selected state and no aggregate before voting', () => {
  const h = history(), ids = arenaTrialIdsFromSavedHistory(h);
  const before = renderPanel(h, ids);
  assert.ok(before.includes('Prefer RAG') && before.includes('Prefer Hindsight'));
  assert.ok(!before.includes('Today:') && !before.includes('Canonical answer'));
  assert.ok(!before.includes('aria-pressed="true"'));
  h.messages.assistant.corvus_arena.vote = 'hindsight';
  assert.ok(renderPanel(h, ids).includes('aria-pressed="true"'));
  h.messages.assistant.corvus_arena.evaluation.votable = false;
  assert.ok(!renderPanel(h, ids).includes('Prefer RAG'));
  assert.ok(!renderPanel(history(), new Set()).includes('Prefer RAG'));
});

// Execute the actual transformed Chat declarations, including load, event,
// completion and serialized persistence. Every server call is mocked.
const chatSource = await read('src/lib/components/chat/Chat.svelte');
function declarations(names) {
  const script = chatSource.match(/<script[^>]*>([\s\S]*?)<\/script>/)[1];
  const tree = ts.createSourceFile('Chat.ts', script, ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);
  return names.map(name => {
    const statement = tree.statements.find(n => ts.isVariableStatement(n) &&
      n.declarationList.declarations.some(d => d.name.getText(tree) === name));
    assert.ok(statement, name);
    return transpile(statement.getText(tree));
  }).join('\n');
}
function integration(saved = history()) {
  const stored = new Map([['chat', { history: copy(saved) }]]), requests = [], errors = [];
  let hold, fail = false;
  const ctx = vm.createContext({
    $chatId: 'chat', chatIdProp: 'chat', history: {}, chat: null,
    $temporaryChatEnabled: false, localStorage: { token: 'test', getItem: () => null },
    selectedModels: ['corvus_pipe'], params: {}, chatFiles: [], $currentChatPage: 1,
    currentChatPage: { set() {} }, chats: { set() {} }, getChatList: async () => [],
    createMessagesList: h => Object.values(h.messages), createArenaSaveQueue,
    acceptArenaEvent, preserveArena, arenaTrialIdsFromSavedHistory,
    tick: async () => {}, scrollToBottom: async () => {}, $settings: {}, $config: {}, navigator: {}, autoScroll: false,
    getMessageContentParts: () => [], eventTarget: { dispatchEvent() {} }, CustomEvent: class {},
    $models: [{ id: 'corvus_pipe' }], $socket: { id: 'socket' }, chatCompleted: async () => null,
    toast: { error: message => errors.push(message) }, console: { log() {} }, taskIds: null,
    getChatById: async (_, id) => ({ id, chat: copy(stored.get(id)) }),
    getTagsById: async () => [], chatTitle: { set() {} }, getUserSettings: async () => null,
    settings: { set() {} }, getTaskIdsByChatId: async () => null,
    updateChatById: async (_, id, body) => {
      const snapshot = copy(body); requests.push({ id, snapshot });
      if (hold) { const gate = hold; hold = null; await gate; }
      if (fail) { fail = false; throw Error('save failed'); }
      stored.set(id, copy(snapshot)); return { id, chat: copy(snapshot) };
    }
  });
  ctx.chatId = { set: id => { ctx.$chatId = id; } };
  vm.runInContext(declarations(['arenaSaves', 'persistedArenaTrialIds', 'persistChatHistory',
    'saveChatHandler', 'chatCompletedHandler', 'chatCompletionEventHandler', 'chatEventHandler', 'loadChat']) +
    ';globalThis.load=loadChat;globalThis.onEvent=chatEventHandler;' +
    'globalThis.complete=chatCompletionEventHandler;globalThis.save=saveChatHandler;' +
    'globalThis.persisted=()=>persistedArenaTrialIds;', ctx);
  return { ctx, stored, requests, errors,
    holdNext() { let release; hold = new Promise(r => { release = r; }); return release; },
    failNext() { fail = true; },
    html: () => renderPanel(ctx.history, ctx.persisted()) };
}
const flush = async () => { for (let i = 0; i < 12; i++) await Promise.resolve(); };
const event = () => ({ chat_id: 'chat', message_id: 'assistant',
  data: { type: 'corvus:arena:v1', data: fixture() } });
const withoutArena = () => { const h = history(); delete h.messages.assistant.corvus_arena; return h; };

for (const preCompletion of [false, true]) {
  for (const failSave of [false, true]) {
    test(`${preCompletion ? 'pre' : 'post'}-completion event: controls wait for ${failSave ? 'failed' : 'successful'} persistence despite aliased history`, async () => {
      const x = integration(withoutArena()); await x.ctx.load();
      assert.equal(x.ctx.history, x.ctx.chat.chat.history); // Reproduce the real alias.
      if (preCompletion) x.ctx.history.messages.assistant.done = false;
      const release = x.holdNext(); if (failSave) x.failNext();
      let pending = x.ctx.onEvent(event());
      if (preCompletion) {
        await pending;
        assert.equal(x.requests.length, 0); // No pre-completion placeholder save.
        assert.ok(x.html().includes('Hindsight candidate'));
        assert.ok(!x.html().includes('Prefer RAG'));
        pending = x.ctx.complete({ done: true }, x.ctx.history.messages.assistant, 'chat');
      }
      await flush();
      assert.equal(x.requests.length, 1);
      assert.equal(x.ctx.chat.chat.history.messages.assistant.corvus_arena.trial_id, trial);
      assert.equal(x.ctx.persisted().has(trial), false);
      assert.ok(x.html().includes('Hindsight candidate'));
      assert.ok(!x.html().includes('Prefer RAG'));
      release();
      if (failSave && preCompletion) await assert.rejects(pending, /save failed/);
      else await pending;
      assert.equal(x.ctx.persisted().has(trial), !failSave);
      assert.equal(x.html().includes('Prefer RAG'), !failSave);
      assert.equal(x.html().includes('Prefer Hindsight'), !failSave);
      assert.equal(x.requests.length, 1); // No automatic retry.
      if (failSave) assert.equal(x.stored.get('chat').history.messages.assistant.corvus_arena, undefined);
    });
  }
}

test('refresh rebuilds eligibility only from saved server history', async () => {
  const x = integration(); await x.ctx.load();
  assert.equal(x.ctx.persisted().has(trial), true);
  assert.ok(x.html().includes('Prefer RAG'));
  delete x.stored.get('chat').history.messages.assistant.corvus_arena;
  await x.ctx.load();
  assert.equal(x.ctx.persisted().has(trial), false);
  acceptArenaEvent(x.ctx.history, event(), 'chat');
  assert.equal(x.ctx.history, x.ctx.chat.chat.history);
  assert.ok(x.html().includes('Hindsight candidate'));
  assert.ok(!x.html().includes('Prefer RAG'));
});

test('a successful earlier snapshot cannot certify an association added while its save was pending', async () => {
  const x = integration(withoutArena()); await x.ctx.load();
  const release = x.holdNext(), saving = x.ctx.save('chat', x.ctx.history);
  await flush();
  acceptArenaEvent(x.ctx.history, event(), 'chat');
  release(); await saving;
  assert.equal(x.ctx.persisted().has(trial), false);
  assert.ok(!x.html().includes('Prefer RAG'));
  await x.ctx.save('chat', x.ctx.history);
  assert.ok(x.html().includes('Prefer RAG'));
});

test('a successful old-chat save cannot make local Arena state in the new chat eligible', async () => {
  const x = integration(withoutArena()); await x.ctx.load();
  acceptArenaEvent(x.ctx.history, event(), 'chat');
  const release = x.holdNext(), saving = x.ctx.save('chat', x.ctx.history);
  await flush();
  x.stored.set('other', { history: withoutArena() }); x.ctx.chatIdProp = 'other';
  await x.ctx.load();
  release(); await saving;
  acceptArenaEvent(x.ctx.history, { ...event(), chat_id: 'other' }, 'other');
  assert.equal(x.ctx.persisted().has(trial), false);
  assert.ok(!x.html().includes('Prefer RAG'));
});
