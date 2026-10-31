# Portfólio de Automação e Inteligência Artificial com n8n

## Apresentação

Portfólio de Denis André Ramalho com projetos de automação de processos, integração de sistemas e soluções com Inteligência Artificial desenvolvidas no n8n. Os workflows exploram agentes conversacionais, recuperação de conhecimento com RAG, processamento de documentos e integração com APIs e bancos de dados.

As descrições abaixo resultam da análise estática dos 19 arquivos JSON disponíveis em `workflows/`. A execução e o funcionamento das integrações não foram validados. Credenciais e serviços precisam ser configurados em um ambiente próprio.

## Projetos

### 1. Assistente de Agendamento com Google Calendar

Agente conversacional com Ollama e memória de conversas em PostgreSQL.
O agente utiliza uma ferramenta de chamada a outro workflow para operações de agenda.
O subworkflow contém rotas para criar, consultar, atualizar e excluir eventos no Google Calendar.
Apesar do nome da pasta, os JSONs analisados não contêm nós de cliente ou servidor MCP; a integração utiliza uma ferramenta de subworkflow do n8n.

**Tecnologias:** n8n, agentes de IA, Ollama, PostgreSQL e Google Calendar com OAuth 2.0.

[Ver workflows de agendamento](workflows/agendamento-google-calendar-mcp/)

### 2. Ingestão e Manutenção de Base Vetorial para RAG

Workflow de ingestão acionado pela criação de arquivos em uma pasta do Google Drive.
Realiza download de PDFs, extração de texto, divisão em trechos e geração de embeddings com Ollama para inserção no PostgreSQL com PGVector.
Um segundo workflow, também configurado para o evento de criação de arquivo, executa exclusão de registros por SQL e exclusão de arquivo no Drive.
Os arquivos representam ingestão e limpeza da base; não comprovam uma substituição atômica nem monitoramento de alterações de documentos existentes.

**Tecnologias:** n8n, Google Drive com OAuth 2.0, extração de PDF, Ollama, embeddings, PostgreSQL, PGVector e SQL.

[Ver workflows da base vetorial](workflows/atualizacao-base-vetorial-rag/)

### 3. Atendimento e Cadastro de Leads via WhatsApp com IA

Recebe mensagens por webhook e contém tratamento de texto e áudio, com chamada HTTP a um serviço de transcrição Whisper.
Utiliza Redis para agrupamento de mensagens e controle de atendimento humano, além de PostgreSQL para cadastro e memória conversacional.
O agente com Ollama consulta conhecimento por PGVector e pode acionar um subworkflow de encaminhamento, com geração e envio de resumo ao atendente.
Inclui envio de mensagens por HTTP e um nó Evolution Go; há também um nó MySQL sem conexão de saída, que não é apresentado como integração operacional validada.

**Tecnologias:** n8n, webhooks, HTTP, WhatsApp via Evolution Go, Whisper API, Ollama, PostgreSQL, PGVector, Redis e JavaScript.

[Ver workflows de atendimento e leads](workflows/captacao-leads-whatsapp-ia/)

### 4. Assistentes Especializados com Orquestração e RAG

Dois workflows conversacionais organizam agentes especializados em documentação de n8n, Power BI e Power Automate.
Os agentes usam Ollama, memória em PostgreSQL e ferramentas de consulta a bases vetoriais com PGVector.
Três workflows adicionais coletam conteúdo com Firecrawl, processam os textos com JavaScript e os dividem em trechos para indexação com embeddings.
Power BI e Power Automate são temas das bases de conhecimento; não foram identificadas integrações diretas com suas APIs.

**Tecnologias:** n8n, agentes de IA, RAG, Ollama, embeddings, PostgreSQL, PGVector, Firecrawl e JavaScript.

[Ver workflows multiagente](workflows/multi-agente-rag/)

### 5. Laboratório de Integrações, IA e Tratamento de Erros

Conjunto de oito exercícios com registro em API de treinamento, agente de consulta e processamento de feedback com modelos de linguagem.
Inclui geração de respostas, classificação com saída estruturada e consultas HTTP sobre pedidos, clientes e produtos.
Os exercícios de dados trabalham enriquecimento de pedidos, cálculo de totais, agregação por região e geração de relatório em CSV.
Também inclui cenários de depuração, teste de falhas e tratamento de erros por workflow dedicado; são materiais de estudo, sem validação de execução nesta revisão.

**Tecnologias:** n8n, HTTP, webhooks, Ollama, Groq, modelos de linguagem, saída estruturada e CSV.

[Ver workflows de treinamento](workflows/treinamentos-n8n/)

## Tecnologias

- **Orquestração e integração:** n8n, subworkflows, webhooks, HTTP e OAuth 2.0.
- **Inteligência Artificial:** agentes e ferramentas de IA do n8n, Ollama, Groq, embeddings, RAG e transcrição por API Whisper.
- **Persistência:** PostgreSQL, PGVector e Redis. MySQL aparece em um nó isolado do projeto de leads.
- **Serviços integrados:** Google Calendar, Google Drive, Firecrawl e Evolution Go para mensagens de WhatsApp.
- **Processamento de dados:** JavaScript, SQL, extração de PDF, divisão de texto, agregações e exportação CSV.

O título anterior deste repositório destacava automação local com n8n, Ollama e MongoDB. n8n e Ollama estão presentes nos projetos atuais; não foram identificados nós MongoDB nos JSONs analisados.

## Configuração e sanitização dos workflows

Os JSONs foram revisados e os valores sensíveis identificados foram substituídos por exemplos: possíveis chaves de API, contatos, endereço de calendário, URLs locais, referências a pastas do Google Drive e identificadores de avaliações. No prompt do agente de leads, somente o endereço de e-mail foi substituído; as instruções foram preservadas.

Antes de executar os exemplos, configure as credenciais no n8n e substitua os marcadores, como `SUBSTITUA_PELA_CHAVE_DA_API`, `SUBSTITUA_PELA_CHAVE_DA_INSTANCIA`, `ID_PASTA_GOOGLE_DRIVE_EXEMPLO`, `ASSESSMENT_ID_EXEMPLO` e os contatos de exemplo. Endereços em `example.invalid` são ilustrativos e devem ser trocados pelos serviços do seu ambiente.

A estrutura dos nós, as conexões, os IDs internos, as referências de credenciais e o código JavaScript foram preservados. Referências de credenciais não contêm, por si só, as respectivas senhas. Os 19 JSONs tiveram a sintaxe validada, sem execução de workflows ou chamadas externas.

O `.gitignore` protege arquivos auxiliares locais, mas não remove informações embutidas nos JSONs nem no histórico do Git. A revisão realizada se aplica aos arquivos locais atuais; o histórico do repositório não foi inspecionado.

## Autor

**Denis André Ramalho**

- GitHub: [Denis-DBA](https://github.com/Denis-DBA)
- LinkedIn: [Denis André Ramalho](https://www.linkedin.com/in/denis-andré-ramalho-8615b6158)

## n8n Ollama Langfuse — Observability

Laboratório independente de observabilidade de IA local, com proxy de tokens reais, workflows n8n e integração OTLP com Langfuse. Inclui instaladores e dois modos de implantação. A validação completa de instalação limpa permanece pendente; consulte o relatório antes de instalar.

[Ver projeto e validação](workflows/n8n-ollama-langfuse-observability/)
