"""Apply narrow, pinned native WebUI changes to a NEW isolated source directory.

No builds, downloads, runtime configuration or deployed source changes.
"""
import ast
import hashlib
from pathlib import Path
import shutil
import sys

PINS = {
    'src/lib/components/chat/Chat.svelte': '8d1cac9a7cf676e7275747df6d55d31d55bc45660819c48b1770b2ff2c4eadcd',
    'src/lib/components/chat/MessageInput.svelte': '09cf2906f768a8d3a343b26a7adc235f7769814c7765cde117ab7abf6f1d88d0',
    'backend/open_webui/models/files.py': '0dc93c0ea941289afd161938778cafdcbe3c160e907ebc513a1d73f4f286fdec',
    'backend/open_webui/models/chats.py': '67d94bd7732af53c431f82da34d83d6c11a7d99e6cff2513075476830f5860fd',
    'backend/open_webui/routers/chats.py': '82d079a8cf3f1ad8bcaab57fe809e9a44753edecf0517f44ee5b3a359122ba15',
    'backend/open_webui/routers/files.py': 'f2cb5ef17326d68140cb5f138abf0b4d18adbeb4f80f9ed9699cfa937f3c9ffd',
}


def once(source, before, after):
    if source.count(before) != 1:
        raise ValueError('Pinned source anchor mismatch')
    return source.replace(before, after, 1)


def patch_chats(source):
    source = once(source, '                chat_item.chat = chat', '''                from open_webui.routers.corvus_vision import validate_chat
                validate_chat(db, chat_item.user_id, id, chat)
                chat_item.chat = chat''')
    # Both initial creation and import/clone must be reference-free. Owned image
    # operations begin only once the server has created a real chat and message.
    before = '            id = str(uuid.uuid4())'
    assert source.count(before) == 2
    source = source.replace(before, '''            from open_webui.routers.corvus_vision import validate_chat
            validate_chat(db, user_id, None, form_data.model_dump(), transfer=True)
''' + before)
    before = '            # Check if the chat is already shared'
    source = once(source, before, '''            from open_webui.routers.corvus_vision import validate_chat
            validate_chat(db, chat.user_id, chat_id, chat.chat, transfer=True)
''' + before)
    source = once(source, '                shared_chat.title = chat.title', '''                from open_webui.routers.corvus_vision import validate_chat
                validate_chat(db, chat.user_id, chat_id, chat.chat, transfer=True)
                shared_chat.title = chat.title''')
    return source


def patch_file_model(source):
    before = '                file = db.query(File).filter_by(id=id).first()'
    assert source.count(before) == 3
    source = source.replace(before, before + '''
                from open_webui.routers.corvus_vision import protect_file
                protect_file(file)''')
    source = once(source, '                db.query(File).filter_by(id=id).delete()', '''                from open_webui.routers.corvus_vision import protect_file
                protect_file(db.get(File, id))
                db.query(File).filter_by(id=id).delete()''')
    source = once(source, '                db.query(File).delete()', '''                from open_webui.routers.corvus_vision import protect_file
                for file in db.query(File).all():
                    protect_file(file)
                db.query(File).delete()''')
    # Generic insert cannot forge a protected provider record.
    source = once(source, '            file = FileModel(', '''            if (form_data.meta or {}).get("provider") == "corvus-vision-v1":
                raise ValueError("Reserved image provider")
            file = FileModel(''')
    return source


def patch_chat_router(source):
    before = '    if chat.user_id != user.id and user.role != "admin":'
    if source.count(before) != 2:
        raise ValueError('Pinned chat message mutation routes mismatch')
    return source.replace(before, """    from open_webui.routers.corvus_vision import mutation_actor
    mutation_actor(chat, user, form_data.model_dump())

""" + before)


def patch_file_router(source):
    # Route wrapper runs BEFORE FastAPI multipart parsing/spooling; the generic
    # uploader is unavailable while this image-only Lab integration is enabled.
    source = once(source, 'router = APIRouter()', '''from fastapi.routing import APIRoute
from open_webui.routers import corvus_vision

class ImageOnlyRoute(APIRoute):
    def get_route_handler(self):
        original = super().get_route_handler()
        async def guarded(request):
            if request.method == "POST" and request.url.path.rstrip("/") == "/api/v1/files":
                raise HTTPException(403, "Generic file storage is disabled for private images")
            return await original(request)
        return guarded

router = APIRouter(route_class=ImageOnlyRoute)
router.include_router(corvus_vision.router)''')
    source = once(source, "async def delete_file_by_id(id: str, user=Depends(get_verified_user)):",
                  "async def delete_file_by_id(id: str, request: Request, user=Depends(get_verified_user)):")
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)
    inserts = []
    for function in ast.walk(tree):
        if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        routes = [ast.unparse(d) for d in function.decorator_list]
        for node in ast.walk(function):
            if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call):
                continue
            if ast.unparse(node.value.func) != 'Files.get_file_by_id' or ast.unparse(node.targets[0]) != 'file':
                continue
            indent = ' ' * node.col_offset
            if any(d.startswith("router.get('/{id}/content')") for d in routes):
                action = 'return await corvus_vision.content(id, user)'
            elif any(d.startswith("router.delete('/{id}')") for d in routes):
                action = 'corvus_vision.bearer_mutation(request)\n' + indent + '    return corvus_vision.revoke(id, user)'
            else:
                action = 'raise HTTPException(404, "Image metadata is private")'
            inserts.append((node.end_lineno, indent + 'if corvus_vision.is_reference(file):\n' + indent + '    ' + action + '\n'))
    for line, code in sorted(inserts, reverse=True):
        lines.insert(line, code)
    return ''.join(lines)


def patch_composer(source):
    source = once(source, "['image/gif', 'image/webp', 'image/jpeg', 'image/png', 'image/avif']", "['image/jpeg', 'image/png']")
    source = once(source, '\t\t\t\tuploadFileHandler(file);', '''                toast.error($i18n.t('Use one PNG/JPEG image.'));''')
    source = once(source, "\t\tinputFiles.forEach((file) => {", """        inputFiles.forEach((file) => {
            if (file.size > 20 * 1024 * 1024 || inputFiles.length !== 1 || files.some((item) => item.type === 'image')) {
                toast.error($i18n.t('Use one PNG/JPEG image up to 20 MiB.')); return;
            }""")
    # Paste uses the SAME native selection handler and bounds, not another uploader.
    import re
    pattern = r"const blob = item.getAsFile\(\);\s*const reader = new FileReader\(\);.*?reader.readAsDataURL\(blob\);"
    source, count = re.subn(pattern, "const blob = item.getAsFile(); if (blob) inputFilesHandler([blob]);", source, flags=re.S)
    if count != 2:
        raise ValueError('Pinned native paste paths mismatch')
    # Enforce after async FileReader as well as at selection (racing selections).
    source = once(source, '\t\t\t\t\tlet imageUrl = event.target.result;', '''                    if (files.some((item) => item.type === 'image') || file.size > 20 * 1024 * 1024) {
                        toast.error($i18n.t('Use one PNG/JPEG image up to 20 MiB.'));
                        return;
                    }
                    let imageUrl = event.target.result;''')
    # Single-store Vision preserves the original selected bytes regardless of
    # the native optional compression preference.
    import re
    source, count = re.subn(
        r"\n\t{5}if \(\$settings\?\.imageCompression \?\? false\) \{.*?\n\t{5}\}",
        "", source, flags=re.S)
    if count != 1:
        raise ValueError('Pinned native compression anchor mismatch')
    return source


def patch_chat(source):
    source = once(source, "<script lang=\"ts\">", '''<script lang="ts">
    import { imageDraft, persistentDraft, uploadImage, reconcileImage } from '$lib/utils/corvus-vision';
    let imageController: AbortController | null = null;
    let imageUploadChatId = '';
    // Keep controller state out of the chatIdProp reactive dependency set.
    const cancelImageUploadForChat = (nextChatId: string) => {
        if (nextChatId !== imageUploadChatId) imageController?.abort();
    };
''')
    source = once(source, '\t\tprompt = \'\';\n\n\t\t// Reset chat input textarea', '''        let visionDraft: Blob | null = null;
        try { visionDraft = imageDraft(files, arenaForTurn); }
        catch { toast.error($i18n.t('Use one PNG/JPEG image without Arena.')); return; }
        if (visionDraft && (!userPrompt.trim() || $temporaryChatEnabled || selectedModels.length !== 1 || selectedModels[0] !== 'corvus_pipe' || (atSelectedModel && atSelectedModel.id !== 'corvus_pipe') || selectedToolIds.length || webSearchEnabled || imageGenerationEnabled || codeInterpreterEnabled)) {
            toast.error($i18n.t('Select Corvus for image input.')); return;
        }
        prompt = '';

        // Reset chat input textarea''')
    source = once(source, '\t\tconst _files = JSON.parse(JSON.stringify(files));', '''        const _files = visionDraft ? [] : JSON.parse(JSON.stringify(files));''')
    source = once(source, '\t\t\tfiles: _files.length > 0 ? _files : undefined,', '''            files: _files.length > 0 ? _files : undefined,
            ...(visionDraft ? { corvus_image_pending: true } : {}),''')
    source = once(source, '{ newChat: true, corvusArena: arenaForTurn }', '{ newChat: true, corvusArena: arenaForTurn, visionDraft }')
    source = once(source, '{ modelId = null, modelIdx = null, newChat = false, corvusArena = false } = {}', '{ modelId = null, modelIdx = null, newChat = false, corvusArena = false, visionDraft = null as Blob | null } = {}')
    before = '\t\tawait saveChatHandler(_chatId, _history);\n\n\t\tawait Promise.all('
    source = once(source, before, '''        await saveChatHandler(_chatId, _history);
        if (visionDraft) {
            const controller = new AbortController();
            imageController?.abort(); imageController = controller;
            imageUploadChatId = _chatId;
            const timer = setTimeout(() => controller.abort(), 30000);
            try {
                const reference = await uploadImage(localStorage.token, _chatId, parentId, visionDraft, controller.signal);
                if (controller.signal.aborted || $chatId !== _chatId) {
                    Object.values(responseMessageIds).forEach((id) => { if (history.messages[id]) history.messages[id].done = true; });
                    history = history;
                    return;
                }
                history.messages[parentId].files = [reference];
                delete history.messages[parentId].corvus_image_pending;
                _history = JSON.parse(JSON.stringify(history));
                await saveChatHandler(_chatId, _history);
                if (controller.signal.aborted || $chatId !== _chatId) {
                    Object.values(responseMessageIds).forEach((id) => { if (history.messages[id]) history.messages[id].done = true; });
                    history = history;
                    return;
                }
            } catch {
                // Keep the saved pending turn; status reconciliation is manual,
                // never a second canonical dispatch or automatic upload retry.
                toast.error($i18n.t('Image upload not confirmed. This turn was not sent.'));
                Object.values(responseMessageIds).forEach((id) => { if (history.messages[id]) history.messages[id].done = true; });
                history = history;
                return;
            } finally {
                clearTimeout(timer);
                if (imageController === controller) {
                    imageController = null;
                    imageUploadChatId = '';
                }
            }
        }

        await Promise.all(''')
    # The Pipe resolves the real owned user parent server-side. Every model
    # message remains text-only; no historical image is re-submitted.
    start = source.index("\t\t\t\t...((message.files?.filter((file) => file.type === 'image')")
    end = source.index('\n\t\t\t}))', start)
    source = source[:start] + '\t\t\t\tcontent: message?.merged?.content ?? message.content' + source[end:]
    source = once(source, 'JSON.stringify(input));', 'JSON.stringify(persistentDraft(input)));')
    source = once(source, '\tonDestroy(() => {', '\tonDestroy(() => {\n        imageController?.abort();')
    source = once(source, '\tconst stopResponse = async () => {', '\tconst stopResponse = async () => {\n        imageController?.abort();')
    source = once(source, "\t$: if (chatIdProp) {", "\t$: if (chatIdProp) {\n        cancelImageUploadForChat(chatIdProp);")
    # Discard legacy raw drafts on restoration, without writing or migrating them.
    source = source.replace('files = input.files;', "files = (input.files ?? []).filter((file) => file.type !== 'image');")
    return patch_image_reference_order(source)




def patch_image_reference_order(source):
    # Default calls keep Arena's capture-of-current-history semantics. Only the
    # upload's reference commit passes a staged snapshot, before it is rendered.
    source = once(source, 'const persistChatHistory = (token, id, body) => {',
        'const persistChatHistory = (token, id, body, snapshotHistory = history) => {')
    source = once(source, '...body, history,\n\t\t\tmessages: createMessagesList(history, history.currentId)',
        '...body, history: snapshotHistory,\n\t\t\tmessages: createMessagesList(snapshotHistory, snapshotHistory.currentId)')
    source = once(source, 'const saveChatHandler = async (_chatId, history) => {',
        'const saveChatHandler = async (_chatId, history, snapshotHistory = undefined) => {')
    start = source.index('const saveChatHandler = async ')
    source = source[:start] + once(source[start:], 'files: chatFiles\n\t\t\t\t});',
        'files: chatFiles\n\t\t\t\t}, snapshotHistory);')
    source = once(source, """                history.messages[parentId].files = [reference];
                delete history.messages[parentId].corvus_image_pending;
                _history = JSON.parse(JSON.stringify(history));
                await saveChatHandler(_chatId, _history);""", """                // Commit the authorized reference before the native Image mounts.
                _history = JSON.parse(JSON.stringify(history));
                _history.messages[parentId].files = [reference];
                delete _history.messages[parentId].corvus_image_pending;
                await saveChatHandler(_chatId, _history, _history);""")
    source = once(source, """                    history = history;
                    return;
                }
            } catch {""", """                    history = history;
                    return;
                }
                // Preserve concurrent live messages; publish only this user turn.
                history.messages[parentId] = { ...history.messages[parentId], files: [reference] };
                delete history.messages[parentId].corvus_image_pending;
                history = history;
                _history = JSON.parse(JSON.stringify(history));
            } catch {""")
    return source


def patch_pipe(source):
    source = once(source, 'import math\n', 'import math\nimport os\n')
    source = once(source, '        payload = {', """        vision_turn = None
        if os.getenv("CORVUS_SINGLE_STORE_VISION") == "offline-reviewed-v1":
            if chat_url != "http://127.0.0.1:18096/api/chat":
                raise ValueError("Vision requires the fixed Lab target")
            from open_webui.routers import corvus_vision
            vision_turn = corvus_vision.current_image(
                user_id, chat_id, (__metadata__ or {}).get("message_id"),
                current["content"], arena_flag,
            )

        payload = {""")
    source = once(source, '        if arena_flag:\n            chat_url =', """        if vision_turn:
            payload["attachment_id"] = vision_turn[1]
        if arena_flag:
            chat_url =""")
    start = source.index('        # No redirects, environment proxies')
    dispatch = once(source[start:], '        return reply\n', """        if vision_turn:
            corvus_vision.finish(vision_turn[0], result)
        return reply
""")
    return source[:start] + '        try:\n' + ''.join(
        '    ' + line if line.strip() else line for line in dispatch.splitlines(keepends=True)
    ) + """        finally:
            if vision_turn:
                corvus_vision.finish(vision_turn[0])
"""


def prepare(frontend, backend, target):
    frontend, backend, target = map(Path, (frontend, backend, target))
    if target.exists():
        raise ValueError('Target must be a new isolated directory')
    sources = {}
    for relative, digest in PINS.items():
        path = (backend if relative.startswith('backend/') else frontend) / relative
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != digest:
            raise ValueError('Source pin mismatch: ' + relative)
        sources[relative] = data.decode()
    patches = [patch_chat, patch_composer, patch_file_model, patch_chats, patch_chat_router, patch_file_router]
    output = {path: patch(data) for (path, data), patch in zip(sources.items(), patches)}
    pipe = (Path(__file__).parent / 'corvus_pipe.py').read_bytes()
    if hashlib.sha256(pipe).hexdigest() != '68967bd0ed499aaf2ecce38bc6afc80c3fc3cdeb805aab6a57182a2e907af861':
        raise ValueError('Actual Lab Pipe source pin mismatch')
    output['deploy/open-webui/corvus_pipe.py'] = patch_pipe(pipe.decode())
    # Syntax check all generated backend source before creating any output.
    for path, data in output.items():
        if path.endswith('.py'):
            ast.parse(data)
    for path, data in output.items():
        dest = target / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(data)
    here = Path(__file__).parent
    for origin, relative in [('vision.py', 'backend/open_webui/routers/corvus_vision.py'), ('vision.ts', 'src/lib/utils/corvus-vision.ts')]:
        dest = target / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(here / origin, dest)
    return target

if __name__ == '__main__':
    prepare(*sys.argv[1:])
