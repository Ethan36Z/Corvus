"""Incremental packaging of the pinned, already built Lab Vision frontend.

No dependency installation or application recompile. Change only three compiled
size constants and the existing optional resize branch. Move affected JS/import
parents to fresh URLs; preserve all other STT/TTS/Arena/branding asset bytes.
"""
import argparse, hashlib, json, pathlib, re, shutil
PIN = 'e2b30c49e2fa5b901f69cf73e27df4a245b8f48e1178c5f25046d25528db0686'
CHUNK = 'CD_kXMG7.js'

def package(source, output):
    source, output = pathlib.Path(source), pathlib.Path(output)
    assert not output.exists(), 'Output must be new'
    original = source / '_app/immutable/chunks' / CHUNK
    assert hashlib.sha256(original.read_bytes()).hexdigest() == PIN, 'Working Lab asset pin mismatch'
    js = original.read_text()
    assert js.count('6*1024*1024') == 3 and js.count('up to 6 MiB') == 2
    js = js.replace('6*1024*1024', '20*1024*1024').replace('up to 6 MiB', 'up to 20 MiB')
    resize = r'if\(\(r==null\?void 0:r\.imageCompression\)\?\?!1\)\{.*?\(ao\|\|\$\)\&\&\(Ht=await Mm\(Ht,ao,\$\)\)\}'
    js, n = re.subn(resize, '', js)
    assert n == 1, 'Pinned optional image compression branch mismatch'
    # Find all import parents before renaming; no stale immutable URL may point
    # at changed code. Names are versioned rather than claiming Vite hashes.
    scripts = {str(p.relative_to(source)):p.read_text() for p in source.rglob('*.js')}
    affected = {str(original.relative_to(source))}
    while True:
        names = {pathlib.Path(p).name for p in affected}
        new = {p for p, text in scripts.items() if any(n in text for n in names)}
        if new <= affected: break
        affected |= new
    names = {pathlib.Path(p).name:pathlib.Path(p).stem+'-vision20.js' for p in affected}
    assert len(names) == len(affected)
    shutil.copytree(source, output)
    changed = []
    for p in list(output.rglob('*')):
        if not p.is_file() or p.suffix not in {'.js','.map','.html','.json'}: continue
        rel = str(p.relative_to(output)); text = js if rel == str(original.relative_to(source)) else p.read_text()
        if rel == str(original.relative_to(source))+'.map':
            d = json.loads(text)
            for i, (name, content) in enumerate(zip(d['sources'], d['sourcesContent'])):
                if name.endswith('/corvus-vision.ts'):
                    assert content.count('6 * 1024 * 1024') == 1
                    d['sourcesContent'][i] = content.replace('6 * 1024 * 1024','20 * 1024 * 1024')
                elif name.endswith('/MessageInput.svelte'):
                    assert content.count('6 * 1024 * 1024') == 2
                    content = content.replace('6 * 1024 * 1024','20 * 1024 * 1024').replace('up to 6 MiB','up to 20 MiB')
                    content,n = re.subn(r'\n\t{5}if \(\$settings\?\.imageCompression \?\? false\) \{.*?\n\t{5}\}', '', content, flags=re.S)
                    assert n == 1
                    d['sourcesContent'][i] = content
            # Original generated columns are no longer valid after incremental
            # edits. Keep reviewable sources, explicitly omit stale mappings.
            d['mappings'] = ''; text = json.dumps(d, separators=(',',':'))
        for old,new in names.items(): text = text.replace(old,new)
        if rel == '_app/version.json':
            v = json.loads(text);v['version'] += '-vision20';text = json.dumps(v)
        if text != p.read_text(): p.write_text(text);changed.append(rel)
    for rel in affected:
        p = output/rel;new = p.with_name(names[p.name]);p.rename(new)
        if pathlib.Path(str(p)+'.map').exists():pathlib.Path(str(p)+'.map').rename(pathlib.Path(str(new)+'.map'))
    for p in output.rglob('*'):
        if p.is_file() and p.suffix in {'.js','.html','.json'}:
            assert not any(old in p.read_text() for old in names), 'Stale asset reference'
    print(json.dumps({'incremental_js':len(affected),'changed_files':changed,'entry_chunk':names[CHUNK]}))

if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('output');a=p.parse_args();package(a.source,a.output)
