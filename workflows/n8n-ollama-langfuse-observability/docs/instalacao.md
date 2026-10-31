# Instalação e redes

Instale Python 3.12+, Git e Docker com Compose separadamente. Execute `docker info` e `docker compose version`. Não execute o instalador dentro da pasta de um serviço existente. Escolha um nome Docker exclusivo e preserve o `.env` gerado. Reexecuções não sobrescrevem o arquivo e não reiniciam projetos já detectados pelo instalador.

## Modo A

O perfil `full` cria n8n, Ollama, proxy, Langfuse web/worker, Postgres, Redis, ClickHouse e MinIO. Os volumes são prefixados pelo nome Compose. Nenhum usa `external: true`, caminho de dados original ou `container_name` fixo. O usuário n8n é criado na UI. O usuário, projeto e chaves Langfuse são inicializados por `LANGFUSE_INIT_*` em uma instalação nova.

Confira recursos em Docker Desktop antes de iniciar: Langfuse + ClickHouse + n8n + modelo local exigem memória e disco consideráveis. O limite Ollama é 12 GiB no exemplo, não uma promessa de que um modelo caberá. Consulte a página do modelo e ajuste limite/contexto conforme hardware. A imagem Ollama de referência é 0.40.13. O padrão testado é Qwen 3 0.6B, com download de aproximadamente 522 MB. Qwen 3.5 9B permanece como exemplo da instalação de origem; não foi homologado neste stack isolado nem é baixado automaticamente. Outros modelos precisam de teste individual de API, memória e seguimento de instruções.

Comandos manuais após configurar `.env`:

```powershell
docker compose --env-file .env --profile full config --quiet
docker compose --env-file .env --profile full up -d --build --wait --wait-timeout 600
docker compose --env-file .env --profile full ps
docker compose --env-file .env --profile full exec ollama ollama list
```

Os mesmos comandos funcionam em Bash. Para baixar modelo, execute conscientemente `docker compose --env-file .env --profile full exec ollama ollama pull NOME_DO_MODELO`. Pode consumir vários GB e tempo de rede. Nenhum modelo pago/remoto é necessário.

As imagens de infraestrutura e a base Python são fixadas por digest. Confira também o digest do modelo em `models.lock.json`: tags de modelos podem receber pesos novos. Atualize os arquivos de lock somente após repetir os testes.

## Modo B

O instalador inicia apenas o proxy. Todos os endpoints existentes e credenciais são configurados manualmente. Ele verifica saúde do novo proxy e a lista de modelos alcançada por esse proxy. n8n e Langfuse existentes devem ser validados pelas credenciais/testes descritos, sem alterar os containers.

```bash
docker compose --env-file .env config --quiet
docker compose --env-file .env up -d --build --wait token-proxy
docker compose --env-file .env ps
```

No Windows/macOS com Docker Desktop, `host.docker.internal` geralmente alcança o host. No Linux, o Compose inclui `host-gateway` **para o novo proxy**. Isso não adiciona o alias ao n8n já existente. Se necessário, configure rede/endereço adequado ao seu ambiente por procedimento separado autorizado. `localhost` dentro de um container aponta para ele mesmo.

Se os serviços existentes publicam somente em `127.0.0.1`, o acesso pelo gateway Docker pode não funcionar. O modo B não muda essas publicações. Uma opção é planejar uma rede Docker dedicada e anexar o novo proxy à rede apropriada; não anexe serviços atuais sem avaliar seu ambiente. Ajuste URLs nas credenciais n8n e nos nós de configuração.

## Importação

Use arquivos de `generated/` após setup. Se não usou setup, os modelos públicos em `workflows/` precisam de configuração manual. Importe, configure e publique o monitor antes do principal. Abra `Chamar Monitoramento`, selecione o workflow publicado, mantenha `waitForSubWorkflow=true` e habilite o nó. O monitor consulta metadados enquanto o principal ainda está ativo; a resposta explícita ao chat já foi enviada antes dessa chamada. Ele vem desabilitado e sem ID para evitar referência ao ambiente original.

Em uma rede compartilhada, não deixe duas instalações anunciarem o mesmo alias `token-proxy`: o DNS pode resolver para o proxy de outra instalação, que usa outra chave. Prefira redes separadas e endereços exclusivos. O instalador B não conecta serviços automaticamente a redes existentes.

No modo existente, Code nodes precisam de `crypto` autorizado (`NODE_FUNCTION_ALLOW_BUILTIN=crypto` no ambiente de execução dos Code nodes/task runners). Se isso exigir mudança no serviço existente, faça em janela e procedimento próprios; o instalador não realiza essa mudança.

Para manutenção, use sempre o mesmo diretório e `--env-file`. `compose config` sem `--quiet` pode exibir segredos expandidos: não compartilhe a saída. Não use comandos de remoção de volumes em instalações com dados a preservar.
