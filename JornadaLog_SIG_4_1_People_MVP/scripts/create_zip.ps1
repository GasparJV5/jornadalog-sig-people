$root = Split-Path -Parent $PSScriptRoot
$dest = Join-Path (Split-Path -Parent $root) "JornadaLog_SIG_4_0_People_MVP.zip"
if (Test-Path $dest) { Remove-Item $dest }
Compress-Archive -Path "$root\*" -DestinationPath $dest
Write-Host "ZIP criado em $dest"
