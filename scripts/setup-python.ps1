param([string]$QuantSource = 'https://github.com/AshJha0/quant-portfolio.git')

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
Set-Location -LiteralPath $root

function Invoke-Checked([string]$Executable, [string[]]$Arguments) {
    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Executable failed with exit code $LASTEXITCODE." }
}

$sha = 'bd71bc3b679758e886550939eaa90f13a8e7f7ac'
$cache = Join-Path $root '.cache'
$env:TEMP = $cache
$env:TMP = $cache
$env:PIP_CACHE_DIR = Join-Path $cache 'pip'
$env:PIP_DISABLE_PIP_VERSION_CHECK = '1'
$env:GIT_TERMINAL_PROMPT = '0'
New-Item -ItemType Directory -Path $cache,'.upstream' -Force | Out-Null
$quant = Join-Path $root '.upstream/quant-portfolio'
if (-not (Test-Path -LiteralPath $quant)) {
    Invoke-Checked 'git' @('init', $quant)
}
$current = git -C $quant rev-parse --verify HEAD 2>$null
if ($current -ne $sha) {
    Invoke-Checked 'git' @('-C', $quant, 'fetch', '--depth', '1', $QuantSource, $sha)
    Invoke-Checked 'git' @('-C', $quant, 'switch', '--detach', $sha)
}
$python = Join-Path $root '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    Invoke-Checked 'python' @('-m', 'venv', '.venv')
}
Invoke-Checked $python @(
    '-m', 'pip', 'install', '-r', 'requirements.txt',
    (Join-Path $quant 'python/core'),
    (Join-Path $quant 'python/fx/01-options-pricing'),
    (Join-Path $quant 'python/fx/03-var-es-engine')
)
