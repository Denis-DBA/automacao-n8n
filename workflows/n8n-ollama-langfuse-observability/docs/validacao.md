# Relatório de validação completa

Data: 31/10/2026. Windows, Docker Desktop (Engine 29.8.2 / Compose 5.5.1), containers Linux/amd64, n8n 2.41.7, Ollama 0.40.13 e Langfuse 4 nas imagens registradas em `images.lock.json`. Modelo efetivamente testado: `qwen3:0.6b` (522 MB de download). A VM tinha aproximadamente 20 GiB e 8 CPUs disponíveis; isso descreve o ambiente, não um requisito mínimo garantido.

Foram criados projetos, portas, credenciais, redes e volumes exclusivos. Nenhum volume/banco ou segredo da instalação original foi utilizado. Os originais foram conferidos por ID, estado, horário de início, contador de reinícios e configuração de mounts: 25 containers preexistentes permaneceram iguais ao baseline.

## Testes aprovados

| Teste | Evidência |
| --- | --- |
| Suíte automatizada | 19 testes Python, incluindo regressões dos erros reais encontrados |
| Sintaxe e estrutura | Python, JSON, referências/conexões, JavaScript e expressões n8n; PowerShell e Bash |
| Build do proxy | Python 3.12, usuário UID 10001, contexto sem ambientes/dados e filesystem somente leitura |
| Compose completo | Nove serviços novos inicializados; health checks existentes aprovados e worker em execução |
| Instalador A real, cópia limpa | Nove serviços, volumes novos, ausência inicial de modelos aceita; recusa do download respeitada |
| Instalador B real | Somente um proxy novo; comunicação com o Ollama da infraestrutura de testes |
| Reexecução dos instaladores | `.env` preservado e nenhum container de outro projeto reiniciado |
| Wrapper PowerShell | Configuração sem inicialização executada; preservação de ambiente e containers conferida |
| Workflows n8n | Importados, credenciais próprias vinculadas e monitor publicado antes do principal |
| Inferência e resposta ao chat | Mensagens sintéticas respondidas pelo Ollama isolado; somente campo output devolvido |
| SSE e NDJSON reais | Contadores finais conferidos contra a resposta do Ollama |
| Cancelamento e erro upstream | Consumo indisponível, com totais null, sem assumir zero |
| Auth e rotas | Inferência/consulta sem chave recusadas; operações administrativas bloqueadas |
| Conteúdo habilitado por opt-in | 3 chats, 2 sessões, 3 traces, 6 gerações, 3 scores e 3 observações do monitor |
| Privacidade padrão | Mesmo conjunto funcional aprovado com input/output omitidos |
| Tokens e métricas | Contadores por request ID iguais no proxy e Langfuse; agregação por modelo igual aos totais, sem soma duplicada no agente pai |
| Sessões e concorrência | Duas sessões simultâneas separadas, sessão repetida estável, traces/requests distintos |
| Monitoramento | Consulta API n8n includeData=false enquanto o principal está ativo; span correlacionado e latência de escopo agent |
| Retenção no n8n | Execuções sintéticas concluídas ausentes da listagem com a política de não salvar conversas |

Os dois ensaios ponta a ponta tiveram, respectivamente, 1.748 e 1.727 tokens reais, incluindo agente e avaliador. Esses números são resultados de teste e não previsão de consumo. Os dados agregados estão em [resultados-sinteticos.json](resultados-sinteticos.json), sem chaves, conversas ou histórico de traces.

## Falhas reproduzidas e correções

| Falha inicial | Correção e resultado da repetição |
| --- | --- |
| Health check Langfuse recusado em localhost | HOSTNAME=0.0.0.0; health interno/externo e instalação limpa aprovados |
| Principal não publica com monitor não publicado | Ordem explícita: configurar/publicar monitor antes do principal; ativação aprovada |
| Monitor assíncrono consultava execução já descartada | Chamada síncrona, sem espera artificial; consulta de snapshot aprovada sem salvar conversas |
| Resultado interno/vazio podia chegar ao chat ao terminar subworkflow | Resposta explícita antes da chamada aninhada; teste exige exatamente output |
| Avaliações podiam não produzir JSON válido | Modo JSON e reasoning_effort=none no avaliador testado; validação continua recusando valores inválidos |
| Instalação vazia retornava lista de modelos null | Instalador aceita lista vazia e respeita ausência de consentimento para download; regressão e nova instalação limpa aprovadas |
| Filtro temporal do teste não achava traces da VM | Validador usa HTTP Date do servidor; nenhuma alteração nos relógios dos sistemas |
| Proxy extra de teste compartilhou alias na mesma rede | Caso adicional encerrado após seu ensaio; testes ponta a ponta repetidos com DNS isolado; limitação de redes documentada |
| Diretório temporário global do pytest bloqueado no sandbox | Repetição com diretório temporário exclusivo no workspace: 19 aprovados |

As falhas acima não estão sendo classificadas como aprovações iniciais. Os resultados aprovados correspondem às repetições após correção. Os digests das imagens e a base Python foram fixados após validação; o instalador limpo final usou essas referências. `models.lock.json` registra o digest dos pesos testados: a tag do modelo pode mudar e deve ser conferida antes de afirmar igualdade dos pesos.

## Segurança e limites

A auditoria cobre o código, workflows, Compose, instaladores, documentação e exemplos candidatos à publicação. Não foram incluídos ambientes reais, credenciais/IDs locais, pinData, backups, dados de execução, logs JSONL ou volumes. A revisão final examinou os 42 arquivos públicos no índice Git com `detect-secrets`: zero achados após identificar um checksum de modelo como falso positivo e representá-lo com prefixo explícito sha256. Não houve novo allowlist de credenciais. A consulta final com `pip-audit` não encontrou vulnerabilidades conhecidas nas dependências Python fixadas. Whitespace/diff do índice também foram verificados antes do commit.

## Não executados / não homologados

- Envio real de Slack: opcional, desabilitado, sem token/canal de teste autorizado.
- Instalação nativa em Linux/macOS, ARM64 e aceleração GPU: não havia esses ambientes dedicados; Bash teve validação de sintaxe, não instalação completa nesses sistemas.
- Outros modelos, inclusive Qwen 3.5 9B, outras versões n8n/Langfuse e operação distribuída: não homologados.
- Auditoria completa de CVEs de imagens e dependências npm: não executada; pinagem e auditoria Python não a substituem.
- Navegação visual manual no dashboard: não executada; observações, sessões, scores, conteúdo e agregações foram confirmados pelas APIs v4 que alimentam a UI.

A instalação e o fluxo foram reproduzidos na configuração descrita. A configuração inicial de credenciais n8n, conta proprietária e associação/publicação dos workflows continua manual. Portanto não se promete instalação universal sem configuração nem funcionamento idêntico em plataformas/modelos não testados. Não houve merge na main.
