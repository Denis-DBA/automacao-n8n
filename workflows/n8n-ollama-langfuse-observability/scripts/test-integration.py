"""Synthetic live smoke test; no private .env is read. Does not test n8n import."""
import argparse
import base64
import json
import os
import secrets
import time
import urllib.request


def call(url, data=None, headers=None):
    body=None if data is None else json.dumps(data).encode()
    req=urllib.request.Request(url,data=body,headers={'Content-Type':'application/json',**(headers or {})})
    with urllib.request.urlopen(req,timeout=180) as response:
        content=response.read()
        return json.loads(content) if content else {}


def main():
    parser=argparse.ArgumentParser(description='Teste sintético; gera inferência e opcionalmente trace/score novos')
    parser.add_argument('--proxy-url',default='http://localhost:18003')
    parser.add_argument('--model',required=True)
    parser.add_argument('--langfuse-url',help='Habilita escrita sintética neste projeto Langfuse')
    args=parser.parse_args()
    headers={'Authorization':'Bearer '+os.environ['PROXY_API_KEY']}
    query={'X-Token-Query-Key':os.environ['TOKEN_QUERY_API_KEY']}
    base=args.proxy_url.rstrip('/')
    assert call(base+'/health')['status']=='ok'
    models=call(base+'/v1/models',headers=headers)
    assert args.model in [m['id'] for m in models['data']], 'Modelo não disponível'
    correlation=f'{time.time_ns()}-0'
    start=time.time_ns()
    response=call(base+'/v1/chat/completions',{'model':args.model,'stream':False,'correlation_id':correlation,
      'messages':[{'role':'user','content':'Explique em três frases o que é observabilidade de inteligência artificial.'}]},headers)
    end=time.time_ns()
    assert response.get('choices'), 'Resposta da IA ausente'
    usage=call(base+'/token-usage?correlation_id='+correlation,headers=query)
    assert usage['status']=='real' and usage['total_tokens']==usage['input_tokens']+usage['output_tokens']
    print('Health, modelo, inferência e contadores reais por correlação: aprovados.')
    if args.langfuse_url:
        lf=args.langfuse_url.rstrip('/')
        basic=base64.b64encode((os.environ['LANGFUSE_PUBLIC_KEY']+':'+os.environ['LANGFUSE_SECRET_KEY']).encode()).decode()
        auth={'Authorization':'Basic '+basic,'x-langfuse-ingestion-version':'4'}
        trace=secrets.token_hex(16)
        attrs={'langfuse.observation.type':'generation','langfuse.trace.name':'synthetic-smoke-test',
          'langfuse.session.id':'synthetic-session-'+secrets.token_hex(8),
          'langfuse.observation.model.name':args.model,
          'langfuse.observation.usage_details':json.dumps({'input':usage['input_tokens'],'output':usage['output_tokens'],'total':usage['total_tokens']}),
          'langfuse.observation.input':json.dumps('Teste sintético de observabilidade'),
          'langfuse.observation.output':json.dumps('Resposta sintética omitida no relatório')}
        span={'traceId':trace,'spanId':secrets.token_hex(8),'name':'Teste sintético','kind':1,
          'startTimeUnixNano':str(start),'endTimeUnixNano':str(end),
          'attributes':[{'key':k,'value':{'stringValue':v}} for k,v in attrs.items()]}
        result=call(lf+'/api/public/otel/v1/traces',{'resourceSpans':[{'scopeSpans':[{'scope':{'name':'synthetic-test'},'spans':[span]}]}]},auth)
        assert not result.get('partialSuccess',{}).get('rejectedSpans'), 'OTLP rejeitou spans'
        call(lf+'/api/public/scores',{'traceId':trace,'name':'synthetic_smoke','value':1,'dataType':'NUMERIC','comment':'Score sintético de transporte; não é avaliação de IA.'},auth)
        print('OTLP e score sintéticos aceitos. Trace ID:',trace)
        print('Confira na UI o uso da observação e o dashboard. Aceitação HTTP não comprova ingestão final.')


if __name__=='__main__':main()
