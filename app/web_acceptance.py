"""Opt-in W2 prototype: explicit evidence coverage, not semantic verification.

No model, persistence, intent parser or provider configuration is owned here.
Metadata assertions must come from a trusted source-specific adapter/operator;
text witnesses prove provenance, not the semantic role of an arbitrary date.
"""
from dataclasses import dataclass, replace
from datetime import date
from hashlib import sha256
from urllib.parse import urlsplit, urlunsplit

from app.web_evidence_select import UsedWebEvidence, select_used_web_evidence
from app.web_extract import ExtractedWebPage, extract_web_page
from app.web_orchestration import prepare_web_grounding
from app.web_passages import rank_web_passages
from app.web_search_routing import build_search_plan
from app.web_security import normalize_public_hostname, validate_public_url


@dataclass(frozen=True)
class EvidenceRequirements:
    versions: tuple[str, ...] = ()
    authoritative_domains: tuple[str, ...] = ()
    min_sources: int = 1
    separate_version_sources: bool = False
    require_publication_date: bool = False
    publication_date: date | None = None
    publication_window: tuple[date, date] | None = None
    required_text: tuple[str, ...] = ()

    def __post_init__(self):
        if type(self.min_sources) is not int or not 1 <= self.min_sources <= 2:
            raise ValueError("Only one or two distinct sources are supported")
        for values in (self.versions, self.authoritative_domains, self.required_text):
            if not isinstance(values, tuple) or any(not isinstance(v, str) or not v.strip() for v in values):
                raise ValueError("Requirements must be tuples of nonempty strings")
            if len(values) != len(set(values)):
                raise ValueError("Duplicate requirements")
        if len(self.versions) > 2:
            raise ValueError("At most two required versions")
        if any(type(flag) is not bool for flag in
               (self.separate_version_sources, self.require_publication_date)):
            raise ValueError("Requirement flags must be booleans")
        if self.publication_date is not None and type(self.publication_date) is not date:
            raise ValueError("Publication date must be a date")
        if self.publication_window is not None:
            if (not isinstance(self.publication_window, tuple) or len(self.publication_window) != 2
                    or any(type(d) is not date for d in self.publication_window)
                    or self.publication_window[0] > self.publication_window[1]):
                raise ValueError("Invalid inclusive publication window")
        for domain in self.authoritative_domains:
            if normalize_public_hostname(domain) != domain:
                raise ValueError("Use normalized authoritative domains")


@dataclass(frozen=True)
class TextFact:
    value: str
    start: int
    end: int


@dataclass(frozen=True)
class SourceFacts:
    # Bind every adapter assertion to the final URL and exact extracted text.
    url: str
    text_sha256: str
    version: TextFact | None = None
    publication_date: TextFact | None = None  # ISO YYYY-MM-DD, source text


@dataclass(frozen=True)
class ProviderFailure:
    engine: str
    code: str


def searxng_failures(payload):
    """Call on raw payload before SearXNGProvider removes diagnostics.

    Keep failure identity, not arbitrary backend messages/credentials in UI data.
    An empty list is genuinely empty only if no selected-engine failure exists.
    """
    failures = []
    for item in payload.get("unresponsive_engines", ()):
        if not isinstance(item, (list, tuple)) or not item or not isinstance(item[0], str) or not item[0]:
            raise ValueError("Malformed provider failure diagnostic")
        failures.append(ProviderFailure(item[0], "UPSTREAM_ENGINE_FAILED"))
    return tuple(failures)


def canonical_url(url):
    valid = validate_public_url(url)
    p = urlsplit(valid["url"])
    host = valid["hostname"]
    host = "[" + host + "]" if ":" in host else host
    return urlunsplit((valid["scheme"], host, p.path or "/", p.query, ""))


def source_identity(url):
    return "web-source:" + sha256(canonical_url(url).encode()).hexdigest()


@dataclass(frozen=True)
class AcceptedSource:
    identity: str
    page: ExtractedWebPage
    version: str | None
    published: date | None
    evidence: tuple[UsedWebEvidence, ...]


@dataclass(frozen=True)
class CandidateDecision:
    result_id: str
    accepted: bool
    missing: tuple[str, ...]


@dataclass(frozen=True)
class EvidenceAcceptance:
    technical_status: str  # legacy readiness, never a sufficiency assertion
    retrieval_status: str
    evidence_status: str
    covered: tuple[str, ...]
    missing: tuple[str, ...]
    sources: tuple[AcceptedSource, ...]
    evidence: tuple[UsedWebEvidence, ...]
    decisions: tuple[CandidateDecision, ...]
    provider_failures: tuple[ProviderFailure, ...]
    grounding: object
    observed_pages: tuple[ExtractedWebPage, ...] = ()


def _fact(page, fact, evidence):
    if fact is None:
        return None
    if not (0 <= fact.start < fact.end <= len(page.text)):
        return None
    if page.text[fact.start:fact.end] != fact.value:
        return None
    # A fact outside the actual model evidence does not satisfy coverage.
    if not any(e.start_char <= fact.start and e.end_char >= fact.end for e in evidence):
        return None
    return fact.value


def _missing(req, sources):
    missing = []
    if len(sources) < req.min_sources:
        missing.append(f"sources:{req.min_sources}")
    versions = {s.version for s in sources}
    missing.extend("version:" + v for v in req.versions if v not in versions)
    if req.separate_version_sources and len(sources) < len(req.versions):
        missing.append("separate_version_sources")
    if not sources:
        if req.authoritative_domains:
            missing.append("authoritative_domain")
        if req.require_publication_date or req.publication_date or req.publication_window:
            missing.append("publication_date")
        missing.extend("text:" + t for t in req.required_text)
    return tuple(missing)


def accept_web_evidence(query, *, requirements, provider_builder,
                        source_facts=lambda page: None, provider_failures=lambda: (),
                        **orchestration_options):
    """Run existing bounded pipeline with an explicit, conservative collector.

    Default Safe Fetch and extraction remain the existing production functions.
    Fixtures may inject existing DI seams. No custom network or storage path.
    """
    if not isinstance(requirements, EvidenceRequirements):
        raise TypeError("Explicit EvidenceRequirements required")
    reserved = {"max_fetch_candidates", "candidate_acceptor", "rank_web_passages_fn",
                "select_used_web_evidence_fn", "build_search_plan_fn"}
    if reserved & orchestration_options.keys():
        raise ValueError("Prototype limits/acceptance hooks cannot be overridden")
    sources, decisions, readable, extracted = [], [], [], []
    extractor = orchestration_options.pop("extract_web_page_fn", extract_web_page)

    def extract(fetched):
        page = extractor(fetched)
        extracted.append(page)
        return page
    quota = 3600 // max(requirements.min_sources, len(requirements.versions), 1)

    def collect(page, ranked, legacy_evidence):
        readable.append(page.result_id)
        evidence = select_used_web_evidence(page, ranked, max_total_chars=quota)
        url = canonical_url(page.fetched_url)
        identity = source_identity(url)
        digest = sha256(page.text.encode()).hexdigest()
        missing = []
        host = validate_public_url(url)["hostname"]
        if requirements.authoritative_domains and not any(
            host == domain or host.endswith("." + domain)
            for domain in requirements.authoritative_domains
        ):
            missing.append("authoritative_domain")
        facts = source_facts(page)
        if facts is not None and (canonical_url(facts.url) != url or facts.text_sha256 != digest):
            missing.append("metadata_binding")
            facts = None
        version = _fact(page, facts.version, evidence) if facts else None
        published = _fact(page, facts.publication_date, evidence) if facts else None
        try:
            published = date.fromisoformat(published) if published else None
        except ValueError:
            published = None
        if requirements.versions and version not in requirements.versions:
            missing.append("source_version")
        if requirements.require_publication_date or requirements.publication_date or requirements.publication_window:
            if published is None:
                missing.append("publication_date")
            elif requirements.publication_date and published != requirements.publication_date:
                missing.append("publication_date_mismatch")
            elif requirements.publication_window and not requirements.publication_window[0] <= published <= requirements.publication_window[1]:
                missing.append("publication_window")
        text = "\n".join(e.excerpt for e in evidence)
        missing.extend("text:" + t for t in requirements.required_text if t not in text)
        if not evidence:
            missing.append("selected_evidence")
        if any(s.identity == identity or sha256(s.page.text.encode()).hexdigest() == digest for s in sources):
            missing.append("distinct_source")
        if requirements.separate_version_sources and any(s.version == version for s in sources):
            missing.append("distinct_version_source")
        if len(sources) == 2:
            missing.append("source_limit")
        decisions.append(CandidateDecision(page.result_id, not missing, tuple(missing)))
        if not missing:
            offset = sum(len(s.evidence) for s in sources)
            evidence = tuple(replace(e, ordinal=offset+i, evidence_ref=f"web_{offset+i+1}")
                             for i, e in enumerate(evidence))
            sources.append(AcceptedSource(identity, page, version, published, evidence))
        if _missing(requirements, sources):
            return None
        return tuple(e for s in sources for e in s.evidence)

    # Reuse the lexical ranker, focusing it on explicitly requested content.
    def rank(query, passages):
        focus = " ".join((query, *requirements.required_text, *requirements.versions))
        return rank_web_passages(focus, passages)

    def single_attempt(query):
        plan = build_search_plan(query)
        return replace(plan, attempts=plan.attempts[:1])

    grounding = prepare_web_grounding(
        query, provider_builder=provider_builder, max_fetch_candidates=3,
        candidate_acceptor=collect, rank_web_passages_fn=rank,
        build_search_plan_fn=single_attempt, extract_web_page_fn=extract,
        **orchestration_options,
    )
    failures = list(provider_failures())
    failures.extend(ProviderFailure(o.name, o.error_code or "PROVIDER_FAILED")
                    for o in grounding.search_execution.outcomes if o.status == "provider_failed")
    discovery = grounding.search_execution.discovery
    if extracted:
        retrieval = "RETRIEVAL_SUCCESS"
    elif failures:
        retrieval = "PROVIDER_FAILED"
    elif discovery is None or not discovery.results:
        retrieval = "NO_RESULTS"
    else:
        retrieval = "EVIDENCE_INSUFFICIENT"  # fetch/extraction/selection outcomes retained
    missing = _missing(requirements, sources)
    covered = tuple([f"source:{s.identity}" for s in sources] +
                    ["version:" + v for v in requirements.versions if any(s.version == v for s in sources)])
    if sources:
        covered += tuple("text:" + t for t in requirements.required_text)
        if requirements.authoritative_domains:
            covered += ("authoritative_domain",)
        if requirements.require_publication_date or requirements.publication_date or requirements.publication_window:
            covered += ("publication_date",)
    return EvidenceAcceptance(
        "READY" if readable else grounding.status, retrieval,
        "EVIDENCE_INSUFFICIENT" if missing else "EVIDENCE_SUFFICIENT",
        covered, missing, tuple(sources), tuple(e for s in sources for e in s.evidence),
        tuple(decisions), tuple(failures), grounding, tuple(extracted),
    )


@dataclass(frozen=True)
class SourceMapEntry:
    evidence_ref: str
    url: str
    title: str
    source_identity: str
    evidence_status: str
    coverage_limitations: tuple[str, ...]
    excerpt: str


def source_map(result):
    """Read-only map from exact accepted slices, never model citation text.

    URL validation here is syntactic/public-literal validation. DNS pinning and
    redirect validation belong to the unchanged Safe Fetch boundary.
    """
    entries = []
    for source in result.sources:
        page = source.page
        url = canonical_url(page.fetched_url)
        if source.identity != source_identity(url):
            raise ValueError("Invalid source identity")
        # Discovery titles are unverified; use a bounded heading from source text.
        title = next((line.strip()[:300] for line in page.text.splitlines() if line.strip()), url)
        for e in source.evidence:
            if (canonical_url(e.source_url) != url or not 0 <= e.start_char < e.end_char <= len(page.text)
                    or page.text[e.start_char:e.end_char].strip() != e.excerpt):
                raise ValueError("Invalid evidence provenance")
            expected = f"web_{len(entries)+1}"
            if e.evidence_ref != expected or e.ordinal != len(entries):
                raise ValueError("Invalid global evidence reference")
            entries.append(SourceMapEntry(e.evidence_ref, url, title, source.identity,
                                          result.evidence_status, result.missing, e.excerpt))
    if tuple(e for s in result.sources for e in s.evidence) != result.evidence:
        raise ValueError("Used-evidence map mismatch")
    return tuple(entries)


def open_webui_sources(result):
    """v0.6.5 source-card payload only; no event emission or chat resubmission.

    Native cards group by metadata.source URL. [web_n] is retained as metadata;
    it is not automatically equivalent to WebUI's numeric inline citations.
    """
    return tuple({
        "source": {"id": e.source_identity, "name": e.title, "url": e.url},
        "document": [e.excerpt],
        "metadata": [{"source": e.url, "name": e.title, "corvus_ref": e.evidence_ref,
                      "corvus_source_identity": e.source_identity,
                      "evidence_status": e.evidence_status,
                      "coverage_limitations": list(e.coverage_limitations)}],
    } for e in source_map(result))
