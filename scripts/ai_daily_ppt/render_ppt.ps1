param(
  [Parameter(Mandatory = $true)][string]$Pptx,
  [Parameter(Mandatory = $true)][string]$OutDir
)

$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $Pptx)) { throw "PPT not found: $Pptx" }
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$ppt = $null
$pres = $null
try {
  $ppt = New-Object -ComObject PowerPoint.Application
  $pres = $ppt.Presentations.Open($Pptx, $true, $false, $false)
  Get-ChildItem -LiteralPath $OutDir -Filter *.PNG | Remove-Item -Force
  $pres.Export($OutDir, 'PNG', 1280, 720)
  $n = 0
  Get-ChildItem -LiteralPath $OutDir -Filter *.PNG |
    Sort-Object { [int]([regex]::Match($_.BaseName, '\d+').Value) } |
    ForEach-Object {
      $n++
      $target = Join-Path $OutDir ("Slide{0}.PNG" -f $n)
      if ($_.FullName -ne $target) {
        Move-Item -LiteralPath $_.FullName -Destination $target -Force
      }
    }
  Write-Output "Exported slides to $OutDir"
} finally {
  if ($pres -ne $null) { $pres.Close() }
  if ($ppt -ne $null) { $ppt.Quit() }
  if ($pres -ne $null) { [void][Runtime.InteropServices.Marshal]::ReleaseComObject($pres) }
  if ($ppt -ne $null) { [void][Runtime.InteropServices.Marshal]::ReleaseComObject($ppt) }
}
