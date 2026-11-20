param([Parameter(Mandatory)][string]$SteamRoot,[Parameter(Mandatory)][string]$Title,[ValidateSet('inspect','confirm','cancel','install')][string]$Action='inspect')
$ErrorActionPreference='Stop'
[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false)
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$tree=[Windows.Automation.AutomationElement]::RootElement
$all=[Windows.Automation.Condition]::TrueCondition
$rootPath=[IO.Path]::GetFullPath($SteamRoot).TrimEnd('\')+'\'
$buttons='^(Installieren|Install|Deinstallieren|Uninstall|Entfernen|Remove|Weiter|Next|Abbrechen|Cancel)$'
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
