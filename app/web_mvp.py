"""Progressive Web presentation over the existing W2 retrieval collector.

No persistence, personal recall, model calls, event emission, or new pipeline.
"""
from dataclasses import dataclass, replace
from time import perf_counter
import re
from urllib.parse import quote

from app.searxng_provider import SearXNGProvider
from app.web_acceptance import (
    EvidenceRequirements, accept_web_evidence, canonical_url,
    searxng_failures, source_identity, source_map,
)


@dataclass(frozen=True)
class MVPSource:
    url: str
    identity: str
    refs: tuple[str, ...] = ()
    verification: str = "FETCHED_EXTRACTED"


@dataclass(frozen=True)
class MVPPreparation:
    status: str
    outcome: str
    evidence_status: str
    missing: tuple[str, ...]
    sources: tuple[MVPSource, ...]
    used_web_evidence: tuple = ()
    selected_result_id: str | None = None
    deterministic_reply: str | None = None
    retrieval_status: str = "NOT_RUN"
    answer_basis: str | None = None
    timings: dict | None = None  # diagnostics only (W2-a); never persisted


def _chinese(text):
    return any('\u3400' <= ch <= '\u9fff' for ch in text)


def source_section(sources, *, chinese=False, concise=False):
    """Only validated retrieval URLs; no source titles or model-provided links."""
    lines = ['\n\n来源（已抓取页面，完整性和时效性另见说明）：' if chinese else
             '\n\nSources (pages fetched; coverage and freshness may remain limited):']
    if concise:
        lines = ['\n\n来源：' if chinese else '\n\nSources:']
    for i, source in enumerate(sources, 1):
        url = canonical_url(source.url)
        if source.identity != source_identity(url):
            raise ValueError('Source identity mismatch')
        # Escape Markdown delimiters in the destination; labels are fixed text.
        destination = quote(url, safe=":/?#@!$&'*+,;=%~.-_")
        if any(re.fullmatch(r'web_[1-9][0-9]*', ref) is None for ref in source.refs):
            raise ValueError('Invalid source reference')
        refs = ' / '.join(source.refs)
        label = f"来源 {i}" if chinese else f"Source {i}"
        lines.append(f"- [{label}](<{destination}>)" + (f" — {refs}" if refs else ''))
    return '\n'.join(lines) if sources else ''


def _fallback(query, sources, code, *, failed=False, missing=()):
    zh = _chinese(query)
    if failed:
        if code == 'NO_RESULTS':
            text = '搜索未返回结果，无法确认当前信息。' if zh else 'Search returned no results. No current information was verified.'
        else:
            text = '本次网页检索未能完成或未获得可核验的页面，无法确认当前信息。' if zh else 'Web retrieval failed or yielded no verifiable page. No current information was verified.'
    else:
        text = ('以下仅提供已抓取的来源链接；尚未确认内容是否完整、最新，或满足所需版本、日期等条件。未据此生成事实性答案。'
                if zh else 'Here are fetched source pages for review. Completeness, freshness, and requested version/date coverage have not all been verified. No factual answer was generated from this partial evidence.')
    if not failed:
        notes = []
        if any(code.startswith('version:') or code == 'source_version' for code in missing):
            notes.append('所需来源版本未确认。' if zh else 'Requested source versions were not verified.')
        if any('publication' in code for code in missing):
            notes.append('所需发布日期或日期范围未确认。' if zh else 'The requested publication date/window was not verified.')
        if any(code.startswith('sources:') or code == 'separate_version_sources' for code in missing):
            notes.append('所需的独立来源覆盖不完整。' if zh else 'Required distinct-source coverage is incomplete.')
        if 'provider_partial_failure' in missing:
            notes.append('部分搜索服务失败，来源覆盖可能不完整。' if zh else 'Some search-provider work failed; source coverage may be incomplete.')
        if 'requirements_not_specified' in missing:
            notes.append('未提供明确的逐项证据要求。' if zh else 'Question-specific evidence requirements were not supplied.')
        if notes:
            text += '\n\n' + ' '.join(notes)
    return text + source_section(sources, chinese=zh)


def failed_preparation(query, code='WEB_PREPARATION_FAILED'):
    return MVPPreparation(code, 'SEARCH_FAILED', 'EVIDENCE_INSUFFICIENT',
                          (code,), (), deterministic_reply=_fallback(query, (), code, failed=True),
                          retrieval_status=code)


def _timed(fn, bucket):
    def wrapper(*args, **kwargs):
        started = perf_counter()
        try:
            return fn(*args, **kwargs)
        finally:
            bucket.append(round((perf_counter() - started) * 1000, 1))
    return wrapper


def prepare_web_mvp(query, *, provider_builder, requirements=None,
                    source_facts=lambda page: None, **collector_options):
    """Run the bounded Web MVP retrieval and record stage timings (W2-a).

    Timing wraps existing injection points only; behaviour is unchanged.
    """
    from app.web_extract import extract_web_page
    from app.web_search_fetch import fetch_search_result

    timings = {"search_ms": [], "fetch_ms": [], "extract_ms": []}

    def timed_builder(attempt):
        provider = provider_builder(attempt)
        if callable(getattr(provider, "search", None)):
            provider.search = _timed(provider.search, timings["search_ms"])
        return provider

    options = dict(collector_options)
    options["fetch_search_result_fn"] = _timed(
        options.get("fetch_search_result_fn", fetch_search_result), timings["fetch_ms"])
    options["extract_web_page_fn"] = _timed(
        options.get("extract_web_page_fn", extract_web_page), timings["extract_ms"])
    started = perf_counter()
    prepared = _prepare_web_mvp(
        query, provider_builder=timed_builder, requirements=requirements,
        source_facts=source_facts, **options,
    )
    total = round((perf_counter() - started) * 1000, 1)
    timings["retrieval_ms"] = total
    timings["evidence_ms"] = round(max(0.0, total - sum(
        sum(timings[k]) for k in ("search_ms", "fetch_ms", "extract_ms"))), 1)
    return replace(prepared, timings=timings)


# W2-r: request wording is not a search topic ("请联网核实你刚才关于 X 的说法").
_REQUEST_PREFIX = re.compile(
    r'^\s*(?:请|麻烦|帮我|帮忙)?\s*(?:你)?\s*(?:联网|上网|在网上)?\s*'
    r'(?:核实|核查|查一下|查查|搜索一下|搜一下|确认)(?:一下)?\s*[:：,，]?\s*'
    r'|^\s*(?:please\s+)?(?:search\s+(?:the\s+web\s+)?for|look\s+up|verify|fact[- ]check)\s*[:,]?\s+',
    re.IGNORECASE,
)
_SELF_REFERENCE = re.compile(r'你(?:刚才|之前|刚刚|上面)(?:说的|提到的|的说法|的回答)?(?:关于)?')
_CLAIM_SUFFIX = re.compile(r'(?:的说法|的回答|是否属实|对不对|是不是真的)\s*[。？?！!.]*\s*$')


# --- W2-b relevance gate (unspecified requests only) -------------------------
# Built only from the existing ranker's output for the passages actually
# selected as evidence. It answers "can this page plausibly answer?", not
# "is the answer true": a long, on-topic page that misses the point can pass.
MIN_EVIDENCE_CHARS = 400
_GENERIC_ANCHORS = {
    "new", "latest", "current", "recent", "best", "version", "versions", "release",
    "releases", "feature", "features", "vs", "versus", "difference", "differences",
    "between", "compare", "with", "which", "it", "this", "that", "can", "should",
}


def _query_terms(query):
    from app.web_passages import lexical_terms

    terms = lexical_terms(query)
    anchors = [t for t in dict.fromkeys(terms)
               if re.search(r'[a-z0-9]', t) and t not in _GENERIC_ANCHORS]
    bigrams = {t for t in terms if len(t) == 2 and all('㐀' <= c <= '鿿' for c in t)}
    return anchors, bigrams


def relevance_gate(query):
    anchors, bigrams = _query_terms(query)

    def check(page, ranked, evidence):
        if sum(len(e.excerpt) for e in evidence) < MIN_EVIDENCE_CHARS:
            return 'thin_evidence'  # index/navigation/title-only pages
        selected = {e.passage_id for e in evidence}
        used = [r for r in ranked if r.passage.passage_id in selected]
        matched = set().union(*(r.matched_terms for r in used)) if used else set()
        if anchors:
            absent = [a for a in anchors if a not in matched]
            if len(absent) > (1 if len(anchors) >= 3 else 0):
                return 'relevance'
        elif not any(r.exact_phrase_match for r in used) and len(bigrams & matched) < 2:
            return 'relevance'
        return None
    return check


TOTAL_EVIDENCE_CHARS = 3600  # unchanged overall evidence budget


def _full_budget_if_single_source(accepted, query):
    """W2-c: one qualifying source gets the whole budget, not half of it.

    Re-runs the existing passage build/rank/select on the same page; the
    evidence can only grow from that page and is renumbered from web_1.
    """
    if len(accepted.sources) != 1:
        return accepted
    from app.web_evidence_select import select_used_web_evidence
    from app.web_passages import build_web_passages, rank_web_passages

    source = accepted.sources[0]
    ranked = rank_web_passages(query, build_web_passages(source.page))
    evidence = select_used_web_evidence(source.page, ranked, max_total_chars=TOTAL_EVIDENCE_CHARS)
    if sum(len(e.excerpt) for e in evidence) <= sum(len(e.excerpt) for e in source.evidence):
        return accepted
    evidence = tuple(replace(e, ordinal=i, evidence_ref=f"web_{i + 1}")
                     for i, e in enumerate(evidence))
    return replace(accepted, sources=(replace(source, evidence=evidence),), evidence=evidence)


def clean_search_query(query):
    """Strip request phrasing; keep the original if too little topic remains."""
    cleaned = _REQUEST_PREFIX.sub('', query, count=1)
    cleaned = _SELF_REFERENCE.sub('', cleaned)
    cleaned = _CLAIM_SUFFIX.sub('', cleaned).strip(' ，,。:：')
    return cleaned if len(cleaned) >= 4 else query


def _prepare_web_mvp(query, *, provider_builder, requirements=None,
                     source_facts=lambda page: None, **collector_options):
    """Explicit constraints establish sufficiency; otherwise use selected evidence.

    SourceFacts is server-supplied; clients cannot assert trusted page metadata.
    """
    failures = []
    def builder(attempt):
        provider = provider_builder(attempt)
        if isinstance(provider, SearXNGProvider):
            previous = provider.diagnostics_callback
            def diagnostics(payload):
                if previous is not None:
                    previous(payload)
                failures.extend(searxng_failures(payload))
            provider.diagnostics_callback = diagnostics
        return provider

    req = requirements if requirements is not None else EvidenceRequirements()
    if not isinstance(req, EvidenceRequirements):
        raise TypeError('Explicit EvidenceRequirements required')
    # Domain/source count alone does not establish factual question coverage.
    explicit = requirements is not None and bool(
        req.versions or req.require_publication_date or req.publication_date
        or req.publication_window or req.required_text
    )
    search_query = clean_search_query(query)
    if not explicit:
        # W2-c: prefer two distinct qualifying sources, never require them.
        req = replace(req, min_sources=max(req.min_sources, 2))
    accepted = accept_web_evidence(
        search_query, requirements=req, provider_builder=builder,
        source_facts=source_facts, provider_failures=lambda: tuple(failures),
        candidate_relevance=None if explicit else relevance_gate(search_query),
        **collector_options,
    )
    if not explicit:
        accepted = _full_budget_if_single_source(accepted, search_query)
        accepted = replace(accepted, missing=tuple(
            m for m in accepted.missing if not m.startswith('sources:')))
    sufficient = (explicit and accepted.evidence_status == 'EVIDENCE_SUFFICIENT'
                  and not accepted.provider_failures)
    if sufficient or (not explicit and accepted.evidence):
        missing = () if explicit else ('requirements_not_specified',)
        if not explicit and len(accepted.sources) == 1:
            missing += ('single_source',)
        if accepted.provider_failures:
            missing += ('provider_partial_failure',)
        return MVPPreparation(
            accepted.technical_status, 'GROUNDED_ANSWER',
            accepted.evidence_status if explicit else 'EVIDENCE_RETRIEVED',
            missing, _answer_sources(accepted), accepted.evidence,
            accepted.grounding.selected_result_id,
            retrieval_status=accepted.retrieval_status,
            answer_basis='EXPLICIT_REQUIREMENTS' if explicit else 'RETRIEVED_EVIDENCE',
        )

    sources = []
    # Only actual extracted pages can become fallback links. Never expose an
    # unfetched hit, search snippet, personal memory, or discarded backend error.
    for page in accepted.observed_pages:
        url = canonical_url(page.fetched_url)
        identity = source_identity(url)
        if not any(s.identity == identity for s in sources):
            sources.append(MVPSource(url, identity))
        if len(sources) == 2:
            break
    missing = accepted.missing or ('question_coverage_not_verified',)
    if accepted.provider_failures:
        missing += ('provider_partial_failure',)
    if not explicit:
        missing = ('requirements_not_specified',) + missing
    if sources:
        return MVPPreparation(accepted.technical_status, 'SOURCES_WITH_LIMITATIONS',
                              'EVIDENCE_INSUFFICIENT', missing, tuple(sources),
                              deterministic_reply=_fallback(query, tuple(sources), 'PARTIAL', missing=missing),
                              retrieval_status=accepted.retrieval_status)
    return failed_preparation(query, accepted.retrieval_status)


def _answer_sources(accepted):
    sources = []
    for entry in source_map(accepted):
        index = next((i for i, s in enumerate(sources) if s.identity == entry.source_identity), None)
        if index is None:
            sources.append(MVPSource(entry.url, entry.source_identity, (entry.evidence_ref,)))
        else:
            old = sources[index]
            sources[index] = MVPSource(old.url, old.identity, old.refs + (entry.evidence_ref,))
    return tuple(sources)


# Fenced blocks (including an unfinished final block) and same-line backtick spans.
_CODE = re.compile(
    r'(?m:^ {0,3}(`{3,})[^\n]*\n[\s\S]*?'
    r'(?:^ {0,3}\1`*[ \t]*(?=\n|$)|\Z))'
    r'|(?<!`)(`+)(?!`)[^\n]*?(?<!`)\2(?!`)'
)
_URL = re.compile(r'(?i)(?:[a-z][a-z0-9+.-]*://|www\.)[^\s<>`"\[\]]+')


def _filter_grounded_answer(answer, prepared, *, chinese=False):
    """Pure presentation filter; counts citations only in prose, never code."""
    if not isinstance(answer, str) or not answer.strip():
        raise ValueError('Empty grounded answer')
    refs = {ref for source in prepared.sources for ref in source.refs}
    urls = {canonical_url(source.url) for source in prepared.sources}
    kept = removed = 0

    def citation(match):
        nonlocal kept, removed
        if match[1] in refs:
            kept += 1
            return match[0]
        removed += 1
        return ''

    def url(match):
        # Sentence punctuation is not part of a bare URL.
        candidate = match[0].rstrip('.,;:!?)}，。；！？”')
        suffix = match[0][len(candidate):]
        for value in (match[0], candidate):
            try:
                if canonical_url(value) in urls:
                    return match[0]
            except ValueError:
                pass
        return ('[链接已移除]' if chinese else '[link removed]') + suffix

    def prose(text):
        text = re.sub(r'!?\[([^\]\n]*)\]\([^\n]*?\)', r'\1', text)
        text = re.sub(r'(?m)^\s*\[[^\]\n]+\]:[^\n]*$', '', text)
        text = text.replace('](', ']\\(').replace('<', '&lt;')
        return re.sub(r'\[(web_\d+|\d+)\]', citation, text)

    parts = []
    cursor = 0
    for match in _CODE.finditer(answer):
        parts.extend((prose(answer[cursor:match.start()]), match[0]))
        cursor = match.end()
    parts.append(prose(answer[cursor:]))
    return _URL.sub(url, ''.join(parts)), kept, removed


def grounded_citation_counts(answer, prepared):
    """Share the exact presentation rules for non-persisted runtime diagnostics."""
    _, kept, removed = _filter_grounded_answer(answer, prepared)
    return {'web_citations_kept': kept, 'web_citations_removed': removed}


# --- Support check (E2): a cheap guard, not a semantic verifier. -------------
# A sentence is "supported" only if its strong anchors (versions, years and
# other numbers >= 32, identifiers containing digits, dotted names, dunders)
# occur in the excerpts it cites (or, if uncited, in this turn's evidence), or
# in the user's own words. Release-status negations must also appear in the
# evidence itself. Matching anchors does NOT prove a sentence true: a claim
# that reverses the evidence with the same anchors passes this check.
_FENCE = re.compile(r'(?m)^ {0,3}(`{3,})[^\n]*\n[\s\S]*?(?:^ {0,3}\1`*[ \t]*(?=\n|$)|\Z)')
_TOKEN = re.compile(r'[A-Za-z0-9_][A-Za-z0-9_.+#-]*')
_CITATION = re.compile(r'\s*\[web_\d+\]')
_RELEASE_NEGATION = re.compile(
    r'尚未(?:正式)?(?:发布|推出|发行)|(?<!是否)未(?:正式)?(?:发布|推出|发行)|'
    r'还没(?:有)?(?:正式)?(?:发布|推出|发行)|没有(?:正式)?(?:发布|推出)|'
    r"\b(?:not|n['’]t)\s+(?:yet\s+)?(?:been\s+)?released\b|"
    r'\bunreleased\b|\bnot\s+(?:out|available)\s+yet\b',
    re.IGNORECASE,
)
_UNVERIFIED_ZH = '（未经来源核实）'
_UNVERIFIED_EN = ' (not verified by sources)'


def _strong_anchors(text):
    anchors = set()
    for raw in _TOKEN.findall(text):
        token = raw.strip('.-+').lower()
        if not token:
            continue
        if token.startswith('__') and token.endswith('__') and len(token) > 4:
            anchors.add(token)
        elif re.fullmatch(r'\d+(?:\.\d+)+', token):
            anchors.add(token)  # version / decimal
        elif token.isdigit():
            if int(token) >= 32:
                anchors.add(token)  # years, larger quantities; not days/months
        elif re.search(r'\d', token):
            anchors.add(token)  # F1, wasm32, 2to3, 11gb, v8
        elif re.search(r'[a-z]\.[a-z]', token):
            anchors.add(token)  # node.js, sys.remote_exec
    return anchors


def _normalize_corpus(text):
    text = text.lower()
    return text + '\n' + re.sub(r'(\d)\s+([a-z])', r'\1\2', text)


def _anchor_present(anchor, corpus):
    return re.search(
        r'(?<![0-9a-z_])' + re.escape(anchor) + r'(?![0-9a-z_])', corpus,
    ) is not None


def _split_sentences(line):
    pieces = [p for p in re.split(r'(?<=[。！？!?])|(?<=\.)(?=\s)', line) if p]
    merged = []
    for piece in pieces:
        # A citation placed after the full stop belongs to that sentence.
        if merged and re.fullmatch(r'(?:\s*\[web_\d+\])+[\s。.]*', piece):
            merged[-1] += piece
        else:
            merged.append(piece)
    return merged


_LEAD = re.compile(r'^(\s*(?:(?:[-*+]|\d+[.)])\s+|#{1,6}\s+|>\s*)*)')
_EMPTY_LINE = re.compile(r'^\s*(?:(?:[-*+]|\d+[.)])\s*|#{1,6}\s*|>\s*)*$')


def _mark_unverified(sentence, chinese):
    """Put the qualifier before the claim so it never reads as established."""
    text = _CITATION.sub('', sentence)
    marker = (_UNVERIFIED_ZH if chinese else _UNVERIFIED_EN.strip() + ' ')
    stripped = text.rstrip()
    if stripped.lstrip().startswith('|'):
        # Table row: keep the qualifier inside the current cell and never
        # add a cell delimiter (a sentence may end mid-row, before " |").
        trailing = text[len(stripped):]
        if stripped.endswith('|'):
            return stripped[:-1].rstrip() + ' ' + marker.strip() + ' |' + trailing
        return stripped + ' ' + marker.strip() + trailing
    lead = _LEAD.match(text).group(1)
    return lead + marker + text[len(lead):]


def support_check(text, prepared, *, user_texts=(), chinese=False):
    """Return (text, unverified_count, removed_count). Fenced code is skipped.

    Unsupported anchored sentences lose their citations and are prefixed as
    unverified. A release-status negation ("尚未发布", "not yet released")
    that this turn's evidence does not itself state is removed entirely:
    it is the observed failure class and must not be shown as fact.
    """
    excerpts = {
        item.evidence_ref: item.excerpt for item in prepared.used_web_evidence
    }
    if not excerpts:
        return text, 0, 0
    all_evidence = _normalize_corpus('\n'.join(excerpts.values()))
    user_corpus = _normalize_corpus('\n'.join(t for t in user_texts if isinstance(t, str)))
    unverified = removed = 0

    def check_sentence(sentence):
        nonlocal unverified, removed
        refs = re.findall(r'\[(web_\d+)\]', sentence)
        # URLs were already restricted to this turn's sources; they are
        # references, not factual anchors.
        claim = _URL.sub(' ', _CITATION.sub('', sentence))
        evidence = (_normalize_corpus('\n'.join(excerpts.get(r, '') for r in refs))
                    if refs else all_evidence)
        if (_RELEASE_NEGATION.search(claim) is not None
                and _RELEASE_NEGATION.search(evidence) is None):
            removed += 1
            lead = _LEAD.match(sentence).group(1)
            return lead if lead.strip() else ''
        missing = [a for a in _strong_anchors(claim)
                   if not _anchor_present(a, evidence) and not _anchor_present(a, user_corpus)]
        if missing:
            unverified += 1
            return _mark_unverified(sentence, chinese)
        return sentence

    def prose(block):
        lines = []
        for line in block.split('\n'):
            checked = ''.join(check_sentence(s) for s in _split_sentences(line))
            if line.strip() and _EMPTY_LINE.match(checked):
                continue  # every sentence on this line was removed
            lines.append(checked)
        return '\n'.join(lines)

    parts, cursor = [], 0
    for match in _FENCE.finditer(text):
        parts.extend((prose(text[cursor:match.start()]), match[0]))
        cursor = match.end()
    parts.append(prose(text[cursor:]))
    result = ''.join(parts)
    if removed:
        result = result.rstrip() + (
            f'\n\n（已省略 {removed} 处本次来源不支持的发布状态说法。）' if chinese else
            f'\n\n(Omitted {removed} release-status statement(s) not supported by this turn\'s sources.)'
        )
    return result, unverified, removed


def present_grounded_answer(answer, prepared, *, chinese=False, user_texts=(),
                            diagnostics=None):
    """Preserve Markdown and build source links only from fetched metadata.

    Presentation filtering plus the cheap E2 support check; not a factual
    claim verifier.
    """
    text, _, _ = _filter_grounded_answer(answer, prepared, chinese=chinese)
    text, unverified, removed = support_check(text, prepared, user_texts=user_texts,
                                              chinese=chinese)
    if diagnostics is not None:
        diagnostics['web_claims_unverified'] = unverified
        diagnostics['web_claims_removed'] = removed
    if 'provider_partial_failure' in prepared.missing:
        text += ('\n\n部分搜索服务失败，来源覆盖可能不完整。' if chinese else
                 '\n\nSome search providers failed; source coverage may be incomplete.')
    return text + source_section(prepared.sources, chinese=chinese, concise=True)
