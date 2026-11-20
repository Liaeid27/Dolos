#Requires -RunAsAdministrator
$ErrorActionPreference = 'Stop'
$null = Get-NetAdapter -Name Tailscale
$exe = Join-Path $env:ProgramFiles 'Apollo\sunshine.exe'
if (!(Test-Path -LiteralPath $exe)) {throw 'Pfad zu Apollo prüfen.'}
foreach ($rule in @(@{Name='DolosRemoteStreamTCP';Protocol='TCP';LocalPort=@('47984','47989','48010');Program=$exe},@{Name='DolosRemoteStreamUDP';Protocol='UDP';LocalPort=@('47998-48000','48002','48010');Program=$exe},@{Name='DolosRemoteVerwaltung';Protocol='TCP';LocalPort='48291'})) {
    if (!(Get-NetFirewallRule -Name $rule.Name -ErrorAction SilentlyContinue)) {
        New-NetFirewallRule @rule -DisplayName $rule.Name -InterfaceAlias Tailscale -Direction Inbound -Action Allow -Profile Any -RemoteAddress '100.64.0.0/10' | Out-Null
    }
}
