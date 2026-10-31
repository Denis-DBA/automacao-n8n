"""Static checks for public artifacts. No environment files are opened."""
import ast
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]


def main():
    count=0
    for path in ROOT.rglob('*.py'):
        ast.parse(path.read_text(encoding='utf-8-sig'),filename=str(path));count+=1
    for path in (ROOT/'workflows').glob('*.json'):
        data=json.loads(path.read_text(encoding='utf-8'))
        assert not data.get('pinData') and not data.get('active')
        assert not any(k in data for k in ('id','meta','versionId','staticData'))
        names={n['name'] for n in data['nodes']}
        assert len(names)==len(data['nodes'])
        for n in data['nodes']:
            assert 'credentials' not in n and 'webhookId' not in n
            text=json.dumps(n['parameters'],ensure_ascii=False)
            for ref in re.findall(r'\$\([\'\"]([^\'\"]+)[\'\"]\)',text.replace('\\"','"')):
                assert ref in names,(path.name,n['name'],ref)
            assert not re.search(r'crm\.|WhatsApp|PGVector|Evolution|HubSpot',text,re.I)
        for src,kinds in data['connections'].items():
            assert src in names
            for outputs in kinds.values():
                for edges in outputs:
                    for edge in edges:assert edge['node'] in names
        count+=1
    compose=json.loads((ROOT/'docker-compose.yml').read_text(encoding='utf-8-sig'))
    assert 'container_name' not in json.dumps(compose)
    for svc in compose['services'].values():
        for port in svc.get('ports',[]):assert port.startswith('127.0.0.1:')
    assert all(not line.split('=',1)[1] for line in (ROOT/'.env.example').read_text(encoding='utf-8').splitlines() if line.startswith(('PROXY_API_KEY=','TOKEN_QUERY_API_KEY=','LANGFUSE_INIT_PROJECT_SECRET_KEY=')))
    print(f'Validação estática aprovada: {count} arquivos Python/JSON; conexões, referências, Compose e template verificados.')


if __name__=='__main__':main()
