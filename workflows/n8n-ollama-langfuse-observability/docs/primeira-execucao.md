# Primeira execução e aceite da instalação

Este roteiro usa o modo A e os valores padrão de portas/modelo. O ambiente validado é Windows com Docker Desktop e containers Linux/amd64. Para serviços existentes, siga as diferenças de rede do [modo B](instalacao.md). Não execute comandos em diretórios de outros projetos.

## 1. Preparar e iniciar

Na pasta `workflows/n8n-ollama-langfuse-observability`, execute:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup.ps1
```

Em Linux/macOS, há o wrapper `bash scripts/setup.sh`; sua sintaxe foi verificada, mas a instalação completa nesses sistemas não foi homologada.

Escolha A, um nome Docker exclusivo e portas livres. Autorize separadamente a criação dos serviços e o download do modelo. Preserve o `.env` gerado: contém segredos exclusivos desta instalação. Não copie o ambiente, banco ou volumes de outro projeto.

Confira o estado e o modelo, usando as mesmas variáveis locais:

```powershell
docker compose --env-file .env --profile full ps
docker compose --env-file .env --profile full exec ollama ollama list
```

Se `qwen3:0.6b` não estiver instalado, o teste de inferência ainda não está pronto. Seu download, autorizado conscientemente, é feito com:

```powershell
docker compose --env-file .env --profile full exec ollama ollama pull qwen3:0.6b
```

Esses comandos Docker também funcionam em Bash. Os digests das imagens e do modelo de referência estão em `images.lock.json` e `models.lock.json` na raiz do projeto.

## 2. Acessar as interfaces

| Interface | URL padrão | Configuração inicial |
| --- | --- | --- |
| n8n | http://localhost:15678 | Crie a conta proprietária na UI desta instância |
| Langfuse | http://localhost:13000 | Use o login e a senha definidos por `LANGFUSE_INIT_USER_EMAIL` e `LANGFUSE_INIT_USER_PASSWORD` no seu `.env` |
| Proxy | http://localhost:18003/health | Deve responder com status ok; a inferência e a consulta de tokens exigem chaves diferentes |

Consulte os segredos somente no seu editor/gerenciador local. Não os cole nos JSONs, terminal compartilhado, documentação ou issues. Se mudou as portas, use as escolhidas no instalador.

## 3. Configurar as credenciais

Na UI n8n, crie as quatro credenciais obrigatórias da tabela de [credenciais](credenciais.md): OpenAI API apontando para o proxy Ollama, Header Auth de consulta de tokens, Basic Auth do projeto Langfuse e Header Auth da API n8n. A chave da API n8n é criada manualmente na sua instância. Slack é opcional e permanece desabilitado.

A credencial OpenAI deve usar a chave do proxy e Base URL `http://token-proxy:8003/v1` no modo A. O nome do tipo de credencial não significa uso do serviço pago OpenAI.

## 4. Importar e publicar na ordem correta

1. Importe `generated/monitoramento-langfuse-ollama.json`.
2. Selecione as credenciais da API n8n e Langfuse nos nós correspondentes. Confira o endereço n8n em `Configurar Monitoramento` e publique o monitor.
3. Importe `generated/n8n-ollama-langfuse-observability.json`.
4. Configure as credenciais dos dois modelos, das duas consultas de tokens e dos nós Langfuse conforme a tabela de credenciais.
5. No nó `Chamar Monitoramento`, selecione o monitor já publicado e habilite o nó. Preserve `waitForSubWorkflow=true`.
6. Confira modelo, endereços, `evaluate=true` e `capture_content=false` em `Configuração da Demonstração`. Publique o principal depois que suas dependências estiverem configuradas.

O chat de teste da UI autenticada é suficiente para a demonstração manual. Para executar `test-e2e.py`, prepare separadamente um chat publicado com Basic Auth e URL própria, conforme [testes](testes.md). Não habilite um chat público sem autenticação para facilitar o teste.

## 5. Aceitar ou diagnosticar

Envie a mensagem sintética: **Explique em três frases o que é observabilidade de inteligência artificial.**

- O chat deve devolver somente a resposta da IA, sem dados internos de telemetria.
- No projeto Langfuse, confira trace `n8n-ollama-observability`, sessão e latência. As gerações do agente e avaliador devem identificar o modelo e seu consumo real; o agente pai não deve duplicar esses contadores.
- Com avaliação habilitada, confira score `overall_quality` entre 0 e 1. Sua justificativa e o conteúdo ficam omitidos por padrão; habilite `capture_content` somente em um ensaio separado com dados sintéticos para inspecioná-los.
- Confira o span `Monitoramento n8n`: a consulta é um snapshot enquanto a execução principal está ativa e a latência padrão tem escopo agent. Isso não é confirmação do estado final nem medida da duração completa do workflow.
- Confira a agregação por modelo. Falta de informação final de uso deve ser tratada como indisponível, sem inventar consumo zero.

Uma resposta no chat ou um HTTP 200 isoladamente não comprovam a ingestão. Para comparação automatizada entre proxy, observações, scores e métricas, use os ensaios documentados em [testes](testes.md). Para falhas, siga [troubleshooting](troubleshooting.md); não recrie volumes como tentativa de correção.

## 6. Retomar esta instalação

Reexecutar o instalador preserva o `.env` e não reinicia containers já detectados. Para iniciar novamente **somente este projeto**, após conferir seu diretório e `COMPOSE_PROJECT_NAME`, use:

```powershell
docker compose --env-file .env --profile full up -d --wait --wait-timeout 600
```

No modo B, omita `--profile full` e selecione apenas `token-proxy`. Não use comandos de remoção de volumes para reiniciar uma instalação. Preserve também a chave de criptografia n8n; alterá-la pode impedir acesso às credenciais salvas.

A [validação existente](validacao.md) registra os testes aprovados, falhas corrigidas e limites. Slack real, outras plataformas/modelos, inspeção visual manual do dashboard e varredura completa de CVEs de imagens/npm não fazem parte da homologação concluída.
