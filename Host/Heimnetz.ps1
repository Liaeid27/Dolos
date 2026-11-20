$ErrorActionPreference = 'Stop'
$exe = Join-Path $env:ProgramFiles 'Apollo\sunshine.exe'
if (!(Test-Path -LiteralPath $exe)) {throw 'Apollo wurde im Standardordner nicht gefunden. Den installierten Host in der privaten Windows-Firewall freigeben.'}
if (!(Get-NetFirewallRule -Name DolosApolloPrivat -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -Name DolosApolloPrivat -DisplayName 'Dolos - Apollo im privaten Heimnetz' -Program $exe -Direction Inbound -Action Allow -Profile Private -RemoteAddress LocalSubnet | Out-Null
}
if (!(Get-NetFirewallRule -Name DolosLAN -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -Name DolosLAN -DisplayName 'Dolos TV im Heimnetz' -Direction Inbound -Action Allow -Profile Private -Protocol TCP -LocalPort 48291 -RemoteAddress LocalSubnet | Out-Null
}
Write-Output 'Apollo und Dolos sind fuer das lokale Subnetz im privaten Netzprofil freigegeben.'
