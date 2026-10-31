# Resolução de problemas

| Sintoma | Verificação |
| --- | --- |
| Docker indisponível | Inicie Docker Desktop/Engine e confira permissões e `docker info`. |
| Porta ocupada | Ajuste a porta no `.env` novo; não pare o serviço que já utiliza a porta. |
| 401 no modelo | Credencial OpenAI deve usar chave do proxy e URL dele com `/v1`. |
| 401 na consulta | Header exato `X-Token-Query-Key`, com chave de consulta diferente da chave de inferência. |
| 403 no proxy | Rota fora da lista permitida. Pull/delete de modelos não passam por este proxy. |
| 429 | Limite de concorrência atingido; aguarde ou dimensione conscientemente. |
| 502 / Ollama indisponível | Confira `OLLAMA_URL`, DNS e redes de cada container. |
| Modelo não encontrado | Execute `ollama list` no serviço escolhido; obtenha o modelo com consentimento. |
| Falta de memória | Reduza modelo/contexto e confira RAM Docker. Não remova volumes para tentar resolver. |
| Tokens indisponíveis | Verifique uso final da API, correlação dinâmica, resposta incompleta, limites e retenção. Não estime como consumo real. |
| Trace ausente | Confira Basic Auth do mesmo projeto, URL, header de ingestão v4, saúde do worker e permissões. |
| Input/output omitidos | `capture_content` é falso por padrão; habilite apenas com dados sintéticos. |
| Score ausente | Confira `evaluate`, compatibilidade do modelo, JSON de avaliação e validação 0–1. Erros não geram score fictício. |
| Uso não aparece no dashboard | Confira geração, modelo e `usage_details`, projeto e janela de tempo; aguarde ingestão. |
| Subworkflow não chamado | Selecione o workflow importado, habilite o nó e confira permissões de chamada. |
| Monitor 401/404 | Chave n8n local, URL alcançável e execution ID recebido do principal. |
| Code node bloqueia crypto | Autorize builtin `crypto` no ambiente correto do executor n8n conforme sua política. |
| Erro de versão de nó | Use n8n 2.41.7 como referência e valide antes de migrar versões. |

Não compartilhe `docker inspect`, `compose config` expandido, `.env` ou logs completos com segredos. As instruções de diagnóstico nunca exigem exportar conversas reais. Nenhum procedimento de instalação deste projeto depende de reiniciar ou remover serviços de outro projeto.
