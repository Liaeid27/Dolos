param([Parameter(Mandatory)][string]$Title,[Parameter(Mandatory)][string]$SteamRoot,[string]$Drive,[switch]$Install)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Drawing,System.Runtime.WindowsRuntime
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public class SteamWindow {
[DllImport("user32.dll")] static extern IntPtr ChildWindowFromPointEx(IntPtr h,System.Drawing.Point pt,uint flags);
[DllImport("user32.dll")] static extern int MapWindowPoints(IntPtr a,IntPtr b,ref System.Drawing.Point pt,uint count);
public static bool Click(IntPtr h,int x,int y){
 var p=new System.Drawing.Point(x,y);System.Drawing.Point old;
 if(GetForegroundWindow()!=h || !ClientToScreen(h,ref p) || GetAncestor(WindowFromPoint(p),2)!=h || !GetCursorPos(out old))return false;
 if(!SetCursorPos(p.X,p.Y))return false;
 try {mouse_event(2,0,0,0,UIntPtr.Zero);mouse_event(4,0,0,0,UIntPtr.Zero);System.Threading.Thread.Sleep(75);}
 finally {SetCursorPos(old.X,old.Y);}return true;
}
[DllImport("user32.dll")] static extern bool ClientToScreen(IntPtr h,ref System.Drawing.Point p);
[DllImport("user32.dll")] static extern bool GetCursorPos(out System.Drawing.Point p);
[DllImport("user32.dll")] static extern bool SetCursorPos(int x,int y);
[DllImport("user32.dll")] static extern IntPtr GetAncestor(IntPtr h,uint flags);
[DllImport("user32.dll")] static extern IntPtr WindowFromPoint(System.Drawing.Point p);
[DllImport("user32.dll")] static extern IntPtr GetForegroundWindow();
[DllImport("user32.dll")] static extern void mouse_event(uint flags,int x,int y,uint data,UIntPtr extra);
[DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr w,IntPtr dc,uint flags);
[DllImport("user32.dll")] public static extern bool GetClientRect(IntPtr w,out System.Drawing.Rectangle r);
[DllImport("user32.dll")] public static extern IntPtr SetThreadDpiAwarenessContext(IntPtr context);
[DllImport("user32.dll")] public static extern bool PostMessage(IntPtr w,int msg,IntPtr wp,IntPtr lp);
[DllImport("user32.dll")] public static extern IntPtr GetWindow(IntPtr w,uint cmd);
}
"@ -ReferencedAssemblies System.Drawing
$null=[SteamWindow]::SetThreadDpiAwarenessContext([IntPtr](-4))
$engine=[Windows.Media.Ocr.OcrEngine,Windows.Foundation,ContentType=WindowsRuntime]::TryCreateFromUserProfileLanguages()
$await=[System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {$_.Name -eq 'AsTask' -and $_.IsGenericMethod -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'} | Select-Object -First 1
function Wait-Result($op,$type){$task=$await.MakeGenericMethod($type).Invoke($null,@($op));$task.Wait();$task.Result}
$windows=@(Get-Process steamwebhelper | Where-Object { $_.MainWindowTitle -match '^(Installieren|Install)$' -and $_.Path.StartsWith(([IO.Path]::GetFullPath($SteamRoot).TrimEnd('\')+'\'),[StringComparison]::OrdinalIgnoreCase)})
if($windows.Count -ne 1){return}
$h=$windows[0].MainWindowHandle
function Read-Dialog{
 $rect=New-Object Drawing.Rectangle
 if(![SteamWindow]::GetClientRect($h,[ref]$rect) -or $rect.Width -lt 200){return}
 $bmp=New-Object Drawing.Bitmap $rect.Width,$rect.Height
 $g=[Drawing.Graphics]::FromImage($bmp);$dc=$g.GetHdc()
 try{$ok=[SteamWindow]::PrintWindow($h,$dc,3)}finally{$g.ReleaseHdc($dc);$g.Dispose()}
 $stream=New-Object IO.MemoryStream
 try{
 $script:sample=$bmp.Clone();$bmp.Save($stream,[Drawing.Imaging.ImageFormat]::Png);$stream.Position=0
 $ras=[System.IO.WindowsRuntimeStreamExtensions]::AsRandomAccessStream($stream)
 $dec=Wait-Result ([Windows.Graphics.Imaging.BitmapDecoder,Windows.Foundation,ContentType=WindowsRuntime]::CreateAsync($ras)) ([Windows.Graphics.Imaging.BitmapDecoder])
 $image=Wait-Result ($dec.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap,Windows.Foundation,ContentType=WindowsRuntime])
 try{$result=Wait-Result ($engine.RecognizeAsync($image)) ([Windows.Media.Ocr.OcrResult,Windows.Foundation,ContentType=WindowsRuntime]);$result.Lines}finally{$image.Dispose()}
 }finally{$bmp.Dispose();$stream.Dispose()}
}
function Find-Controls($lines){
 $text=$lines.Text -join ' '
 if (!$Title -or $text.IndexOf($Title,[StringComparison]::OrdinalIgnoreCase) -lt 0 -or $text -notmatch 'INSTALLIEREN IN|INSTALL (TO|LOCATION)' -or $text -match 'Lizenzvereinbarung|license agreement'){return}
 $cancel=@($lines | Where-Object {$_.Text -match '^(Abbrechen|Cancel)$'})
 if($cancel.Count -ne 1){return}
 $limit=@($cancel[0].Words)[0].BoundingRect.Y
 $confirm=@($lines | Where-Object {$_.Text -match '^(Installieren|stallieren|Install)$' -and [Math]::Abs(@($_.Words)[0].BoundingRect.Y-$limit) -lt 8})
 if($confirm.Count -ne 1){return}
 $row=@($lines | Where-Object {$Drive -and $_.Text -match ('(?i)\('+[regex]::Escape($Drive)+'(?:\)|\s|$)')})
 if($row.Count -ne 1){return}
 @{row=@($row[0].Words)[0].BoundingRect;ok=@($confirm[0].Words)[0].BoundingRect}
}
if($Drive -notmatch '^[A-Za-z]:$'){return}
$ctl=Find-Controls @(Read-Dialog)
if(!$ctl){return}
if($Install){$shell=New-Object -ComObject WScript.Shell; $null=$shell.AppActivate($windows[0].Id);Start-Sleep -Milliseconds 180
 $r=$ctl.row
 if(![SteamWindow]::Click($h,[int]($r.X+4),[int]($r.Y+$r.Height/2))){return}
 Start-Sleep -Milliseconds 350
 $script:sample.Dispose()
 $ctl=Find-Controls @(Read-Dialog)
 if(!$ctl){return}
 $r=$ctl.row
 $color=$script:sample.GetPixel([Math]::Max(1,[int]$r.X-9),[int]($r.Y+$r.Height/2))
 if($color.B-$color.R -lt 70 -or $color.G-$color.R -lt 45){return}
 $b=$ctl.ok
 if(![SteamWindow]::Click($h,[int]($b.X+4),[int]($b.Y+$b.Height/2))){return}
}
@{text=($Title+' · '+$Drive);confirm='Installieren';cancel=$false}|ConvertTo-Json -Compress


