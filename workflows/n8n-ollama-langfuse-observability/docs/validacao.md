# Relatório de validação

Data: 31/10/2026. Testes sem alterações aos containers, volumes ou credenciais da instalação original. Foi criado um projeto Compose exclusivo de validação, com chaves novas e porta distinta. Nenhuma chave original foi lida.

## Executados

| Verificação | Resultado |
| --- | --- |
| Testes Python do proxy, instalador e artefatos | 14 aprovados; upstream simulado, armazenamento temporário |
| Sintaxe Python | Aprovada por AST/compileall |
| JSON e referências de nós | Aprovados: nomes, conexões, referências e ausência de credenciais/dados locais |
| JavaScript de Code nodes e expressões completas | Compilado em Node da imagem n8n 2.41.7 |
| Importação n8n | Dois workflows importados em container descartável sem rede, com SQLite temporário |
| Compose modo A | `docker compose --env-file .env --profile full config --quiet` aprovado com ambiente sintético |
| Build proxy | Construído em Python 3.12, dependências fixadas, usuário UID 10001 |
| Inicialização modo B | Novo proxy saudável em projeto/porta exclusivos; HTTP health 200 |
| Inferência sintética real | Modelo local já disponível respondeu pelo novo proxy; tokens reais consultados por correlação e soma validada; nenhum modelo baixado |
| PowerShell/Bash | Sintaxe aprovada por parser PowerShell e `bash -n` |
| Dependências Python | `pip-audit` sem vulnerabilidades conhecidas para as versões fixadas na data da consulta |
| Detecção de segredos | Revisão de 35 candidatos staged; duas ocorrências iniciais eram o prefixo público de chave gerada e uma URL de teste explicitamente sintética, com allowlist somente nessas linhas |

Os testes de proxy cobrem autenticação, startup sem chave, bloqueio de operações administrativas, headers não encaminhados, correlação separada, soma de múltiplas chamadas, SSE/NDJSON com chunks partidos, interrupção após uso, limites de corpo/buffer, concorrência/429, falha upstream, deduplicação, retenção e limite de armazenamento.

O primeiro build encontrou conflito com um grupo já existente na imagem base; o Dockerfile foi corrigido para usuário/grupo próprio e o build repetido passou. Não se declarou aprovado o build inicial.

## Pendentes e limites de evidência

- Modo A completo com todos os serviços Langfuse e modelo em instalação limpa não homologado. Não foram copiados bancos/volumes nem usados segredos Langfuse existentes para tentar simular esse resultado.
- Execução completa no n8n, configuração de credenciais pela UI, chamada assíncrona do subworkflow e envio/ingestão de traces/scores/dashboards precisam do teste demonstrativo documentado em uma instalação independente.
- O alerta Slack não foi enviado; é opcional, desabilitado e exige credencial/canal próprios.
- Modelos alternativos, aceleração GPU, versões anteriores de n8n e diferentes plataformas Docker não homologados.
- Dependências Python foram auditadas por versão. Imagens e dependências npm do n8n/Langfuse não passaram por scanner completo de CVEs neste trabalho.
- Tags principais Langfuse e algumas imagens de infraestrutura são mutáveis. Fixe digests após homologação do conjunto em seu ambiente; isto limita a reprodução exata futura.

O projeto é apresentado para revisão, sem alegação de Plug & Play validado. Aceitação HTTP e importação não comprovam funcionamento do dashboard. Repita o checklist de `testes.md` antes de divulgar uma instalação como validada.
