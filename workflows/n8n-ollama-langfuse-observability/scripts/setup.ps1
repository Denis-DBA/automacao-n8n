param([switch]$ConfigureOnly)
$ErrorActionPreference = 'Stop'
$pythonArgs = @((Join-Path $PSScriptRoot 'setup.py'))
if ($ConfigureOnly) { $pythonArgs += '--configure-only' }
if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 @pythonArgs
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    & python @pythonArgs
} else {
    throw 'Instale Python 3.12+ e Docker com Compose. O instalador não instala programas do sistema.'
}
if ($LASTEXITCODE -ne 0) { throw 'Configuração ou instalação não concluída. Consulte as instruções e tente novamente.' }
