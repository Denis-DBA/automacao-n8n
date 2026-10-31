# Credenciais por instalação

Nenhum ID de credencial é distribuído nos workflows. Crie e selecione as credenciais na UI n8n; não cole valores nos JSONs ou em Code nodes.

| Credencial | Configuração | Nós |
| --- | --- | --- |
| OpenAI API para Ollama | API Key = `PROXY_API_KEY` local; Base URL = `http://token-proxy:8003/v1` no modo A | Modelo principal e avaliador |
| Header Auth de consulta | Name = `X-Token-Query-Key`; Value = `TOKEN_QUERY_API_KEY` local | Consultas de tokens principal e avaliador |
| Basic Auth Langfuse | User = chave pública do projeto; Password = chave secreta do mesmo projeto | Registro de trace, uso do avaliador, score e métricas no monitor |
| Header Auth API n8n | Name = `X-N8N-API-KEY`; Value = chave criada na UI desta instância | Consultar Execução n8n |
| Header Auth Slack, opcional | Name = `Authorization`; Value = `Bearer` seguido do token do bot, com `chat:write` | Slack — Alerta Opcional |

No modo B, troque a Base URL pelo endereço que o n8n alcança para o proxy, incluindo `/v1`. Evite o endpoint padrão do provedor OpenAI. Ambos os modelos usam Chat Completions; Responses API permanece desligada.

No modo A, as chaves Langfuse são as `LANGFUSE_INIT_PROJECT_PUBLIC_KEY` e `LANGFUSE_INIT_PROJECT_SECRET_KEY` geradas no `.env` local. Esse arquivo também contém senha inicial Langfuse e chave de criptografia n8n. Não remova a chave de criptografia com credenciais salvas. Consulte os valores somente em seu editor local, sem registrá-los em terminal compartilhado, issues ou screenshots.

A API n8n exige criação manual da chave pelo proprietário na UI. A disponibilidade de permissões granulares depende da edição; conceda somente leitura de execuções quando suportada. O monitor não precisa do conteúdo das execuções.

O chat é uma demonstração local. Mantenha a porta em loopback e use o chat de teste da UI autenticada. Para disponibilizar chat público, configure autenticação e proteção na implantação antes de ativar acesso externo. Simple Memory não substitui gestão de identidade.

Para habilitar Slack: configure a credencial, informe `slack_channel` no nó `Configurar Monitoramento`, ajuste o limiar e habilite conscientemente o nó opcional. O projeto não envia mensagens Slack durante os testes locais.

Conteúdo/justificativa permanecem omitidos por padrão. Para ver input, output e justificativa na UI Langfuse, ative `capture_content` somente após revisar privacidade e use a mensagem sintética. O score numérico pode continuar habilitado com conteúdo omitido. A sanitização é parcial e exige revisão humana antes de usar dados reais.
