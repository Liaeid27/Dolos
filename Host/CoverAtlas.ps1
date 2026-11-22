param([string]$Manifest,[string]$Destination)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Drawing
$files=ConvertFrom-Json -InputObject (Get-Content -Raw -Encoding UTF8 -LiteralPath $Manifest)
$images=@($files)
$valid=[Collections.Generic.List[int]]::new()
$wrap=[Drawing.Imaging.ImageAttributes]::new()
$wrap.SetWrapMode([Drawing.Drawing2D.WrapMode]::TileFlipXY)
$jpeg=[Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() | Where-Object { $_.MimeType -eq 'image/jpeg' } | Select-Object -First 1
$encoding=[Drawing.Imaging.EncoderParameters]::new(1)
$encoding.Param[0]=[Drawing.Imaging.EncoderParameter]::new([Drawing.Imaging.Encoder]::Quality,[long]68)
$cellWidth=144
$cellHeight=216
$index=0
$page=0
try {
    while ($index -lt $images.Count) {
        $bitmap=[Drawing.Bitmap]::new(8*$cellWidth,8*$cellHeight)
        $graphics=[Drawing.Graphics]::FromImage($bitmap)
        try {
            $graphics.Clear([Drawing.Color]::FromArgb(23,32,46))
            $graphics.InterpolationMode=[Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
            $graphics.PixelOffsetMode=[Drawing.Drawing2D.PixelOffsetMode]::Half
            $cell=0
            while ($cell -lt 64 -and $index -lt $images.Count) {
                $sourceIndex=$index
                $index++
                $image=$null
                try {
                    $image=[Drawing.Image]::FromFile($images[$sourceIndex])
                    $x=($cell%8)*$cellWidth
                    $y=[Math]::Floor($cell/8)*$cellHeight
                    $sw=$image.Width
                    $sh=$image.Height
                    if ($sw -ge $sh) {
                        # Preserve the complete title on horizontal Steam headers.
                        $h=[Math]::Max(1,[Math]::Round($cellWidth*$sh/$sw))
                        $dst=[Drawing.Rectangle]::new($x,$y+[Math]::Floor(($cellHeight-$h)/2),$cellWidth,$h)
                        $srcX=$srcY=0
                    } else {
                        $scale=[Math]::Max($cellWidth/$sw,$cellHeight/$sh)
                        $srcX=($sw-$cellWidth/$scale)/2
                        $srcY=($sh-$cellHeight/$scale)/2
                        $sw=$cellWidth/$scale
                        $sh=$cellHeight/$scale
                        $dst=[Drawing.Rectangle]::new($x,$y,$cellWidth,$cellHeight)
                    }
                    $graphics.DrawImage($image,$dst,[float]$srcX,[float]$srcY,[float]$sw,[float]$sh,[Drawing.GraphicsUnit]::Pixel,$wrap)
                } catch [System.OutOfMemoryException],[System.ArgumentException],[System.IO.IOException] {
                    # GDI+ uses OutOfMemoryException for malformed image files.
                    continue
                } finally {
                    if ($image) {$image.Dispose()}
                }
                $valid.Add($sourceIndex)
                $cell++
            }
            if ($cell) {
                $bitmap.Save((Join-Path $Destination "$page.jpg"),$jpeg,$encoding)
                $page++
            }
        } finally {
            $graphics.Dispose()
            $bitmap.Dispose()
        }
    }
} finally {
    $encoding.Dispose()
    $wrap.Dispose()
}
[IO.File]::WriteAllLines((Join-Path $Destination 'indices.txt'),[string[]]$valid)
