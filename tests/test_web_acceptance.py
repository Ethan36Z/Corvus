"""Offline public snapshots plus explicitly synthetic positive fixtures."""
from dataclasses import replace
from datetime import date
from hashlib import sha256
import json
from pathlib import Path
import unittest

from app.web_acceptance import (
    EvidenceRequirements as Requirements, SourceFacts, TextFact, ProviderFailure,
    accept_web_evidence, searxng_failures, source_map, open_webui_sources,
)
from app.web_evidence_prompt import pack_web_evidence
from app.web_extract import ExtractedWebPage, extract_web_page
from app.web_orchestration import prepare_web_grounding
from app.web_search_fetch import FetchedSearchResult
from app.web_fetch import WebFetchError

FIXTURES = json.loads((Path(__file__).parent/'fixtures/web_acceptance_w1.json').read_text())


def historical(name):
    record = FIXTURES['pages'][name]
    assert sha256(record['page']['text'].encode()).hexdigest() == record['text_sha256']
    return ExtractedWebPage(**record['page'])


def controlled(version='3.14', suffix='', published='2026-10-15'):
    # Synthetic schema fixtures, not claims that this body was fetched publicly.
    text = (f'Controlled fixture: concurrent.futures version {version}\n'
            f'Publication date: {published}\n'
            f'concurrent.futures source version {version} describes worker controls {suffix}.')
    url = f'https://docs.python.org/{version}/library/concurrent.futures{suffix}.html'
    return ExtractedWebPage('fixture', 'offline', 'Unverified search title', url, url,
                            'text/plain', 'controlled-fixture', text, len(text), len(text), False)


def substantive(version='3.14', suffix='', published='2026-10-15'):
    """controlled() plus enough on-topic body to pass the W2-b evidence-size rule."""
    page = controlled(version, suffix, published)
    detail = (
        '\nThe concurrent.futures module provides a high-level interface for '
        'asynchronously executing callables. Execution can be performed with '
        'threads, using ThreadPoolExecutor, or separate processes, using '
        'ProcessPoolExecutor. Both implement the same interface defined by the '
        'abstract Executor class. submit() schedules a callable and returns a '
        'Future; map() applies a function across iterables; shutdown() releases '
        'resources once pending futures finish. Worker controls include '
        'max_workers, initializer and initargs, which configure each worker '
        'before tasks run in this synthetic concurrent.futures fixture.'
    )
    text = page.text + detail
    from dataclasses import replace as _replace
    return _replace(page, text=text, original_chars=len(text), extracted_chars=len(text))


def facts(page, version=None, published=None):
    def witness(value):
        start = page.text.index(value)
        return TextFact(value, start, start+len(value))
    return SourceFacts(page.fetched_url, sha256(page.text.encode()).hexdigest(),
                       witness(version) if version else None,
                       witness(published) if published else None)


class Harness:
    def __init__(self, pages, *, fail=False, diagnostics=()):
        self.pages, self.fail, self.diagnostics = pages, fail, diagnostics
        self.fetches, self.calls = [], 0

    def provider(self, attempt):
        outer = self
        class Provider:
            name = 'offline-fixture'
            def search(self, query, *, limit):
                outer.calls += 1
                if outer.fail:
                    raise RuntimeError('Synthetic provider failure')
                return [{'url':p.source_url, 'title':'Python 3.14 Published 2026-10-15',
                         'snippet':'Connection.autocommit current stable 2026-10-15'}
                        for p in outer.pages][:limit]
        return Provider()

    def fetch(self, discovery, rid):
        self.fetches.append(rid)
        result = discovery.result_by_id(rid)
        page = next(p for p in self.pages if p.source_url == result.url)
        return FetchedSearchResult(rid, result.provider, result.title, result.url,
                                   page.fetched_url, 200, page.media_type, page.text,
                                   len(page.text.encode()), ())

    def extract(self, fetched):
        p = next(p for p in self.pages if p.source_url == fetched.source_url)
        return replace(p, result_id=fetched.result_id, provider=fetched.provider)

    def run(self, req=Requirements(), fact_fn=lambda p:None, query="concurrent.futures", **kw):
        return accept_web_evidence(query, requirements=req,
            provider_builder=self.provider, source_facts=fact_fn,
            provider_failures=lambda:self.diagnostics,
            fetch_search_result_fn=self.fetch, extract_web_page_fn=self.extract, **kw)


class EvidenceAcceptanceTests(unittest.TestCase):
    def test_saved_snapshot_integrity(self):
        for name in FIXTURES['pages']:
            self.assertIsInstance(historical(name), ExtractedWebPage)

    def test_old_sqlite_cannot_satisfy_parameter(self):
        h=Harness([historical('sqlite_old')])
        result=h.run(Requirements(required_text=('Connection.autocommit',)),query='autocommit')
        self.assertEqual(result.technical_status,'READY')
        self.assertEqual(result.retrieval_status,'RETRIEVAL_SUCCESS')
        self.assertEqual(result.evidence_status,'EVIDENCE_INSUFFICIENT')
        self.assertIn('text:Connection.autocommit',result.missing)
        self.assertEqual(result.evidence,())

    def test_release_index_has_no_verified_date(self):
        result=Harness([historical('firefox_index')]).run(Requirements(
            require_publication_date=True, authoritative_domains=('firefox.com',)),query='Firefox')
        self.assertEqual(result.evidence_status,'EVIDENCE_INSUFFICIENT')
        self.assertIn('publication_date',result.decisions[0].missing)

    def test_unversioned_one_page_is_not_two_version_sources(self):
        result=Harness([historical('python_unversioned')]).run(Requirements(
            versions=('3.13','3.14'), min_sources=2, separate_version_sources=True,
            authoritative_domains=('docs.python.org',)))
        self.assertEqual(result.evidence_status,'EVIDENCE_INSUFFICIENT')
        self.assertIn('version:3.13',result.missing)
        self.assertIn('separate_version_sources',result.missing)

    def test_google_news_access_denied_is_failure_not_empty(self):
        diag=FIXTURES['google_news_diagnostics']
        failures=searxng_failures({'unresponsive_engines':diag['unresponsive_engines']})
        result=Harness([],diagnostics=failures).run()
        self.assertEqual(result.technical_status,'NO_RESULTS')
        self.assertEqual(result.retrieval_status,'PROVIDER_FAILED')
        self.assertEqual(result.provider_failures,(ProviderFailure('google news','UPSTREAM_ENGINE_FAILED'),))

    def test_genuine_empty_and_exception_are_distinct(self):
        empty=Harness([]);failed=Harness([],fail=True)
        self.assertEqual(empty.run().retrieval_status,'NO_RESULTS')
        result=failed.run()
        self.assertEqual(result.retrieval_status,'PROVIDER_FAILED')
        self.assertEqual(result.provider_failures[0].code,'WEB_SEARCH_PROVIDER_FAILED')
        self.assertEqual((empty.calls,failed.calls),(1,1))
        self.assertEqual(failed.fetches,[])

    def test_continue_after_readable_irrelevant_then_stop_when_satisfied(self):
        old=historical('sqlite_old');good=historical('sqlite_current')
        h=Harness([old,good,controlled()])
        r=h.run(Requirements(required_text=('Connection.autocommit',)),query='autocommit')
        self.assertEqual(r.evidence_status,'EVIDENCE_SUFFICIENT')
        self.assertEqual(h.fetches,['result_1','result_2'])
        self.assertEqual([x.accepted for x in r.decisions],[False,True])

    def test_two_official_versions_distinct_global_refs_and_exact_slices(self):
        h=Harness([controlled('3.13'),controlled('3.14'),controlled('3.15')])
        r=h.run(Requirements(versions=('3.13','3.14'),min_sources=2,
             separate_version_sources=True,authoritative_domains=('docs.python.org',)),
             lambda p:facts(p,version='3.13' if '/3.13/' in p.fetched_url else '3.14'))
        self.assertEqual(r.evidence_status,'EVIDENCE_SUFFICIENT')
        self.assertEqual(len(r.sources),2);self.assertEqual(len(h.fetches),2)
        self.assertNotEqual(r.sources[0].identity,r.sources[1].identity)
        self.assertEqual([e.evidence_ref for e in r.evidence],[f'web_{i+1}' for i in range(len(r.evidence))])
        self.assertLessEqual(sum(len(e.excerpt) for e in r.evidence),3600)
        self.assertEqual(pack_web_evidence(r.evidence).evidence_refs,tuple(e.evidence_ref for e in r.evidence))
        for s in r.sources:
            for e in s.evidence:self.assertEqual(s.page.text[e.start_char:e.end_char].strip(),e.excerpt)

    def test_verified_date_in_window_exact_date_and_boundaries(self):
        p=controlled();req=Requirements(require_publication_date=True,
            publication_date=date(2026,10,15), publication_window=(date(2026,10,15),date(2026,10,15)))
        r=Harness([p]).run(req,lambda p:facts(p,published='2026-10-15'))
        self.assertEqual(r.evidence_status,'EVIDENCE_SUFFICIENT')
        self.assertEqual(r.sources[0].published,date(2026,10,15))

    def test_date_outside_window_and_unproven_title_date_fail(self):
        p=controlled();req=Requirements(publication_window=(date(2026,10,16),date(2026,10,18)))
        r=Harness([p]).run(req,lambda p:facts(p,published='2026-10-15'))
        self.assertIn('publication_window',r.decisions[0].missing)
        r=Harness([p]).run(Requirements(require_publication_date=True))
        self.assertEqual(r.evidence_status,'EVIDENCE_INSUFFICIENT')

    def test_witness_mismatch_binding_and_unselected_fact_fail(self):
        p=controlled();req=Requirements(versions=('3.14',))
        for bad in [replace(facts(p,version='3.14'),text_sha256='0'*64),
                    replace(facts(p,version='3.14'),url='https://example.com/other'),
                    SourceFacts(p.fetched_url,sha256(p.text.encode()).hexdigest(),TextFact('3.14',0,4))]:
            self.assertEqual(Harness([p]).run(req,lambda p:bad).evidence_status,'EVIDENCE_INSUFFICIENT')
        # Even a valid page witness outside selected snippets cannot qualify.
        from app.web_acceptance import _fact
        self.assertIsNone(_fact(p,facts(p,version='3.14').version,()))

    def test_authority_suffix_and_redirect_final_domain_checked(self):
        p=replace(controlled(),fetched_url='https://docs.python.org.evil.example/page')
        r=Harness([p]).run(Requirements(authoritative_domains=('docs.python.org',)))
        self.assertIn('authoritative_domain',r.decisions[0].missing)

    def test_aliases_and_identical_bodies_do_not_count_twice(self):
        p=controlled();alias=replace(p,source_url='https://docs.python.org/alias')
        r=Harness([p,alias]).run(Requirements(min_sources=2))
        self.assertEqual(len(r.sources),1)
        self.assertIn('distinct_source',r.decisions[1].missing)
        mirror=replace(p,source_url='https://docs.python.org/mirror',fetched_url='https://docs.python.org/mirror')
        self.assertEqual(len(Harness([p,mirror]).run(Requirements(min_sources=2)).sources),1)

    def test_three_candidate_limit_and_two_source_limit(self):
        pages=[controlled(suffix=str(i)) for i in range(5)]
        h=Harness(pages);r=h.run(Requirements(required_text=('not-in-page',)))
        self.assertEqual(len(h.fetches),3);self.assertEqual(r.evidence_status,'EVIDENCE_INSUFFICIENT')
        r=Harness(pages).run(Requirements(min_sources=2));self.assertEqual(len(r.sources),2)
        with self.assertRaises(ValueError):Requirements(min_sources=3)
        with self.assertRaises(ValueError):Harness(pages).run(max_fetch_candidates=8)

    def test_budget_remains_bounded_with_large_pages(self):
        p=controlled();q=controlled('3.13');p=replace(p,text=p.text+'\n\n'+('concurrent.futures additional background '*400))
        r=Harness([p,q]).run(Requirements(min_sources=2))
        self.assertLessEqual(sum(len(e.excerpt) for e in r.evidence),3600)
        self.assertEqual(len(r.sources),2)

    def test_current_single_page_and_legacy_orchestration_do_not_regress(self):
        p=historical('sqlite_current');h=Harness([p])
        r=h.run(Requirements(required_text=('Connection.autocommit',)),query='autocommit')
        self.assertEqual(r.evidence_status,'EVIDENCE_SUFFICIENT')
        legacy=prepare_web_grounding('autocommit',provider_builder=h.provider,
                     fetch_search_result_fn=h.fetch,extract_web_page_fn=h.extract)
        self.assertEqual(legacy.status,'READY')
        self.assertTrue(legacy.used_web_evidence)

    def test_source_map_and_native_card_shape_no_generated_url(self):
        r=Harness([controlled()]).run();entries=source_map(r);cards=open_webui_sources(r)
        self.assertEqual(len(entries),len(r.evidence))
        for e,card in zip(entries,cards):
            self.assertEqual(card['metadata'][0]['corvus_ref'],e.evidence_ref)
            self.assertEqual(card['metadata'][0]['source'],e.url)
            self.assertEqual(card['source']['id'],e.source_identity)
            self.assertEqual(card['document'],[e.excerpt])
            self.assertEqual(len(card['document']),len(card['metadata']))
            self.assertNotEqual(e.title,'Python 3.14 Published 2026-10-15')
        forged=replace(r,evidence=(replace(r.evidence[0],source_url='http://127.0.0.1/private'),))
        with self.assertRaises(ValueError):source_map(forged)
        s=r.sources[0];bad=replace(s,evidence=(replace(s.evidence[0],excerpt='fabricated'),))
        with self.assertRaises(ValueError):source_map(replace(r,sources=(bad,)))

    def test_partial_source_map_has_coverage_limitations(self):
        r=Harness([controlled('3.13')]).run(Requirements(versions=('3.13','3.14'),min_sources=2),
                                          lambda p:facts(p,version='3.13'))
        self.assertEqual(r.evidence_status,'EVIDENCE_INSUFFICIENT')
        self.assertIn('version:3.14',source_map(r)[0].coverage_limitations)

    def test_existing_extraction_and_fetch_failure_outcomes(self):
        p=controlled();h=Harness([p])
        # Exercise actual text/plain extraction rather than the saved-page seam.
        result=accept_web_evidence('concurrent.futures',requirements=Requirements(),
            provider_builder=h.provider,fetch_search_result_fn=h.fetch)
        self.assertEqual(result.evidence_status,'EVIDENCE_SUFFICIENT')
        def fail(*a):raise WebFetchError('FIXTURE_FETCH_FAILED','offline')
        result=accept_web_evidence('concurrent.futures',requirements=Requirements(),
            provider_builder=h.provider,fetch_search_result_fn=fail)
        self.assertEqual(result.evidence_status,'EVIDENCE_INSUFFICIENT')
        self.assertEqual(result.grounding.candidate_outcomes[0].status,'FETCH_FAILED')


if __name__=='__main__':unittest.main(verbosity=2)
