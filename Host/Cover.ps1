param([Parameter(Mandatory)][string]$Manifest)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Drawing
foreach ($item in (Get-Content -Raw -Encoding UTF8 -LiteralPath $Manifest | ConvertFrom-Json)) {
    if ((Test-Path -LiteralPath $item.target) -and (!$item.source -or (Get-Item -LiteralPath $item.target).LastWriteTimeUtc -ge (Get-Item -LiteralPath $item.source).LastWriteTimeUtc)) {
        $saved=[Drawing.Image]::FromFile($item.target)
        try {$current=$saved.Width -ge 600} finally {$saved.Dispose()}
        if ($current) {continue}
    }
    $bitmap=[Drawing.Bitmap]::new(600,900)
    $graphics=[Drawing.Graphics]::FromImage($bitmap)
    try {
        $graphics.SmoothingMode='AntiAlias'
        $graphics.InterpolationMode='HighQualityBicubic'
        $graphics.TextRenderingHint='AntiAliasGridFit'
        $rect=[Drawing.Rectangle]::new(0,0,600,900)
        if ($item.source) {
            $art=[Drawing.Image]::FromFile($item.source)
            try {
                $scale=[Math]::Max(600.0/$art.Width,900.0/$art.Height)
                $w=[float]($art.Width*$scale)
                $h=[float]($art.Height*$scale)
                $graphics.DrawImage($art,[Drawing.RectangleF]::new((600-$w)/2,(900-$h)/2,$w,$h))
            } finally {$art.Dispose()}
        } else {
            $graphics.ScaleTransform([float](600/420),[float](900/560))
            $hash=[uint64]$item.id % 131
            $shade=[Drawing.Color]::FromArgb(36+($hash % 46),48,87+($hash % 75))
            $brush=[Drawing.Drawing2D.LinearGradientBrush]::new([Drawing.Rectangle]::new(0,0,420,560),$shade,[Drawing.Color]::FromArgb(9,16,32),58)
            $graphics.FillRectangle($brush,0,0,420,560)
            $brush.Dispose()
            $pen=[Drawing.Pen]::new([Drawing.Color]::FromArgb(55,182,220,251),1.3)
            for($n=0;$n -lt 25;$n++) {$graphics.DrawBezier($pen,-30,195+$n,135,65-$n,330,460+$n,448,150+$n*3)}
            $pen.Dispose()
            $font=[Drawing.Font]::new('Segoe UI Light',26)
            $graphics.DrawString($item.name,$font,[Drawing.Brushes]::White,[Drawing.RectangleF]::new(26,275,368,250))
            $font.Dispose()
        }
        $bitmap.Save($item.target,[Drawing.Imaging.ImageFormat]::Png)
    } finally {$graphics.Dispose(); $bitmap.Dispose()}
}
