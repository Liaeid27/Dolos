$ErrorActionPreference='Stop'
$src=Join-Path $PSScriptRoot 'steam_aktion.py'
$folder=Join-Path $env:ProgramFiles 'Apollo\config'
$dst=Join-Path $folder 'aster-steam-aktion.py'
if(!(Test-Path -LiteralPath $dst -PathType Leaf)){throw 'Dolos-Spiele in Apollo zuerst über Store aktualisieren einrichten.'}
if((Get-FileHash -LiteralPath $dst).Hash -eq (Get-FileHash -LiteralPath $src).Hash){return}
$tmp=Join-Path $folder ('dolos-'+[guid]::NewGuid().ToString()+'.tmp')
Copy-Item -LiteralPath $src -Destination $tmp
[IO.File]::Replace($tmp,$dst,(Join-Path $folder 'aster-steam-aktion.vor-update.bak'))
