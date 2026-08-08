param(
  [Parameter(Mandatory = $true)][string]$Dir,
  [Parameter(Mandatory = $true)][string]$Out
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime

$null = [Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics.Imaging, ContentType = WindowsRuntime]
$null = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime]
$null = [Windows.Globalization.Language, Windows.Globalization, ContentType = WindowsRuntime]

$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() |
    Where-Object {
      $_.Name -eq 'AsTask' -and
      $_.GetParameters().Count -eq 1 -and
      $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
    })[0]

function Await($WinRtTask, $ResultType) {
  $asTask = $asTaskGeneric.MakeGenericMethod($ResultType)
  $netTask = $asTask.Invoke($null, @($WinRtTask))
  $netTask.Wait(-1) | Out-Null
  return $netTask.Result
}

$engine = $null
try {
  $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
} catch {
  $engine = $null
}
if ($null -eq $engine) {
  $lang = [Windows.Globalization.Language]::new('zh-Hans-CN')
  $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage($lang)
}
if ($null -eq $engine) {
  throw 'No OCR engine available for this user profile.'
}

$files = Get-ChildItem -LiteralPath $Dir -Filter *.PNG |
  Sort-Object { [int]([regex]::Match($_.BaseName, '\d+').Value) }
$result = @()

foreach ($file in $files) {
  $storageFile = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync($file.FullName)) ([Windows.Storage.StorageFile])
  $stream = Await ($storageFile.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
  try {
    $decoder = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
    $bitmap = Await ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
    $ocr = Await ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
    $lines = @()
    foreach ($line in $ocr.Lines) {
      $words = @()
      foreach ($word in $line.Words) {
        $words += [ordered]@{
          text = $word.Text
          x = [math]::Round($word.BoundingRect.X)
          y = [math]::Round($word.BoundingRect.Y)
          w = [math]::Round($word.BoundingRect.Width)
          h = [math]::Round($word.BoundingRect.Height)
        }
      }
      $lines += [ordered]@{
        text = $line.Text
        words = $words
      }
    }
    $result += [ordered]@{
      slide = [int]([regex]::Match($file.BaseName, '\d+').Value)
      width = $decoder.PixelWidth
      height = $decoder.PixelHeight
      lines = $lines
    }
  } finally {
    $stream.Dispose()
  }
}

$json = $result | ConvertTo-Json -Depth 8
[System.IO.File]::WriteAllText($Out, $json, [System.Text.UTF8Encoding]::new($false))
Write-Output ("OCR done: {0} slides -> {1}" -f $result.Count, $Out)
