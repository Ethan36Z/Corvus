"""W2.1 offline MVP integration: no live HTTP, model or deployed storage."""
from dataclasses import replace
from datetime import date
import asyncio
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).parent))
from test_web_acceptance import Harness, historical, facts
from test_web_acceptance import substantive as controlled  # W2-b: pages must carry real content
from app.web_acceptance import EvidenceRequirements as Requirements, source_identity
from app.web_mvp import prepare_web_mvp, present_grounded_answer, MVPSource, source_section
from app.conversation_runtime import process_turn
from app.model_client import ModelClientError
from app import playground_api as api
from app.searxng_provider import SearXNGProvider
import httpx


class Runtime:
    def __init__(self,harness,requirements=None,fail_assistant=False):
        self.h=harness;self.req=requirements;self.events=[];self.prepared=None
        self.fail_assistant=fail_assistant;self.packed=None
    def add(self,session,role,text):
        self.events.append(('add',role,text))
        if role=='assistant' and self.fail_assistant:raise RuntimeError('synthetic commit failure')
        return 1 if role=='user' else 2
    def prepare(self,query,**kwargs):
        kwargs['provider_builder']=self.h.provider
        self.prepared=prepare_web_mvp(query,**kwargs,fetch_search_result_fn=self.h.fetch,
                                     extract_web_page_fn=self.h.extract)
        return self.prepared
    def context(self,**kwargs):
        self.events.append(('context',));self.packed=kwargs.get('web_evidence_content')
        return {'messages':[{'role':'system','content':self.packed or ''},{'role':'user','content':'synthetic'}],
                'recent_message_ids':[],'historical_message_ids':[],'input_tokens':20,'retrieval_status':'OK'}
    def generate(self,messages):
        self.events.append(('generate',))
        return 'A natural explanation [web_1]. [invented](http://127.0.0.1:8096/private) [web_999].'
    def persist(self,message_id,items):
        self.events.append(('evidence',message_id,items));return list(range(len(items)))
    def run(self,**kwargs):
        return process_turn('synthetic-session','concurrent.futures',add_message_fn=self.add,
            build_context_fn=self.context,count_tokens_fn=lambda msgs:20,generate_fn=self.generate,
            dense_sync_fn=lambda ids:self.events.append(('dense',ids)),system_prompt_fn=lambda:'system',
            record_web_evidence_batch_fn=self.persist,web_mode='on',web_mvp_enabled=True,
            web_requirements=self.req,prepare_web_mvp_fn=self.prepare,**kwargs)


class MVPIntegrationTests(unittest.TestCase):
    def test_unknown_requirements_with_evidence_generate_answer(self):
        for req in (None, Requirements()):
            with self.subTest(requirements=req):
                r=Runtime(Harness([controlled()]),req);result=r.run()
                self.assertEqual(result['web_presentation_outcome'],'GROUNDED_ANSWER')
                self.assertEqual(result['web_answer_basis'],'RETRIEVED_EVIDENCE')
                self.assertEqual(result['web_acceptance_status'],'EVIDENCE_RETRIEVED')
                self.assertEqual(result['model_status'],'OK')
                self.assertEqual(result['web_coverage_missing'],['requirements_not_specified','single_source'])  # W2-c diagnostic
                self.assertEqual([x[0] for x in r.events],['add','context','generate','add','evidence','dense'])
                saved=next(e[2] for e in r.events if e[0]=='evidence')
                expected=[dict(ordinal=e.ordinal,source_title=e.source_title,
                    source_url=e.source_url,excerpt=e.excerpt)
                    for e in r.prepared.used_web_evidence]
                self.assertEqual(saved,expected)
                self.assertIn('[web_1]',result['reply'])
                self.assertIn(r.prepared.sources[0].url,result['reply'])
                self.assertNotIn('web_999',result['reply']);self.assertNotIn('127.0.0.1',result['reply'])
                self.assertEqual(result['web_citations_kept'],1)
                self.assertEqual(result['web_citations_removed'],1)
                self.assertEqual(result['web_query_rewrite_status'],'NOT_REQUESTED')

    def test_unknown_requirements_partial_provider_failure_still_generates(self):
        p=controlled();h=Harness([p]);r=Runtime(h)
        payload={'results':[{'url':p.source_url,'title':'source','content':'concurrent.futures'}],
                 'unresponsive_engines':[['google cse','access denied']]}
        h.provider=lambda a:SearXNGProvider(fetch_json=lambda *a,**kw:payload)
        result=r.run()
        self.assertEqual(result['web_presentation_outcome'],'GROUNDED_ANSWER')
        self.assertEqual(result['web_answer_basis'],'RETRIEVED_EVIDENCE')
        self.assertEqual(result['web_acceptance_status'],'EVIDENCE_RETRIEVED')
        self.assertEqual(result['web_coverage_missing'],['requirements_not_specified','single_source','provider_partial_failure'])  # W2-c
        self.assertIn('Some search providers failed; source coverage may be incomplete.',result['reply'])
        self.assertEqual([e[0] for e in r.events],['add','context','generate','add','evidence','dense'])

    def test_unknown_requirements_without_relevant_passages_do_not_generate(self):
        p=controlled();p=replace(p,text='Unrelated apples and pears.',original_chars=26,extracted_chars=26)
        r=Runtime(Harness([p]));result=r.run()
        self.assertEqual(result['web_presentation_outcome'],'SOURCES_WITH_LIMITATIONS')
        self.assertEqual(result['web_evidence_status'],'NOT_USED')
        self.assertEqual(result['model_status'],'NOT_CALLED')
        self.assertEqual([e[0] for e in r.events],['add','add','dense'])

    def test_unknown_requirements_model_failure_never_retries_or_writes_assistant(self):
        r=Runtime(Harness([controlled()]))
        def fail(messages):
            r.events.append(('generate',))
            raise ModelClientError('MODEL_UNAVAILABLE','synthetic model failure')
        r.generate=fail
        result=r.run()
        self.assertEqual(result['model_status'],'MODEL_UNAVAILABLE')
        self.assertIsNone(result['assistant_message_id'])
        self.assertEqual([e[0] for e in r.events],['add','context','generate'])
        self.assertNotIn('web_presentation_outcome',result)

    def test_grounded_markdown_preserved_with_filtered_links_and_citations(self):
        h=Harness([controlled()]);p=prepare_web_mvp('concurrent.futures',provider_builder=h.provider,
            fetch_search_result_fn=h.fetch,extract_web_page_fn=h.extract)
        markdown='# Heading\n- **bold**\n\n| A | B |\n| --- | --- |\n| 1 | 2 |\n> quote\n'
        code='```python\nprint("[web_999] [3] <tag> [t](dest)")\n```\n`[web_999] <tag>`'
        answer=markdown+code+'\n<script> [t](http://x) ![alt](http://x) [web_1] [web_999] [3]\n'
        answer+='[ref]: https://evil.invalid\nhttps://evil.invalid/path\n'+p.sources[0].url
        answer+='\n```text\nhttps://evil.invalid/path\n```\n`https://evil.invalid/path`'
        text=present_grounded_answer(answer,p)
        self.assertIn(markdown,text);self.assertIn(code,text)
        self.assertIn('&lt;script>',text);self.assertIn('t alt [web_1]',text)
        body=text.split('\n\nSources:')[0]
        self.assertNotIn('[web_999]',body.replace(code,''));self.assertNotIn('[3]',body.replace(code,''))
        self.assertNotIn('evil.invalid',text);self.assertNotIn('http://x',text)
        self.assertNotIn('[ref]:',text);self.assertIn(p.sources[0].url,body)
        self.assertEqual(text.count('](<'),1)
        self.assertIn('```text\n[link removed]\n```',text)
        self.assertIn('`[link removed]`',text)
        zh=present_grounded_answer('事实 [web_1] https://evil.invalid',
            replace(p,missing=('provider_partial_failure',)),chinese=True)
        self.assertIn('[链接已移除]',zh);self.assertIn('\n\n来源：',zh)
        self.assertIn('部分搜索服务失败，来源覆盖可能不完整。',zh)
        canonical=present_grounded_answer(p.sources[0].url+'#section',p)
        self.assertIn(p.sources[0].url+'#section',canonical)
        extra='``literal `tick` [web_999]``\n````text\n```\n[web_999]\n````'
        self.assertTrue(present_grounded_answer(extra,p).startswith(extra))
        self.assertIn('`'+p.sources[0].url+'`',present_grounded_answer('`'+p.sources[0].url+'`',p))
        paren_url='https://docs.python.org/page_(example)'
        paren=replace(p,sources=(MVPSource(paren_url,source_identity(paren_url),('web_1',)),))
        self.assertTrue(present_grounded_answer(paren_url,paren).startswith(paren_url))

    def test_inline_code_cannot_hide_malicious_links_across_paragraphs(self):
        h=Harness([controlled()]);p=prepare_web_mvp('concurrent.futures',provider_builder=h.provider,
            fetch_search_result_fn=h.fetch,extract_web_page_fn=h.extract)
        for separator in ('\n','\n\n'):
            with self.subTest(separator=repr(separator)):
                answer='`opening'+separator+'[malicious](javascript:alert(1))'+separator+'closing`'
                text=present_grounded_answer(answer,p)
                body=text.split('\n\nSources:')[0]
                self.assertIn('malicious',body)
                self.assertNotIn('javascript:',body)
                self.assertNotIn('](',body)
                self.assertEqual(text.count('](<'),1)
                self.assertIn(p.sources[0].url,text)

    def test_inline_code_cannot_hide_raw_html_across_paragraphs(self):
        h=Harness([controlled()]);p=prepare_web_mvp('concurrent.futures',provider_builder=h.provider,
            fetch_search_result_fn=h.fetch,extract_web_page_fn=h.extract)
        for separator in ('\n','\n\n'):
            with self.subTest(separator=repr(separator)):
                answer='`opening'+separator+'<script>alert(1)</script><img src=x onerror=alert(1)>'+separator+'closing`'
                text=present_grounded_answer(answer,p)
                body=text.split('\n\nSources:')[0]
                self.assertNotIn('<',body)
                self.assertIn('&lt;script>alert(1)&lt;/script>',body)
                self.assertIn('&lt;img src=x onerror=alert(1)>',body)

    def test_grounded_answer_uses_packer_and_persists_exact_used_evidence_once(self):
        r=Runtime(Harness([controlled()]),Requirements(required_text=('concurrent.futures',)))
        result=r.run()
        self.assertEqual(result['web_presentation_outcome'],'GROUNDED_ANSWER')
        self.assertEqual(result['model_status'],'OK');self.assertEqual(result['web_evidence_status'],'PERSISTED')
        self.assertIn('CORVUS_UNTRUSTED_WEB_',r.packed)
        self.assertEqual([x[0] for x in r.events],['add','context','generate','add','evidence','dense'])
        saved=next(e[2] for e in r.events if e[0]=='evidence')
        self.assertEqual([e['excerpt'] for e in saved],[e.excerpt for e in r.prepared.used_web_evidence])
        self.assertNotIn('127.0.0.1',result['reply']);self.assertNotIn('web_999',result['reply'])
        self.assertIn(r.prepared.sources[0].url,result['reply'])
        self.assertEqual(len([e for e in r.events if e[0]=='generate']),1)

    def test_provider_failure_and_empty_are_honest_canonical_replies_without_model(self):
        for h,expected in [(Harness([],fail=True),'PROVIDER_FAILED'),(Harness([]),'NO_RESULTS')]:
            r=Runtime(h);result=r.run()
            self.assertEqual(result['web_presentation_outcome'],'SEARCH_FAILED')
            self.assertEqual(result['web_discovery_status'],expected)
            self.assertEqual([x[0] for x in r.events],['add','add','dense'])
            self.assertEqual(h.calls,1);self.assertEqual(h.fetches,[])
            self.assertNotIn('synthetic provider failure',result['reply'].lower())
            self.assertEqual(result['web_sources'],[])

    def test_incorrect_version_date_preserves_link_without_claiming_false_source(self):
        p=controlled('3.13');r=Runtime(Harness([p]),Requirements(versions=('3.14',),require_publication_date=True))
        result=r.run(web_source_facts_fn=lambda p:facts(p,version='3.13',published='2026-10-15'))
        self.assertEqual(result['web_presentation_outcome'],'SOURCES_WITH_LIMITATIONS')
        self.assertIn('version:3.14',result['web_coverage_missing'])
        self.assertEqual(result['model_status'],'NOT_CALLED')
        self.assertNotIn('false',result['reply'].lower())
        r=Runtime(Harness([p]),Requirements(publication_window=(date(2026,10,16),date(2026,10,18))))
        self.assertEqual(r.run(web_source_facts_fn=lambda p:facts(p,published='2026-10-15'))['web_acceptance_status'],'EVIDENCE_INSUFFICIENT')

    def test_bounded_continuation_and_multisource_refs_reach_canonical_provenance(self):
        r=Runtime(Harness([historical('python_unversioned'),controlled('3.13'),controlled('3.14')]),
                  Requirements(versions=('3.13','3.14'),min_sources=2,separate_version_sources=True))
        def fact_fn(p):
            if '/3.13/' in p.fetched_url:return facts(p,version='3.13')
            if '/3.14/' in p.fetched_url:return facts(p,version='3.14')
        result=r.run(web_source_facts_fn=fact_fn)
        self.assertEqual(result['web_presentation_outcome'],'GROUNDED_ANSWER')
        self.assertEqual(len(r.h.fetches),3)
        refs=[e.evidence_ref for e in r.prepared.used_web_evidence]
        self.assertEqual(len(refs),len(set(refs)));self.assertEqual(refs,[f'web_{i+1}' for i in range(len(refs))])
        self.assertEqual(len(result['web_sources']),2)
        self.assertLessEqual(sum(len(e.excerpt) for e in r.prepared.used_web_evidence),3600)

    def test_no_unfetched_search_link_is_presented(self):
        h=Harness([controlled()])
        from app.web_fetch import WebFetchError
        def failed(*a):raise WebFetchError('FIXTURE_FAILED','PRIVATE_BACKEND_DETAIL')
        prepared=prepare_web_mvp('concurrent.futures',provider_builder=h.provider,fetch_search_result_fn=failed)
        self.assertEqual(prepared.outcome,'SEARCH_FAILED');self.assertEqual(prepared.sources,())
        self.assertNotIn(controlled().source_url,prepared.deterministic_reply)
        self.assertNotIn('PRIVATE_BACKEND_DETAIL',prepared.deterministic_reply)

    def test_assistant_commit_failure_stops_provenance_and_never_retries(self):
        r=Runtime(Harness([controlled()]),Requirements(required_text=('absent condition',)),fail_assistant=True);result=r.run()
        self.assertEqual(result['persistence_status'],'ASSISTANT_PERSISTENCE_FAILED')
        self.assertEqual(result['assistant_message_id'],None)
        self.assertEqual([x[0] for x in r.events],['add','add']);self.assertEqual(r.h.calls,1)

    def test_api_serializes_typed_requirements_and_mvp_fields_without_private_memory(self):
        request=api.ChatRequest(session_id='synthetic-session',message='question',web_mode='on',
            web_requirements={'required_text':['concurrent.futures']})
        self.assertEqual(request.web_requirements.required_text,('concurrent.futures',))
        r=Runtime(Harness([controlled()]));result=r.run()
        response=api.build_chat_response(result,load_messages_fn=lambda ids:[])
        self.assertEqual(response['web_presentation_outcome'],'GROUNDED_ANSWER')
        self.assertEqual(response['status']['model'],'OK')
        self.assertEqual(response['web_answer_basis'],'RETRIEVED_EVIDENCE')
        self.assertEqual(response['status']['persistence'],'NORMAL')
        self.assertNotIn('excerpt',json.dumps(response['web_sources']))
        self.assertEqual(response['web_sources'][0]['verification'],'FETCHED_EXTRACTED')

    def test_searxng_diagnostics_retained_before_normalization(self):
        payload={'results':[],'unresponsive_engines':[['google news','access denied']]}
        def builder(attempt):return SearXNGProvider(fetch_json=lambda *a,**kw:payload)
        prepared=prepare_web_mvp('NASA news',provider_builder=builder)
        self.assertEqual(prepared.outcome,'SEARCH_FAILED')
        self.assertEqual(prepared.retrieval_status,'PROVIDER_FAILED')
        self.assertNotIn('access denied',prepared.deterministic_reply)

    def test_model_links_and_unknown_citations_cannot_create_source_links(self):
        h=Harness([controlled()]);p=prepare_web_mvp('concurrent.futures',provider_builder=h.provider,
            requirements=Requirements(required_text=('concurrent.futures',)),fetch_search_result_fn=h.fetch,extract_web_page_fn=h.extract)
        text=present_grounded_answer('[nested [x]](//evil.invalid/path) <a href="http://127.0.0.1/x">bad</a> [web_999]',p)
        self.assertNotIn('127.0.0.1',text);self.assertNotIn('[web_999]',text)
        self.assertNotIn('[nested [x]](',text)
        self.assertNotIn('<a ',text)
        self.assertEqual(text.count('](<'),1)
        with self.assertRaises(ValueError):source_section((MVPSource('http://127.0.0.1/x','fake'),))

    def test_normal_chat_compatibility_mvp_flag_does_not_force_web(self):
        r=Runtime(Harness([controlled()]))
        result=process_turn('synthetic','hello',add_message_fn=r.add,build_context_fn=r.context,
          count_tokens_fn=lambda msgs:20,generate_fn=lambda msgs:'ordinary reply',dense_sync_fn=lambda ids:None,
          system_prompt_fn=lambda:'system',web_mode='off',web_mvp_enabled=True)
        self.assertEqual(result['reply'],'ordinary reply')
        self.assertNotIn('web_presentation_outcome',result);self.assertEqual(r.h.calls,0)

    def test_failed_intent_does_not_silently_call_answer_model(self):
        r=Runtime(Harness([controlled()]))
        def fail(*a):raise RuntimeError('PRIVATE_INTENT_ERROR')
        result=process_turn('synthetic','latest info',add_message_fn=r.add,
            generate_fn=lambda msgs:self.fail('must not generate'),dense_sync_fn=lambda ids:None,
            web_mode='auto',web_mvp_enabled=True,web_intent_decide_fn=fail)
        self.assertEqual(result['web_presentation_outcome'],'SEARCH_FAILED')
        self.assertNotIn('PRIVATE_INTENT_ERROR',result['reply'])
        self.assertEqual(len(r.events),2)

    def test_presentation_failure_never_repeats_generation_or_user_commit(self):
        r=Runtime(Harness([controlled()]),Requirements(required_text=('concurrent.futures',)))
        with patch('app.conversation_runtime.present_grounded_answer',side_effect=ValueError('PRIVATE_DETAIL')):
            result=r.run()
        self.assertEqual(result['model_status'],'WEB_PRESENTATION_FAILED')
        self.assertEqual([e[0] for e in r.events],['add','context','generate'])
        self.assertIsNone(result['assistant_message_id']);self.assertEqual(r.h.calls,1)
        self.assertNotIn('web_presentation_outcome',result)
        self.assertNotIn('PRIVATE_DETAIL',result['error'])

    def test_api_passes_only_requirements_not_client_metadata_or_activation(self):
        request=api.ChatRequest(session_id='synthetic-session',message='question',web_mode='on',
            web_requirements={'required_text':['concurrent.futures']},
            web_mvp_enabled=True,web_source_facts={'version':'invented'})
        r=Runtime(Harness([controlled()]));result=r.run();captured=[]
        def runtime(**kwargs):captured.append(kwargs);return result
        with patch.object(api,'process_turn',runtime):response=api.post_chat(request)
        self.assertEqual(captured[0]['web_requirements'].required_text,('concurrent.futures',))
        self.assertNotIn('web_mvp_enabled',captured[0]);self.assertNotIn('web_source_facts',captured[0])
        self.assertEqual(response['web_presentation_outcome'],'GROUNDED_ANSWER')

    def test_partial_provider_failure_with_content_stays_visible(self):
        p=controlled();h=Harness([p])
        payload={'results':[{'url':p.source_url,'title':'source','content':'concurrent.futures'}],
                 'unresponsive_engines':[['google cse','access denied']]}
        prepared=prepare_web_mvp('concurrent.futures',requirements=Requirements(required_text=('concurrent.futures',)),
            provider_builder=lambda a:SearXNGProvider(fetch_json=lambda *a,**kw:payload),
            fetch_search_result_fn=h.fetch,extract_web_page_fn=h.extract)
        self.assertEqual(prepared.outcome,'SOURCES_WITH_LIMITATIONS')
        self.assertIn('provider_partial_failure',prepared.missing)
        self.assertIn('search-provider work failed',prepared.deterministic_reply)


# Reuse the existing mocked Pipe contracts; no live endpoint is contacted.
spec=importlib.util.spec_from_file_location('pipe_contract_fixture',Path(__file__).with_name('test_open_webui_pipe.py'))
fixture=importlib.util.module_from_spec(spec);sys.modules[spec.name]=fixture;spec.loader.exec_module(fixture)
class MVPPipeTests(fixture.PipeContracts):
    # The inherited contracts run too, including existing auth/identity/no-retry checks.
    async def test_confirmed_fallback_is_returned_once(self):
        session=fixture.adapter.corvus_session_id('corvus-private-test','user-1',fixture.CHAT_ID)
        self.response_override={'session_id':session,'assistant_message_id':2,'reply':'Sources with limitations',
          'web_presentation_outcome':'SOURCES_WITH_LIMITATIONS','web_acceptance_status':'EVIDENCE_INSUFFICIENT',
          'status':{'overall':'DEGRADED','model':'NOT_CALLED','persistence':'NORMAL'}}
        self.assertEqual(await self.call(),'Sources with limitations');self.assertEqual(len(self.requests),1)
    async def test_fallback_still_requires_same_session_and_confirmed_persistence(self):
        session=fixture.adapter.corvus_session_id('corvus-private-test','user-1',fixture.CHAT_ID)
        base={'session_id':session,'assistant_message_id':2,'reply':'fallback',
          'web_presentation_outcome':'SEARCH_FAILED','web_acceptance_status':'EVIDENCE_INSUFFICIENT',
          'status':{'overall':'DEGRADED','model':'NOT_CALLED','persistence':'NORMAL'}}
        for changes in [{'session_id':'other'},{'assistant_message_id':None},
                        {'status':{'overall':'FAILED','model':'NOT_CALLED','persistence':'ASSISTANT_PERSISTENCE_FAILED'}},
                        {'web_presentation_outcome':'GROUNDED_ANSWER'}]:
            self.response_override={**base,**changes}
            with self.assertRaises(ValueError):await self.call()
        self.assertEqual(len(self.requests),4)

if __name__=='__main__':unittest.main(verbosity=2)
