"""Additive inference transport tests; all openers are synthetic."""
from copy import deepcopy
from email.message import Message
from io import BytesIO
import json
import socket
import unittest
from unittest.mock import patch
import urllib.error
from app import model_client as client


def envelope(content=' answer ', finish='stop'):
    return {'id':'chatcmpl-synthetic', 'object':'chat.completion', 'created':1700000000,
            'model':'corvus','choices':[{'index':0,'message':{'role':'assistant','content':content},'finish_reason':finish}],
            'usage':{'prompt_tokens':10,'completion_tokens':3,'total_tokens':13}}


class StatelessTransport(unittest.TestCase):
    def payload(self):
        return {'model':'corvus','messages':[{'role':'user','content':'test'}], 'max_tokens':512}

    def test_counts_same_rendered_request_then_one_generation_preserving_envelope(self):
        calls=[]
        def opener(req, timeout):
            calls.append((req.full_url,json.loads(req.data),timeout))
            return BytesIO(json.dumps({'input_tokens':10} if req.full_url.endswith('input_tokens') else envelope()).encode())
        result=client.stateless_chat_completion(self.payload(),opener=opener)
        self.assertEqual(result,envelope());self.assertEqual(len(calls),2)
        self.assertEqual(calls[0][1],calls[1][1])
        self.assertEqual(calls[0][1]['chat_template_kwargs'],{'enable_thinking':False})
        self.assertIs(calls[0][1]['stream'],False);self.assertIs(calls[0][1]['cache_prompt'],False)
        self.assertLessEqual(calls[1][2],calls[0][2])

    def test_bad_counts_and_budget_never_generate(self):
        for value,code in [(True,'MODEL_RESPONSE_INVALID'),(-1,'MODEL_RESPONSE_INVALID'),(None,'MODEL_RESPONSE_INVALID'),(4097,'INPUT_TOO_LONG')]:
            calls=[]
            def opener(req,timeout):
                calls.append(req.full_url);return BytesIO(json.dumps({'input_tokens':value}).encode())
            with self.subTest(value=value),self.assertRaises(client.ModelClientError) as raised:
                client.stateless_chat_completion(self.payload(),opener=opener)
            self.assertEqual(raised.exception.code,code);self.assertEqual(len(calls),1)

    def test_failures_never_retry(self):
        for failure in [TimeoutError(),socket.timeout(),urllib.error.URLError('synthetic'),
                        urllib.error.HTTPError('http://synthetic',500,'private',{},None),ValueError('private')]:
            calls=[]
            def opener(req,timeout):
                calls.append(req.full_url);raise failure
            with self.subTest(failure=type(failure)),self.assertRaises(client.ModelClientError):
                client.stateless_chat_completion(self.payload(),opener=opener)
            self.assertEqual(len(calls),1)

    def test_legacy_caller_payload_and_string_result_unchanged(self):
        def opener(req,timeout):
            body=json.loads(req.data)
            self.assertEqual(set(body),{'model','messages','temperature','top_p','seed','max_tokens','chat_template_kwargs'})
            self.assertEqual(body['temperature'],0);self.assertEqual(body['seed'],42)
            return BytesIO(json.dumps(envelope()).encode())
        self.assertEqual(client.generate_chat_completion(self.payload()['messages'],opener=opener),'answer')

    def reply(self,body=b'{}',**kwargs):
        response=BytesIO(body);response.status=200
        headers=Message();headers['Content-Type']='application/json'
        response.headers=headers;response.geturl=lambda:client.CHAT_COMPLETIONS_URL
        for k,v in kwargs.items():setattr(response,k,v)
        return response

    def test_fixed_target_no_proxy_redirect_and_bounded_read(self):
        response=self.reply();fake=type('Opener',(),{'open':lambda *_a,**_kw:response})()
        request=urllib_request()
        with patch.object(client.urllib.request,'build_opener',return_value=fake) as build:
            with client._bounded_model_opener(request,1) as body:self.assertEqual(body.read(),b'{}')
            self.assertEqual(build.call_args.args[0].proxies,{})
            self.assertIsNone(build.call_args.args[1].redirect_request(None,None,302,'',{},'http://evil'))
        self.assertTrue(response.closed)
        with patch.object(client.urllib.request,'build_opener') as build,self.assertRaises(client.ModelClientError):
            client._bounded_model_opener(client.urllib.request.Request('http://evil',method='POST'),1)
        build.assert_not_called()

    def test_bound_compression_content_type_and_error_closure(self):
        for body,content_type,encoding in [(b'x'*262145,'application/json','identity'),(b'{}','text/plain','identity'),(b'{}','application/json','gzip')]:
            response=self.reply(body);response.headers.replace_header('Content-Type',content_type);response.headers['Content-Encoding']=encoding
            fake=type('Opener',(),{'open':lambda *_a,**_kw:response})()
            with self.subTest(content_type=content_type,encoding=encoding,size=len(body)),patch.object(client.urllib.request,'build_opener',return_value=fake),self.assertRaises(client.ModelClientError):
                with client._bounded_model_opener(urllib_request(),1) as result:result.read()
            self.assertTrue(response.closed)
        body=BytesIO(b'secret provider response')
        error=urllib.error.HTTPError('http://synthetic',503,'private',{},body)
        fake=type('Opener',(),{'open':lambda *_a,**_kw: (_ for _ in ()).throw(error)})()
        with patch.object(client.urllib.request,'build_opener',return_value=fake),self.assertRaises(client.ModelClientError) as raised:
            client._bounded_model_opener(urllib_request(),1)
        self.assertEqual(raised.exception.code,'MODEL_UNAVAILABLE');self.assertTrue(body.closed)

    def test_header_wait_and_body_share_deadline(self):
        response=self.reply();fake=type('Opener',(),{'open':lambda *_a,**_kw:response})()
        with patch.object(client.urllib.request,'build_opener',return_value=fake),patch('time.monotonic',side_effect=[10,12]):
            with self.assertRaises(TimeoutError):
                with client._bounded_model_opener(urllib_request(),1) as result:result.read()
        self.assertTrue(response.closed)


def urllib_request():
    return client.urllib.request.Request(client.CHAT_COMPLETIONS_URL,method='POST')


if __name__=='__main__':unittest.main()
