# Testes e demonstração

## Automatizados

PowerShell, a partir da pasta do projeto:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r tests/requirements.txt
.\.venv\Scripts\python.exe -m pytest -q -c pytest.ini
.\.venv\Scripts\python.exe scripts/validate.py
docker compose --env-file .env --profile full config --quiet
```

Bash:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r tests/requirements.txt
.venv/bin/python -m pytest -q -c pytest.ini
.venv/bin/python scripts/validate.py
docker compose --env-file .env --profile full config --quiet
```

Com Node.js 22+, execute `node scripts/validate-workflows.js`. Testes unitários usam upstream simulado e diretório temporário, sem volumes ou conversas existentes. A auditoria de dependências pode ser repetida com `python -m pip_audit -r proxy/requirements.txt --no-deps --disable-pip` no ambiente virtual. Faça detecção de segredos apenas sobre os arquivos candidatos à publicação, nunca apontando ferramentas indiscriminadamente para `.env` privados.

## Instalação limpa e demonstração n8n

1. Instale em um projeto Compose exclusivo, sem volumes externos. Importe e configure ambos os workflows.
2. Selecione o modelo instalado nos dois modelos/configuração do principal e a base URL do proxy na credencial OpenAI.
3. Habilite `Chamar Monitoramento` após selecionar o monitor. Cadastre sua chave API n8n e a credencial Langfuse no monitor.
4. Com dados sintéticos, ative `capture_content: true` se desejar verificar input, output e justificativa. Mantenha `evaluate: true` para avaliação automática.
5. No chat de teste, envie: **Explique em três frases o que é observabilidade de inteligência artificial.**
6. Confira resposta, execução e credenciais sem copiar conteúdo privado para logs.
7. No Langfuse, localize `n8n-ollama-observability`, sessão derivada, observação pai e gerações filhas. Confira modelo, input/output sintéticos, latência e uso real de cada geração.
8. Confira `overall_quality` entre 0 e 1, justificativa, geração do avaliador e métricas do subworkflow. A latência do monitor informa se mede agente ou workflow completo.
9. No Dashboard/Metrics, agrupe uso por modelo e compare com as gerações. O pai não deve duplicar contadores. Contadores ausentes precisam aparecer como indisponíveis, não zero.
10. Teste duas sessões simultâneas: as correlações não podem compartilhar registros. Repetir a mensagem na mesma sessão mantém a sessão, mas cria execution/trace ID novos.

## Smoke test de serviços

`scripts/test-integration.py` faz inferência sintética pelo proxy e consulta seus contadores. Recebe `PROXY_API_KEY` e `TOKEN_QUERY_API_KEY` no ambiente do processo. **Não lê `.env` automaticamente.** Defina-os por seu gerenciador de segredos ou prompt local sem compartilhar o terminal.

```powershell
py -3 scripts/test-integration.py --model NOME_DO_MODELO --proxy-url http://localhost:18003
```

```bash
python3 scripts/test-integration.py --model NOME_DO_MODELO --proxy-url http://localhost:18003
```

Com `--langfuse-url http://localhost:13000` e `LANGFUSE_PUBLIC_KEY`/`LANGFUSE_SECRET_KEY` no ambiente, o script também envia um trace e score **sintéticos**. Aceitação HTTP não comprova ingestão final/dashboard; confira na UI. Esse teste não executa o workflow n8n nem substitui a demonstração completa.

Resultados efetivamente executados e pendências ficam em [validacao.md](validacao.md).
