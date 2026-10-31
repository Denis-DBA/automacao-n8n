"""Synthetic live proxy checks. Never reads an environment file or prints keys."""
import argparse
import json
import os
import time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request,urlopen


def run(args):
    base=args.proxy_url.rstrip('/')
    infer={'Authorization':'Bearer '+os.environ['PROXY_API_KEY']}
    query_headers={'X-Token-Query-Key':os.environ['TOKEN_QUERY_API_KEY']}
    checks=[]

    def call(path,data=None,headers=None):
        body=json.dumps(data).encode() if data is not None else None
        return urlopen(Request(base+path,data=body,headers={'Content-Type':'application/json',**(headers or {})}),timeout=180)

    def status(path,data,headers,expected):
        try:
            with call(path,data,headers) as response:actual=response.status
        except HTTPError as error:actual=error.code
        assert actual==expected,(path,actual,expected)

    def usage(cid):
        with call('/token-usage?'+urlencode({'correlation_id':cid}),headers=query_headers) as response:return json.load(response)

    with call('/health') as response:assert json.load(response)['status']=='ok'
    status('/v1/models',None,{},401)
    status('/token-usage',None,{},401)
    status('/api/pull',{'name':'synthetic-not-a-real-model'},infer,403)
    status('/api/chat',{'model':args.model,'correlation_id':'invalid'},infer,400)
    checks.extend(['health','inference_auth','query_auth','admin_routes_blocked','correlation_validation'])
    for native in [False,True]:
        cid=str(time.time_ns())+'-0'
        payload={'model':args.model,'stream':True,'correlation_id':cid,
                 'messages':[{'role':'user','content':'Responda somente: teste sintético.'}]}
        if native:payload['options']={'num_predict':64};payload['think']=False
        else:payload.update(max_tokens=64,reasoning_effort='none')
        result=None
        with call('/api/chat' if native else '/v1/chat/completions',payload,infer) as response:
            for raw in response:
                line=raw.decode().strip()
                if line.startswith('data:'):line=line[5:].strip()
                if not line or line=='[DONE]':continue
                data=json.loads(line)
                if native and data.get('done'):result=(data['prompt_eval_count'],data['eval_count'])
                elif data.get('usage'):result=(data['usage']['prompt_tokens'],data['usage']['completion_tokens'])
        assert result is not None,'Streaming não trouxe informação final de uso'
        record=usage(cid)
        assert record['status']=='real' and (record['input_tokens'],record['output_tokens'])==result
        assert record['total_tokens']==sum(result)
        checks.append('ndjson_actual_usage' if native else 'sse_actual_usage')
    cid=str(time.time_ns())+'-0'
    payload={'model':args.model,'stream':True,'correlation_id':cid,'max_tokens':2048,
             'messages':[{'role':'user','content':'Escreva um texto sintético longo sobre números naturais.'}]}
    with call('/v1/chat/completions',payload,infer) as response:response.read(1)
    deadline=time.monotonic()+20
    while True:
        interrupted=usage(cid)
        if interrupted['found']:break
        assert time.monotonic()<deadline,'Interrupção não registrada'
        time.sleep(.2)
    assert interrupted['status']=='unavailable' and interrupted['total_tokens'] is None
    checks.append('cancelled_stream_unavailable_not_zero')
    missing=str(time.time_ns())+'-0'
    status('/api/chat',{'model':'synthetic-model-not-installed','correlation_id':missing,'stream':False},infer,404)
    assert usage(missing)['status']=='unavailable' and usage(missing)['total_tokens'] is None
    checks.append('upstream_error_unavailable_not_zero')
    report={'result':'passed','checks':checks,'model':args.model,'synthetic':True}
    print(json.dumps(report,ensure_ascii=False,indent=2))
    if args.report:
        from pathlib import Path
        Path(args.report).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':
    p=argparse.ArgumentParser(description='Teste ao vivo com modelo instalado: autenticação, streams e consumo indisponível')
    p.add_argument('--proxy-url',default='http://localhost:18003');p.add_argument('--model',required=True);p.add_argument('--report')
    run(p.parse_args())
