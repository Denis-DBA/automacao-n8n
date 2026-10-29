# Testes automatizados

Requer Python 3.10+ e pytest 9.2.0. Os testes leem todos os JSONs de
`workflows/` e validam sintaxe, estrutura minima e identidade dos nos.
Nao executam n8n, chamadas HTTP, bancos ou modelos de IA. Os exemplos de
treinamento com falhas intencionais continuam incluidos apenas nesta
validacao estrutural; comportamento funcional e conexoes serao outra etapa.

Na raiz do repositorio, em PowerShell, usando o ambiente ja existente:

```powershell
.\qa\.venv\Scripts\python.exe -m pytest
.\qa\.venv\Scripts\python.exe -m pytest --junitxml=qa/reports/pytest-results.xml
```

Para recriar o ambiente em outra maquina:

```powershell
py -m venv qa/.venv
.\qa\.venv\Scripts\python.exe -m pip install -r qa/requirements.txt
```

Nenhuma dependencia adicional precisa ser instalada no ambiente atual.
Novos exports sao descobertos automaticamente e aparecem pelo caminho no
resultado. Ausencia de exports faz a suite falhar. Relatorios gerados,
ambiente virtual e caches nao devem ser versionados.
