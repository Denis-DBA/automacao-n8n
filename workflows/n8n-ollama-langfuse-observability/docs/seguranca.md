# Segurança e auditoria da versão pública

Revisão estática dos dois JSONs originais, sete arquivos de código/configuração do proxy original e somente nomes de variáveis de seu `.env`. Os originais permanecem locais. Nenhum valor secreto do `.env` original foi utilizado, copiado ou incluído nesta distribuição.

## Correções na cópia pública

- Credenciais, IDs locais de credenciais, workflow IDs de instância, webhooks privados, `meta`, `versionId` e dados fixados removidos.
- Nomes e referências de CRM/WhatsApp removidos. Monitoramento não depende mais do banco adicional original.
- Autenticação de inferência e consulta separadas; startup recusa chaves fracas por comprimento ou iguais.
- Lista de rotas/métodos, limite de corpo/buffer/concurrency e timeout de inferência.
- Headers de credenciais/cookies não enviados ao upstream. Erros de conexão não registram URL/segredos.
- Retenção e teto de disco para contadores. Respostas incompletas não são registradas como zero.
- Usuário sem privilégios, filesystem somente leitura e capacidades removidas no proxy.
- Contexto de build permite somente código, Dockerfile e dependências.
- Conteúdo omitido por padrão; sucesso/erro de execuções não são persistidos por configuração do exemplo.
- APIs internas sem portas de host; interfaces de laboratório publicadas somente em loopback.
- `.env.example` sem segredos, ambientes reais/backups/dados/volumes ignorados pelo Git.

## Limites e operação

Não há garantia de anonimização de conteúdo habilitado por opt-in. Hash de sessão é pseudônimo. O chat local e memória não devem ser expostos como serviço multiusuário de produção. O exemplo não implementa gestão de usuários do proxy, quotas individuais ou rate limiting distribuído.

HTTP é usado na rede local de demonstração; implantações remotas exigem TLS e proteção de rede. O instalador modo B não modifica serviços existentes para aplicar essas políticas.

As evidências de instalação não homologam exposição pública. Mantenha interfaces em loopback, chat autenticado quando publicado, conteúdo omitido por padrão e segredos próprios por instalação. Não há credenciais ou dados originais a reutilizar para completar o setup. A primeira configuração está detalhada no [roteiro de primeira execução](primeira-execucao.md).

O proxy usa um único worker e volume exclusivo. A retenção pode excluir dados para respeitar o teto de disco. O controle de concorrência protege recursos, mas não substitui proteção contra tráfego abusivo antes do container. Rotação de credenciais exige atualizar consumidores e reiniciar somente a nova instalação em janela própria.

As regras Git não removem arquivos já rastreados ou histórico. A revisão de publicação cobre os arquivos novos e os diffs staged; não é auditoria integral do histórico e dos demais projetos. Não trate ausência de achado como prova universal de ausência de segredos.

Versões Python e digests das imagens de infraestrutura/base foram fixados. Atualizações exigem revisão explícita e repetição dos testes. Isso não substitui auditoria de vulnerabilidades de imagens ou dependências npm. O Chat Trigger também desabilita o salvamento automático de campos destacados. Resultados das ferramentas e verificações do índice Git constam em [validação](validacao.md).
