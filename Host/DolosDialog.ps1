﻿param([Parameter(Mandatory)][string]$SteamRoot,[Parameter(Mandatory)][string]$Title,[ValidateSet('inspect','confirm','cancel','install','launch','terms','accept')][string]$Action='inspect',[string]$Expected='')
$ErrorActionPreference='Stop'
[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false)
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$tree=[Windows.Automation.AutomationElement]::RootElement
$all=[Windows.Automation.Condition]::TrueCondition
$rootPath=[IO.Path]::GetFullPath($SteamRoot).TrimEnd('\')+'\'
$buttons='^(Installieren|Install|Deinstallieren|Uninstall|Entfernen|Remove|Weiter|Next|Abbrechen|Cancel)$'
if($Action -eq 'launch'){$buttons='^(Play|Spielen|Starten|Launch|Abbrechen|Cancel)$'}
if($Action -in @('terms','accept')){$buttons='^(Ich stimme zu|Ich akzeptiere|Zustimmen|Akzeptieren|I agree|I accept|Accept|Agree)$'}
foreach($w in $tree.FindAll([Windows.Automation.TreeScope]::Children,$all)){
 try {
    $proc=Get-Process -Id $w.Current.ProcessId -ErrorAction Stop
    if ($proc.Name -notin @('steam','steamwebhelper') -or !$proc.Path.StartsWith($rootPath,[StringComparison]::OrdinalIgnoreCase)) {continue}
    $nodes=$w.FindAll([Windows.Automation.TreeScope]::Descendants,$all)
    foreach($b in $nodes){
        if($b.Current.IsOffscreen -or !$b.Current.IsEnabled -or $b.Current.ControlType -ne [Windows.Automation.ControlType]::Button -or $b.Current.Name -notmatch $buttons){continue}
        $scope=$b
        for($i=0;$i -lt 8;$i++){
            $scope=[Windows.Automation.TreeWalker]::ControlViewWalker.GetParent($scope)
            if(!$scope){break}
            if($scope.Current.ProcessId -ne $w.Current.ProcessId){
                $owner=Get-Process -Id $scope.Current.ProcessId -ErrorAction SilentlyContinue
                if(!$owner -or $owner.Name -notin @('steam','steamwebhelper') -or !$owner.Path.StartsWith($rootPath,[StringComparison]::OrdinalIgnoreCase)){break}
            }
            $children=$scope.FindAll([Windows.Automation.TreeScope]::Descendants,$all)
            if($children.Count -gt 400){break}
            $texts=@($scope.Current.Name)+@($children | Where-Object {!$_.Current.IsOffscreen} | ForEach-Object {$_.Current.Name} | Where-Object {$_} | Select-Object -Unique)
            $body=$texts -join "`n"
            if($Action -in @('terms','accept')){
                if($body.IndexOf($Title,[StringComparison]::OrdinalIgnoreCase) -lt 0 -or $body -notmatch '(?i)license agreement|lizenzvereinbarung|nutzungsbedingungen|terms of service|EULA'){continue}
                $agreement=$children | Where-Object {$_.Current.ControlType -in @([Windows.Automation.ControlType]::Document,[Windows.Automation.ControlType]::Edit)} | ForEach-Object {try{$_.GetCurrentPattern([Windows.Automation.TextPattern]::Pattern).DocumentRange.GetText(-1)}catch{}}
                $detail=(($agreement | Sort-Object Length -Descending | Select-Object -First 1) -as [string])
                if($detail.Length -lt 100 -or $detail.Length -gt 150000){continue}
                $hash=[BitConverter]::ToString([Security.Cryptography.SHA256]::Create().ComputeHash([Text.Encoding]::UTF8.GetBytes($Title+$detail)))
                if($Action -eq 'accept'){
                    if($hash -ne $Expected){continue}
                    $b.GetCurrentPattern([Windows.Automation.InvokePattern]::Pattern).Invoke()
                    '{"confirmed":true}';exit 0
                }
                @{text=$detail;hash=$hash}|ConvertTo-Json -Compress;exit 0
            }
            if($Action -eq 'launch'){
                if($body.IndexOf($Title,[StringComparison]::OrdinalIgnoreCase) -lt 0 -or $body -notmatch '(?i)Startoption|launch option|select.{0,25}(mode|version)|Startmodus'){continue}
                $options=@($children | Where-Object {$_.Current.ControlType -eq [Windows.Automation.ControlType]::RadioButton -and $_.Current.IsEnabled -and !$_.Current.IsOffscreen})
                if(!$options.Count){continue}
                $selected=@($options | Where-Object {$_.GetCurrentPattern([Windows.Automation.SelectionItemPattern]::Pattern).Current.IsSelected})
                if($selected.Count -ne 1 -or $selected[0].Current.Name -match '(?i)VR|Oculus'){continue}
                $play=@($children | Where-Object {$_.Current.ControlType -eq [Windows.Automation.ControlType]::Button -and $_.Current.IsEnabled -and !$_.Current.IsOffscreen -and $_.Current.Name -match '^(Play|Spielen|Starten|Launch)$'})
                if($play.Count -ne 1){continue}
                $play[0].GetCurrentPattern([Windows.Automation.InvokePattern]::Pattern).Invoke()
                '{"confirmed":true}';exit 0
            }
            if($body.IndexOf($Title,[StringComparison]::OrdinalIgnoreCase) -lt 0 -or $body -notmatch '(?i)install|speicherplatz|disk space|entfernen'){continue}
            $choices=@($children | Where-Object {$_.Current.ControlType -eq [Windows.Automation.ControlType]::Button -and $_.Current.IsEnabled -and !$_.Current.IsOffscreen -and $_.Current.Name -match $buttons})
            $ok=@($choices | Where-Object {$_.Current.Name -match '^(Installieren|Install|Deinstallieren|Uninstall|Entfernen|Remove|Weiter|Next)$'})
            $cancel=@($choices | Where-Object {$_.Current.Name -match '^(Abbrechen|Cancel)$'})
            if($ok.Count -ne 1 -or $cancel.Count -ne 1){continue}
            $confirmName=$ok[0].Current.Name
            if($Action -ne 'inspect'){
                if($Action -eq 'install' -and ($confirmName -notmatch '^(Installieren|Install)$' -or $body -match '(?i)lizenzvereinbarung|license agreement|kaufen|purchase')){continue}
                if($Action -in @('confirm','install')){$target=$ok[0]}else{$target=$cancel[0]}
                $target.GetCurrentPattern([Windows.Automation.InvokePattern]::Pattern).Invoke()
            }
            [ordered]@{text=$body.Substring(0,[Math]::Min($body.Length,2400));confirm=$confirmName;cancel=$true}|ConvertTo-Json -Compress
            exit 0
        }
    }
 } catch {continue}
}
'{}'
