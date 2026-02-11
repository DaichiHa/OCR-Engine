param(
  [int]$Pr = 20,
  [string]$PageMid = "$HOME\\Downloads\\日本帝國港灣統計_0001\\pages\\page_011_mid.png",
  [string]$PageHi  = "$HOME\\Downloads\\日本帝國港灣統計_0001\\pages\\page_011_hi.png",
  [string]$OutDir  = "$HOME\\Downloads\\PDF_OCR_OUT",
  [int]$N = 6,
  [double]$InkMin = 0.010,
  [int]$Row = 1,
  [double]$TimeoutMid = 0.8,
  [double]$TimeoutHi  = 1.0,
  [switch]$RightToLeft
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

function Get-TessLangs {
  try {
    $x = & tesseract --list-langs 2>$null
    if($LASTEXITCODE -ne 0){ return @() }
    return $x | Select-Object -Skip 1 | ForEach-Object { $_.Trim() } | Where-Object { $_ }
  } catch { return @() }
}

function Pick-Lang([string[]]$want, [string[]]$have){
  $ok = @()
  foreach($w in $want){ if($have -contains $w){ $ok += $w } }
  if($ok.Count -eq 0){ return "jpn+eng" }
  return ($ok -join "+")
}

function Clean-Text([string]$t){
  if($null -eq $t){ $t="" }
  $c = $t -replace "[\r\n\t ]",""
  $c = $c -replace "\|",""
  $c = $c -replace "[—ー_\-\.]",""
  return $c
}

function KPI-FromMd([string]$mdPath){
  if(!(Test-Path $mdPath)){ return @{ok=$false} }
  $t = Get-Content $mdPath -Raw -ErrorAction SilentlyContinue
  $c = Clean-Text $t
  $jp  = ([regex]::Matches($c,"[\u3040-\u30ff\u3400-\u9fff]")).Count
  $dig = ([regex]::Matches($c,"[0-9]")).Count
  $all = ([regex]::Matches($c,".")).Count
  $jp_rate2  = [math]::Round($jp/[math]::Max(1,$all),4)
  $dig_rate2 = [math]::Round($dig/[math]::Max(1,$all),4)
  $noise2 = ([regex]::Matches($c,"[|—ー_\-\.]")).Count
  $noise_rate2 = [math]::Round($noise2/[math]::Max(1,$all),4)
  return @{
    ok=$true; chars2=$all; jp_rate2=$jp_rate2; dig_rate2=$dig_rate2; noise_rate2=$noise_rate2
  }
}

function Crop-Roi([string]$src, [string]$dst, [int]$i, [int]$N){
  python -c "from PIL import Image; p=r'$src'; o=r'$dst'; im=Image.open(p); w,h=im.size; x0=int(w*($i/$N)); x1=int(w*(($i+1)/$N)); im.crop((x0,0,x1,h)).save(o)"
}

function Run-One([string]$img, [string]$lang, [double]$timeout, [string]$tag){
  $env:INK_MIN = ("{0:0.000}" -f $InkMin)
  mkdir $OutDir -Force | Out-Null
  $res = & python .\ops\mini_runner.py --page "$img" --out "$OutDir" --row-min $Row --row-max $Row --timeout $timeout --lang "$lang" 2>&1
  $log = Join-Path $OutDir ("_run_{0}.log" -f $tag)
  $res | Out-File $log -Encoding utf8

  $md = ($res | Where-Object { $_ -match "\.md$" } | Select-Object -First 1)
  if([string]::IsNullOrWhiteSpace($md)){ return @{ok=$false; tag=$tag; log=$log} }

  $k = KPI-FromMd $md
  if(-not $k.ok){ return @{ok=$false; tag=$tag; md=$md; log=$log} }
  return @{
    ok=$true; tag=$tag; md=$md; log=$log;
    chars2=$k.chars2; jp_rate2=$k.jp_rate2; dig_rate2=$k.dig_rate2; noise_rate2=$k.noise_rate2
  }
}

# ---- main ----
$have = Get-TessLangs
$langMid = "jpn+eng"
$langHi  = Pick-Lang @("jpn","chi_tra","chi_sim","eng") $have

mkdir $OutDir -Force | Out-Null

# ROI sweep (mid)
$best = @{i=-1; noise=9.0; jp=0.0; chars=0; md=""; tag=""}
$idx = 0..($N-1)
if($RightToLeft){ $idx = $idx | Sort-Object -Descending }

foreach($i in $idx){
  $roi = Join-Path $OutDir ("roi_x{0:00}.png" -f $i)
  Crop-Roi $PageMid $roi $i $N
  $r = Run-One $roi $langMid $TimeoutMid ("mid_x{0:00}" -f $i)
  if(-not $r.ok){ continue }
  "{0} i={1} chars2={2} jp2={3} dig2={4} noise2={5}" -f $r.tag,$i,$r.chars2,$r.jp_rate2,$r.dig_rate2,$r.noise_rate2

  if($r.chars2 -ge 50){
    if( ($r.noise_rate2 -lt $best.noise) -or (($r.noise_rate2 -eq $best.noise) -and ($r.jp_rate2 -gt $best.jp)) ){
      $best = @{i=$i; noise=$r.noise_rate2; jp=$r.jp_rate2; chars=$r.chars2; md=$r.md; tag=$r.tag}
    }
  }
}

if($best.i -lt 0){ $best.i = 0 }

"BEST i=$($best.i) chars2=$($best.chars) jp2=$($best.jp) noise2=$($best.noise) langHi=$langHi"

# best ROI (hi)
$roi_hi = Join-Path $OutDir ("roi_x{0:00}_hi.png" -f $best.i)
Crop-Roi $PageHi $roi_hi $best.i $N

$r1 = Run-One $roi_hi "jpn+eng" $TimeoutHi ("hi_x{0:00}_jpn_eng" -f $best.i)
if($r1.ok){ Copy-Item $r1.md (Join-Path $OutDir "cmp_hi_jpn_eng.md") -Force }

$r2 = Run-One $roi_hi $langHi $TimeoutHi ("hi_x{0:00}_multi" -f $best.i)
if($r2.ok){ Copy-Item $r2.md (Join-Path $OutDir "cmp_hi_multi.md") -Force }

# PR comment
$ts = (Get-Date -Format o)
$body = @()
$body += "KPI_ROI ts=$ts best_i=$($best.i) N=$N ink=$InkMin row=$Row rtl=$RightToLeft"
if($r1.ok){ $body += "HI_jpn_eng chars2=$($r1.chars2) jp2=$($r1.jp_rate2) dig2=$($r1.dig_rate2) noise2=$($r1.noise_rate2) md=$([IO.Path]::GetFileName($r1.md))" }
if($r2.ok){ $body += "HI_multi  lang=$langHi chars2=$($r2.chars2) jp2=$($r2.jp_rate2) dig2=$($r2.dig_rate2) noise2=$($r2.noise_rate2) md=$([IO.Path]::GetFileName($r2.md))" }
$bodyTxt = ($body -join "`n")

& gh pr comment $Pr --body $bodyTxt
$bodyTxt
