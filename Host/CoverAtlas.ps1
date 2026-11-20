param([string]$Manifest,[string]$Destination)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Drawing
$images=ConvertFrom-Json -InputObject (Get-Content -Raw -Encoding UTF8 -LiteralPath $Manifest)
for($first=0;$first -lt $images.Count;$first+=64){
 $bitmap=New-Object Drawing.Bitmap 1152,1728
 $graphics=[Drawing.Graphics]::FromImage($bitmap)
 try{
  $graphics.Clear([Drawing.Color]::FromArgb(23,32,46))
  $graphics.InterpolationMode=[Drawing.Drawing2D.InterpolationMode]::HighQualityBilinear
  for($n=0;$n -lt 64 -and ($first+$n) -lt $images.Count;$n++){
   $im=[Drawing.Image]::FromFile($images[$first+$n])
   try{$graphics.DrawImage($im,[Drawing.Rectangle]::new(($n%8)*144,[int][Math]::Floor($n/8)*216,144,216))}finally{$im.Dispose()}
  }
  $bitmap.Save((Join-Path $Destination ("{0}.jpg" -f [int]($first/64))),[Drawing.Imaging.ImageFormat]::Jpeg)
 }finally{$graphics.Dispose();$bitmap.Dispose()}
}

