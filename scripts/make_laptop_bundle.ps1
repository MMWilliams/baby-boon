# Copy the llama.cpp runtime, one exported GGUF and laptop_bench.ps1 into dist\laptop-bench (plus a zip) for the target laptop.
param([string]$Model = 'pilot-v14-1.7b')
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$dest = Join-Path $root 'dist\laptop-bench'
if (Test-Path $dest) { Remove-Item $dest -Recurse -Force }
New-Item -ItemType Directory -Force (Join-Path $dest 'runtime') | Out-Null
Copy-Item (Join-Path $root 'tools\llama\runtime\*') (Join-Path $dest 'runtime') -Recurse
Copy-Item (Join-Path $root "models\$Model\model-q4_k_m.gguf") $dest
Copy-Item (Join-Path $PSScriptRoot 'laptop_bench.ps1') (Join-Path $dest 'bench.ps1')
"Model: $Model`r`nRun: powershell -ExecutionPolicy Bypass -File bench.ps1`r`nSend back: laptop-bench.json" | Out-File (Join-Path $dest 'README.txt') -Encoding utf8
Compress-Archive -Path "$dest\*" -DestinationPath "$dest.zip" -Force
"Bundle: $dest.zip ($([math]::Round((Get-Item "$dest.zip").Length / 1MB)) MiB)"
