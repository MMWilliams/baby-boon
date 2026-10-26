# Self-contained CPU benchmark for the target laptop: needs only this folder (runtime\llama-server.exe + DLLs and
# model-q4_k_m.gguf), no Python. Writes laptop-bench.json next to this script; send that file back.
param([int]$Threads = 0, [int]$Port = 11438)
$ErrorActionPreference = 'Stop'
$here = $PSScriptRoot
$server = Join-Path $here 'runtime\llama-server.exe'
$model = Join-Path $here 'model-q4_k_m.gguf'
$cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
if ($Threads -le 0) { $Threads = [int]$cpu.NumberOfCores }
$system = 'You are Baby Boon, a conversational AI. Be warm, natural, concise and attentive to the user''s actual words. ' +
  'Usually reply in one to three short sentences. After your conversational reply, append one newline and <cue>tone|expression|intensity.'
$prompts = @('Long day. Say something nice, just a sentence.', 'My roommate keeps eating my leftovers. How do I bring it up?',
  'Tell me a quick fun fact about octopuses.', 'I just got the job!', 'Can you help me plan a cheap dinner for four?',
  'I''m nervous about my exam tomorrow.', 'Okay, that''s all for tonight. Bye.', 'What''s a good name for a goldfish?')

function Invoke-Stream($text) {
  $body = @{ messages = @(@{ role = 'system'; content = $system }, @{ role = 'user'; content = $text }); max_tokens = 128
    temperature = 0; seed = 0; stream = $true; chat_template_kwargs = @{ enable_thinking = $false } } | ConvertTo-Json -Depth 5
  $request = [System.Net.HttpWebRequest]::Create("http://127.0.0.1:$Port/v1/chat/completions")
  $request.Method = 'POST'; $request.ContentType = 'application/json'; $request.Timeout = 120000
  $bytes = [System.Text.Encoding]::UTF8.GetBytes($body)
  $watch = [System.Diagnostics.Stopwatch]::StartNew()
  $stream = $request.GetRequestStream(); $stream.Write($bytes, 0, $bytes.Length); $stream.Close()
  $reader = New-Object System.IO.StreamReader($request.GetResponse().GetResponseStream())
  $first = $null; $content = ''; $timings = $null
  while (($line = $reader.ReadLine()) -ne $null) {
    if (-not $line.StartsWith('data: ') -or $line -eq 'data: [DONE]') { continue }
    $event = $line.Substring(6) | ConvertFrom-Json
    if ($event.timings) { $timings = $event.timings }
    $part = $event.choices[0].delta.content
    if ($part) { if ($null -eq $first) { $first = $watch.Elapsed.TotalMilliseconds }; $content += $part }
  }
  $reader.Close()
  [pscustomobject]@{ prompt = $text; reply = $content; first_content_ms = [math]::Round($first); total_ms = [math]::Round($watch.Elapsed.TotalMilliseconds)
    decode_tok_s = [math]::Round($timings.predicted_per_second, 1); tokens = $timings.predicted_n }
}

$proc = Start-Process $server -ArgumentList '-m', "`"$model`"", '-t', $Threads, '-tb', $Threads, '-ngl', '0', '-c', '2048', '-np', '1',
  '--host', '127.0.0.1', '--port', $Port, '--no-webui', '--jinja' -WindowStyle Hidden -PassThru
try {
  $loaded = [System.Diagnostics.Stopwatch]::StartNew()
  while ($true) {
    try { if ((Invoke-RestMethod "http://127.0.0.1:$Port/health" -TimeoutSec 2).status -eq 'ok') { break } } catch {}
    if ($proc.HasExited) { throw 'llama-server exited during load' }
    if ($loaded.Elapsed.TotalSeconds -gt 180) { throw 'llama-server did not load within 180 s' }
    Start-Sleep -Milliseconds 500
  }
  $loadSeconds = [math]::Round($loaded.Elapsed.TotalSeconds, 1)
  Invoke-Stream 'Hi.' | Out-Null  # warm-up
  $runs = foreach ($p in $prompts) { Invoke-Stream $p; Write-Host '.' -NoNewline }
  Write-Host ''
  $proc.Refresh()
  $first = @($runs.first_content_ms | Sort-Object)
  $os = Get-CimInstance Win32_OperatingSystem
  $result = [ordered]@{
    machine = [ordered]@{ cpu = $cpu.Name.Trim(); cores = $cpu.NumberOfCores; logical = $cpu.NumberOfLogicalProcessors
      ram_gib = [math]::Round($os.TotalVisibleMemorySize / 1MB, 1); os = $os.Caption; threads_used = $Threads }
    model_mib = [math]::Round((Get-Item $model).Length / 1MB); load_seconds = $loadSeconds
    peak_rss_mib = [math]::Round($proc.PeakWorkingSet64 / 1MB)
    median_decode_tok_s = (@($runs.decode_tok_s | Sort-Object))[[int][math]::Floor($runs.Count / 2)]
    p95_first_content_ms = $first[[int][math]::Ceiling(0.95 * $first.Count) - 1]
    targets = 'peak RSS <= ~2 GB, decode >= 20 tok/s, p95 first content <= 500 ms'
    runs = $runs }
  $out = Join-Path $here 'laptop-bench.json'
  $result | ConvertTo-Json -Depth 5 | Out-File $out -Encoding utf8
  "$($result.machine.cpu): $($result.median_decode_tok_s) tok/s median, p95 first content $($result.p95_first_content_ms) ms, peak RSS $($result.peak_rss_mib) MiB"
  "Wrote $out"
} finally { if (-not $proc.HasExited) { Stop-Process -Id $proc.Id -Force } }
