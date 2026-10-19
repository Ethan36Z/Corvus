"""Progressive Web presentation over the existing W2 retrieval collector.

No persistence, personal recall, model calls, event emission, or new pipeline.
"""
from dataclasses import dataclass
from html import escape
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


def _chinese(text):
    return any('\u3400' <= ch <= '\u9fff' for ch in text)


def source_section(sources, *, chinese=False):
    """Only validated retrieval URLs; no source titles or model-provided links."""
    lines = ['\n\n来源（已抓取页面，完整性和时效性另见说明）：' if chinese else
             '\n\nSources (pages fetched; coverage and freshness may remain limited):']
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


def prepare_web_mvp(query, *, provider_builder, requirements=None,
                    source_facts=lambda page: None, **collector_options):
    """Unknown requirements deliberately select the conservative link fallback.

    Explicit constraints define the scope of sufficiency, never universal truth.
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
    accepted = accept_web_evidence(
        query, requirements=req, provider_builder=builder, source_facts=source_facts,
        provider_failures=lambda: tuple(failures), **collector_options,
    )
    # Domain/source count alone does not establish factual question coverage.
    explicit = requirements is not None and bool(
        req.versions or req.require_publication_date or req.publication_date
        or req.publication_window or req.required_text
    )
    sufficient = (explicit and accepted.evidence_status == 'EVIDENCE_SUFFICIENT'
                  and not accepted.provider_failures)
    if sufficient:
        mapped = source_map(accepted)
        sources = []
        for entry in mapped:
            index = next((i for i, s in enumerate(sources) if s.identity == entry.source_identity), None)
            if index is None:
                sources.append(MVPSource(entry.url, entry.source_identity, (entry.evidence_ref,)))
            else:
                old = sources[index]
                sources[index] = MVPSource(old.url, old.identity, old.refs + (entry.evidence_ref,))
        return MVPPreparation(accepted.technical_status, 'GROUNDED_ANSWER',
                              accepted.evidence_status, (), tuple(sources), accepted.evidence,
                              accepted.grounding.selected_result_id,
                              retrieval_status=accepted.retrieval_status)

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


def present_grounded_answer(answer, prepared, *, chinese=False):
    """Keep model prose, but build all clickable source links from metadata.

    This is conservative presentation filtering, not a factual claim verifier.
    """
    if not isinstance(answer, str) or not answer.strip():
        raise ValueError('Empty grounded answer')
    refs = {ref for source in prepared.sources for ref in source.refs}
    text = escape(answer, quote=False)
    # Remove link/image destinations and link definitions from model output.
    text = re.sub(r'!?\[([^\]\n]*)\]\([^\n]*?\)', r'\1', text)
    text = re.sub(r'(?m)^\s*\[[^\]\n]+\]:[^\n]*$', '', text)
    text = re.sub(r'(?i)(?:[a-z][a-z0-9+.-]*://|www\.)[^\s<>]+', '[unverified link omitted]', text)
    text = re.sub(r'\[(web_\d+)\]', lambda m: m[0] if m[1] in refs else '[unverified citation]', text)
    text = re.sub(r'\[\d+\]', '[unverified citation]', text)
    # Treat model output as prose, not executable Markdown link syntax.
    specials = set('\\`*_{}[]()#+.!|>~-')
    text = ''.join('\\' + ch if ch in specials else ch for ch in text)
    return text + source_section(prepared.sources, chinese=chinese)
