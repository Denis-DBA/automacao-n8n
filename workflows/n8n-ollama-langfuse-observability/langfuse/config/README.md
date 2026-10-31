# Inicialização independente

No modo completo, `LANGFUSE_INIT_*` cria organização, projeto, usuário e chaves novos.
Não importa banco, conversas, traces, scores ou dashboards da instalação original.
O setup gera as chaves no `.env` local; a interface permite revogá-las posteriormente.

O score `overall_quality` é enviado como NUMERIC, de 0 a 1. A justificativa é sanitizada no workflow.
Os tokens são enviados em observações `generation` por requisição, com modelo e
`langfuse.observation.usage_details`. O agente pai não repete os totais, evitando dupla contagem.
No Dashboard/Metrics do projeto, agregue uso por modelo; confirme com o procedimento de testes.

Preços, dashboards personalizados e configurações adicionais de avaliação devem ser criados
na UI desta instalação. Não há importação automática desses recursos neste projeto.
Para modelos locais, não interprete custo de API zero como custo de infraestrutura zero.
