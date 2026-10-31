# Arquitetura e decisões

O chat cria uma execução n8n; `Tokens - Identificar Execução` cria a correlação antes da inferência. O subnó de modelo envia `correlation_id` em extra body ao endpoint compatível OpenAI do proxy. O proxy remove esse campo antes de enviar ao Ollama, autentica o cliente e nunca encaminha seus segredos ao upstream.

SSE/NDJSON é encaminhado preservando conteúdo. Contadores nativos (`prompt_eval_count`, `eval_count`) ou compatíveis (`usage.prompt_tokens`, `usage.completion_tokens`) são capturados. Completude exige fim normal da resposta HTTP e contadores válidos. Interrupções, erro de transporte, resposta sem uso ou falha upstream geram estado `unavailable`; não zero nem estimativa.

Persistência utiliza arquivos JSONL diários, contadores e metadados mínimos, com deduplicação por request ID na consulta. A trava é local ao processo e o volume deve ser exclusivo desta instância. Retentativas do cliente são requisições novas e seu consumo real é somado. O projeto não oferece idempotência de geração, quotas por usuário ou banco de contabilidade financeira.

O agente pai envia input/output controlados por opt-in; gerações filhas recebem uso real. Cada geração é associada ao modelo reportado no Ollama. Os spans de geração usam a janela temporal do agente: ainda não há timestamp individual de cada chamada no workflow. Latência por requisição não deve ser inferida desses spans. O avaliador usa janela do início do agente até sua conclusão, e correlação separada.

O subworkflow recebe trace ID, span ID, sessão derivada e execution ID do principal. Consulta somente estado/duração na API n8n. Não acessa PostgreSQL adicional e não estima tokens. O alerta opcional passa somente identificador técnico, sem conteúdo de conversa.

O hash de sessão evita publicar diretamente o sessionId, mas é determinístico e não equivale a anonimização irreversível. Use IDs de sessão sintéticos/aleatórios. ID de trace/span usa `crypto.randomBytes`, sem reutilização de IDs locais.

Avaliação falha sem produzir score inventado. Falhas no envio de telemetria usam saída regular para manter a resposta ao chat; verifique explicitamente resultados de HTTP e UI, pois o chat responder não prova que a telemetria chegou. Falhas de validação de tokens inconsistentes interrompem o fluxo para impedir números incorretos.
