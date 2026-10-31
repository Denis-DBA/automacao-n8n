import asyncio
import importlib.util
import json
import secrets
import time
from pathlib import Path

import httpx
import pytest

CLIENT = httpx.AsyncClient
ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def proxy(tmp_path, monkeypatch):
    monkeypatch.setenv('TOKEN_DATA_DIR', str(tmp_path))
    monkeypatch.setenv('PROXY_API_KEY', secrets.token_hex(32))
    monkeypatch.setenv('TOKEN_QUERY_API_KEY', secrets.token_hex(32))
    spec = importlib.util.spec_from_file_location('proxy_under_test', ROOT/'proxy/main.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def upstream(proxy, monkeypatch, handler):
    def factory(*args, **kwargs):
        return CLIENT(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(proxy.httpx, 'AsyncClient', factory)


def auth(proxy):
    return {'Authorization': 'Bearer '+proxy.PROXY_API_KEY}


async def query(client, proxy, correlation='12-0'):
    return (await client.get('/token-usage', params={'correlation_id': correlation},
             headers={'X-Token-Query-Key': proxy.TOKEN_QUERY_API_KEY})).json()


@pytest.mark.asyncio
async def test_auth_and_allowlist(proxy):
    await proxy.validate_config()
    async with CLIENT(transport=httpx.ASGITransport(app=proxy.app),base_url='http://test') as c:
        assert (await c.get('/health')).status_code == 200
        assert (await c.get('/token-usage')).status_code == 401
        assert (await c.post('/v1/chat/completions')).status_code == 401
        assert (await c.delete('/api/delete',headers=auth(proxy))).status_code == 403
        assert (await c.post('/api/pull',headers=auth(proxy))).status_code == 403
        assert (await c.post('/v1/chat/completions',headers=auth(proxy),json={})).status_code == 400
        assert (await c.get('/v1/models?token=synthetic',headers=auth(proxy))).status_code == 400


@pytest.mark.asyncio
async def test_json_usage_headers_and_aggregation(proxy, monkeypatch):
    def handle(req):
        assert 'authorization' not in req.headers
        assert 'cookie' not in req.headers
        assert 'x-token-query-key' not in req.headers
        data=json.loads(req.content)
        assert 'correlation_id' not in data
        return httpx.Response(200,json={'model':'synthetic-model','usage':{'prompt_tokens':7,'completion_tokens':3}})
    upstream(proxy,monkeypatch,handle)
    async with CLIENT(transport=httpx.ASGITransport(app=proxy.app),base_url='http://test') as c:
        for _ in range(2):
            r=await c.post('/v1/chat/completions',headers=auth(proxy)|{'Cookie':'synthetic','X-Token-Query-Key':'synthetic'},json={'model':'synthetic-model','stream':False,'correlation_id':'12-0'})
            assert r.status_code==200
        usage=await query(c,proxy)
        assert usage['status']=='real' and usage['requests']==2 and usage['total_tokens']==20
        assert usage['by_model']['synthetic-model']['input_tokens']==14
        assert (await query(c,proxy,'13-0'))['total_tokens'] is None


class Chunks(httpx.AsyncByteStream):
    def __init__(self,chunks,fail=False):self.chunks,self.fail=chunks,fail
    async def __aiter__(self):
        for chunk in self.chunks:
            yield chunk
        if self.fail:raise httpx.ReadError('synthetic interruption')


@pytest.mark.asyncio
@pytest.mark.parametrize('native',[False,True])
async def test_streaming_split_chunks(proxy,monkeypatch,native):
    usage={'model':'synthetic','prompt_eval_count':2,'eval_count':4} if native else {'model':'synthetic','usage':{'prompt_tokens':2,'completion_tokens':4}}
    raw=(('' if native else 'data: ')+json.dumps(usage)+'\n'+('' if native else '\ndata: [DONE]\n\n')).encode()
    def handle(req):
        if not native:assert json.loads(req.content)['stream_options']['include_usage'] is True
        return httpx.Response(200,headers={'content-type':'application/x-ndjson' if native else 'text/event-stream'},stream=Chunks([raw[:5],raw[5:19],raw[19:]]))
    upstream(proxy,monkeypatch,handle)
    async with CLIENT(transport=httpx.ASGITransport(app=proxy.app),base_url='http://test') as c:
        r=await c.post('/api/chat' if native else '/v1/chat/completions',headers=auth(proxy),json={'model':'synthetic','correlation_id':'12-0','stream':True})
        assert r.content==raw
        assert (await query(c,proxy))['total_tokens']==6


@pytest.mark.asyncio
async def test_missing_and_interrupted_usage(proxy,monkeypatch):
    def handle(req):
        return httpx.Response(200,stream=Chunks([b'data: {"usage":{"prompt_tokens":2,"completion_tokens":4}}\n'],fail=True))
    upstream(proxy,monkeypatch,handle)
    async with CLIENT(transport=httpx.ASGITransport(app=proxy.app),base_url='http://test') as c:
        with pytest.raises(Exception):
            await c.post('/v1/chat/completions',headers=auth(proxy),json={'model':'synthetic','correlation_id':'12-0'})
        usage=await query(c,proxy)
        assert usage['status']=='unavailable' and usage['total_tokens'] is None
        assert usage['unavailable_requests']==1
    assert proxy.active==0


@pytest.mark.asyncio
async def test_body_and_buffer_limits(proxy,monkeypatch):
    proxy.MAX_BODY=100
    async with CLIENT(transport=httpx.ASGITransport(app=proxy.app),base_url='http://test') as c:
        assert (await c.post('/api/chat',headers=auth(proxy),content=b'x'*101)).status_code==413
    proxy.MAX_BODY=10000;proxy.MAX_LINE=10
    upstream(proxy,monkeypatch,lambda req:httpx.Response(200,stream=Chunks([b'x'*11])))
    async with CLIENT(transport=httpx.ASGITransport(app=proxy.app),base_url='http://test') as c:
        with pytest.raises(Exception):
            await c.post('/api/chat',headers=auth(proxy),json={'model':'synthetic','correlation_id':'12-0'})
        assert (await query(c,proxy))['status']=='unavailable'


@pytest.mark.asyncio
async def test_concurrent_correlations_and_admission(proxy,monkeypatch):
    async def handle(req):
        await asyncio.sleep(0.02)
        return httpx.Response(200,json={'model':'synthetic','usage':{'prompt_tokens':1,'completion_tokens':2}})
    upstream(proxy,monkeypatch,handle)
    proxy.MAX_CONCURRENT=2
    async with CLIENT(transport=httpx.ASGITransport(app=proxy.app),base_url='http://test') as c:
        results=await asyncio.gather(*(c.post('/v1/chat/completions',headers=auth(proxy),json={'model':'synthetic','correlation_id':f'{i}-0'}) for i in range(10,14)))
        assert sorted(r.status_code for r in results)==[200,200,429,429]
        for i in range(10,12):assert (await query(c,proxy,f'{i}-0'))['requests']==1
    assert proxy.active==0


def test_deduplication_rotation_retention(proxy):
    record=proxy.extrair_tokens({'usage':{'prompt_tokens':1,'completion_tokens':2}},'synthetic-id','12-0','synthetic')
    proxy.escrever_registro(record);proxy.escrever_registro(record)
    assert len(proxy.consultar_registros('12-0'))==1
    assert proxy.extrair_tokens({'usage':{'prompt_tokens':True,'completion_tokens':2}},'x','12-0','x') is None
    old=proxy.TOKEN_DIR/'token_usage-2000-01-01.jsonl'
    old.write_text('{}\n')
    __import__('os').utime(old,(0,0))
    proxy.escrever_registro(record)
    assert not old.exists()
    proxy.MAX_STORAGE=1000
    for _ in range(20):proxy.escrever_registro(record)
    assert sum(f.stat().st_size for f in proxy.TOKEN_DIR.glob('*.jsonl'))<=1000


@pytest.mark.asyncio
async def test_upstream_failure_and_invalid_query(proxy,monkeypatch):
    def fail(req):raise httpx.ConnectError('synthetic unreachable')
    upstream(proxy,monkeypatch,fail)
    async with CLIENT(transport=httpx.ASGITransport(app=proxy.app),base_url='http://test') as c:
        assert (await c.post('/api/chat',headers=auth(proxy),json={'model':'synthetic','correlation_id':'12-0'})).status_code==502
        assert (await c.get('/token-usage?correlation_id=invalid',headers={'X-Token-Query-Key':proxy.TOKEN_QUERY_API_KEY})).status_code==400


@pytest.mark.asyncio
async def test_startup_fails_closed(proxy):
    proxy.PROXY_API_KEY=''
    with pytest.raises(RuntimeError):await proxy.validate_config()
