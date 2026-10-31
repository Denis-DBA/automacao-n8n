"""Regression guards for failures reproduced in the real isolated installation."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def load(name):return json.loads((ROOT/'workflows'/name).read_text(encoding='utf-8'))


def test_monitor_queries_before_execution_is_discarded():
    main=load('n8n-ollama-langfuse-observability.json')
    monitor=load('monitoramento-langfuse-ollama.json')
    call=next(n for n in main['nodes'] if n['type']=='n8n-nodes-base.executeWorkflow')
    assert call['parameters']['options']['waitForSubWorkflow'] is True
    assert main['settings']['saveDataSuccessExecution']=='none'
    assert main['settings']['saveDataErrorExecution']=='none'
    assert not any(n['type']=='n8n-nodes-base.wait' for n in monitor['nodes'])
    query=next(n for n in monitor['nodes'] if n['name']=='Consultar Execução n8n')
    assert 'includeData=false' in query['parameters']['url']


def test_chat_response_is_explicit_and_precedes_nested_workflow():
    main=load('n8n-ollama-langfuse-observability.json')
    trigger=next(n for n in main['nodes'] if n['type'].endswith('chatTrigger'))
    assert trigger['parameters']['options']['responseMode']=='responseNode'
    response=next(n for n in main['nodes'] if n['type']=='n8n-nodes-base.respondToWebhook')
    assert 'output' in response['parameters']['responseBody']
    assert main['connections'][response['name']]['main'][0][0]['node']=='Preparar Monitoramento'
    assert trigger['parameters']['options']['autoSaveHighlightedData'] is False


def test_langfuse_listens_on_healthcheck_interface():
    compose=json.loads((ROOT/'docker-compose.yml').read_text(encoding='utf-8-sig'))
    assert compose['services']['langfuse-web']['environment']['HOSTNAME']=='0.0.0.0'


def test_images_match_validated_digest_lock():
    compose=json.loads((ROOT/'docker-compose.yml').read_text(encoding='utf-8-sig'))
    lock=json.loads((ROOT/'images.lock.json').read_text(encoding='utf-8'))
    for name,service in compose['services'].items():
        if name=='token-proxy':continue
        assert '@sha256:' in service['image']
        assert service['image']==lock[name]['image']
    assert (ROOT/'proxy/Dockerfile').read_text().splitlines()[0]=='FROM '+lock['proxy_base']['image']
