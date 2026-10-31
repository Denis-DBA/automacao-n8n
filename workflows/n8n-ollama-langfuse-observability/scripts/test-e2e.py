"""Opt-in synthetic live validation. Reads credentials only from process environment.

Requires the imported, configured and published workflows in an independent stack.
No Docker service is changed by this test. No credential or conversation is printed.
"""
import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import hashlib
import json
import os
import secrets
import time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

MESSAGE='Explique em três frases o que é observabilidade de inteligência artificial.'


def basic(user,password):
    return 'Basic '+base64.b64encode((user+':'+password).encode()).decode()


def request(url,headers,data=None):
    body=json.dumps(data).encode() if data is not None else None
    req=Request(url,data=body,headers={'Content-Type':'application/json',**headers})
    with urlopen(req,timeout=180) as response:
        content=response.read()
        return json.loads(content) if content else {}


def retry(check,timeout=90):
    deadline=time.monotonic()+timeout
    while True:
        try:return check()
        except (AssertionError,StopIteration,HTTPError):
            if time.monotonic()>=deadline:raise
            time.sleep(2)


def parse_content(value):
    if not isinstance(value,str):return value
    try:return json.loads(value)
    except ValueError:return value


def run(args):
    lf=args.langfuse_url.rstrip('/')
    proxy=args.proxy_url.rstrip('/')
    lf_headers={'Authorization':basic(os.environ['LANGFUSE_PUBLIC_KEY'],os.environ['LANGFUSE_SECRET_KEY'])}
    chat_headers={'Authorization':basic(os.environ['N8N_CHAT_USER'],os.environ['N8N_CHAT_PASSWORD'])}
    query_headers={'X-Token-Query-Key':os.environ['TOKEN_QUERY_API_KEY']}
    # Docker Desktop VM and Windows may have different clocks. Never change host
    # time: bound reads using the server's HTTP Date and correlate by session.
    with urlopen(lf+'/api/public/health',timeout=15) as response:
        server_time=parsedate_to_datetime(response.headers['Date'])
    since=(server_time-timedelta(seconds=5)).isoformat()
    until=(server_time+timedelta(hours=1)).isoformat()
    prefix='synthetic-e2e-'+secrets.token_hex(8)
    sessions=[prefix+'-a',prefix+'-b']
    expected_sessions={hashlib.sha256(s.encode()).hexdigest() for s in sessions}

    def chat(session):
        data=request(args.chat_url,chat_headers,{'action':'sendMessage','sessionId':session,'chatInput':MESSAGE})
        assert set(data)=={'output'},'Chat devolveu dados internos ou formato incorreto'
        assert isinstance(data['output'],str) and data['output'].strip(),'Resposta IA vazia'
        assert 'otel-ingestion' not in data['output'],'Resposta de telemetria exposta ao chat'

    # Different concurrent sessions, then a repeated session to check stability.
    with ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(chat,sessions))
    chat(sessions[0])
    print('Chat: duas sessões simultâneas e repetição de sessão aprovadas.')

    def observation_rows():
        params={'fromStartTime':since,'toStartTime':until,
                'fields':'core,basic,usage,io,model,metrics,metadata,trace_context','limit':100}
        return request(lf+'/api/public/v2/observations?'+urlencode(params),lf_headers)['data']

    def verify_ingestion():
        rows=observation_rows()
        roots=[r for r in rows if r['type']=='AGENT' and r.get('sessionId') in expected_sessions]
        assert len(roots)==3,'Três observações do agente ainda não disponíveis'
        counts={sid:sum(r['sessionId']==sid for r in roots) for sid in expected_sessions}
        assert sorted(counts.values())==[1,2],'Sessão não permaneceu estável'
        trace_ids={r['traceId'] for r in roots}
        assert len(trace_ids)==3,'Trace IDs reutilizados'
        generations=[];request_ids=set();proxy_totals={'input':0,'output':0,'total':0}
        for root in roots:
            same=[r for r in rows if r['traceId']==root['traceId']]
            assert any(r['name']=='Monitoramento n8n' for r in same),'Subworkflow ainda não ingerido'
            gens=[r for r in same if r['type']=='GENERATION']
            assert any(r['name']=='Ollama — avaliação' for r in gens),'Consumo do avaliador ausente'
            assert root['totalUsage']==0,'Agente pai duplica os tokens das gerações'
            assert root['latency']>0,'Latência ausente'
            for field in ['input','output']:
                value=str(parse_content(root[field]))
                if args.expect_content:assert value and 'OMITIDO' not in value,'Conteúdo sintético não capturado'
                else:assert 'OMITIDO' in value,'Conteúdo exposto sem opt-in'
            execution_id=str(root['metadata']['execution_id'])
            records=[]
            for suffix in ['0','99999999']:
                usage=request(proxy+'/token-usage?'+urlencode({'correlation_id':execution_id+'-'+suffix}),query_headers)
                assert usage['status']=='real' and usage['found'],'Proxy sem contadores reais completos'
                records.extend(usage['records'])
            assert len(records)==len(gens),'Quantidade de chamadas difere entre proxy e Langfuse'
            for record in records:
                rid=record['request_id'];assert rid not in request_ids,'Request ID duplicado entre execuções'
                request_ids.add(rid)
                observation=next(g for g in gens if g['metadata'].get('request_id')==rid)
                assert observation['sessionId']==root['sessionId']
                assert observation['model']==args.model
                for key,field in [('input','inputUsage'),('output','outputUsage'),('total','totalUsage')]:
                    assert observation[field]==record[key+'_tokens'],'Contador real divergente'
                    proxy_totals[key]+=record[key+'_tokens']
            generations.extend(gens)
        score_params={'fields':'subject,details','traceId':','.join(sorted(trace_ids)),'limit':100}
        scores=request(lf+'/api/public/v3/scores?'+urlencode(score_params),lf_headers)['data']
        for trace_id in trace_ids:
            score=next(s for s in scores if s['name']=='overall_quality' and s['subject']['id']==trace_id)
            assert isinstance(score['value'],(float,int)) and 0<=score['value']<=1
            assert score.get('comment'),'Justificativa de score ausente'
        return rows,roots,generations,proxy_totals

    rows,roots,gens,totals=retry(verify_ingestion)
    query={'view':'observations','dimensions':[{'field':'providedModelName'}],
           'metrics':[{'measure':m,'aggregation':'sum'} for m in ['inputTokens','outputTokens','totalTokens']],
           'filters':[{'type':'string','column':'traceName','operator':'=','value':'n8n-ollama-observability'}],
           'fromTimestamp':since,'toTimestamp':until}

    def verify_metrics():
        data=request(lf+'/api/public/v2/metrics?'+urlencode({'query':json.dumps(query)}),lf_headers)['data']
        for key,field in [('input','sum_inputTokens'),('output','sum_outputTokens'),('total','sum_totalTokens')]:
            assert sum(float(row.get(field) or 0) for row in data)==totals[key],'Agregação do dashboard diverge dos contadores'
        return data

    retry(verify_metrics)
    report={'result':'passed','synthetic':True,'chat_requests':3,'sessions':2,'traces':len(roots),
            'generation_observations':len(gens),'scores':3,'monitor_observations':3,
            'real_tokens':totals,'capture_content':args.expect_content,'model':args.model,
            'checks':['chat_reply_only','concurrent_sessions','stable_session','unique_traces','unique_requests',
                      'proxy_langfuse_usage_equal','model','latency','score_and_comment','subworkflow_api_snapshot',
                      'metrics_usage_by_model','content_policy']}
    print(json.dumps(report,ensure_ascii=False,indent=2))
    if args.report:
        from pathlib import Path
        Path(args.report).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return report


def main():
    parser=argparse.ArgumentParser(description='Valida workflows reais usando apenas conversas sintéticas e credenciais próprias')
    parser.add_argument('--chat-url',required=True,help='URL do chat publicado com Basic Auth na instalação de teste')
    parser.add_argument('--langfuse-url',required=True)
    parser.add_argument('--proxy-url',default='http://localhost:18003')
    parser.add_argument('--model',required=True)
    parser.add_argument('--expect-content',action='store_true',help='Somente se capture_content=true com dados sintéticos')
    parser.add_argument('--report',help='JSON de resultados agregados, sem credenciais ou conversas')
    run(parser.parse_args())


if __name__=='__main__':main()
