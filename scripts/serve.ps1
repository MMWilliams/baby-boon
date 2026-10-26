param([string]$Model = 'pilot-v1', [int]$Port = 11438, [int]$Threads = 6)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$runtimePath = Join-Path $projectRoot 'tools/llama/runtime/llama-server.exe'
$modelPath = Join-Path $projectRoot "models/$Model/model-q4_k_m.gguf"
if (-not (Test-Path -LiteralPath $modelPath)) { throw 'Pilot GGUF is not exported yet.' }
& $runtimePath -m $modelPath -t $Threads -tb $Threads -ngl 0 -c 2048 -np 1 --host 127.0.0.1 --port $Port --no-webui --jinja
exit $LASTEXITCODE
