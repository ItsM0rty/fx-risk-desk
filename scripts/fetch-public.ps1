param([string]$EcbArchive)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$raw = Join-Path $root 'data/raw'
New-Item -ItemType Directory -Path $raw -Force | Out-Null

$ecbPath = Join-Path $raw 'ecb-eurofxref-hist.zip'
if ($EcbArchive) {
    Copy-Item -LiteralPath $EcbArchive -Destination $ecbPath
} elseif (-not (Test-Path -LiteralPath $ecbPath)) {
    Invoke-WebRequest -Uri 'https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist.zip' -OutFile $ecbPath -TimeoutSec 40
}

$start = '2022-01-01'
$end = '2025-12-31'
$perPage = 100
$endpoint = 'https://www.nrb.org.np/api/forex/v1/rates'
$nrbPath = Join-Path $raw 'nrb-usd-npr.json'
if (Test-Path -LiteralPath $nrbPath) {
    Write-Output "Using cached NRB rates at $nrbPath."
    return
}
$records = [System.Collections.Generic.List[object]]::new()
$page = 1
do {
    $uri = "${endpoint}?page=$page&per_page=$perPage&from=$start&to=$end"
    $response = Invoke-RestMethod -Uri $uri -TimeoutSec 25 -MaximumRetryCount 2 -RetryIntervalSec 2
    if ($response.status.code -ne 200 -or $response.pagination.page -ne $page) {
        throw "NRB returned an unexpected response for page $page."
    }
    if ($page -eq 1) {
        $total = [int]$response.pagination.total
        $pages = [int]$response.pagination.pages
        if ($total -le 0 -or $pages -lt 1 -or $pages -gt 25) { throw 'NRB returned an invalid range size.' }
    }
    if ($response.pagination.total -ne $total -or $response.pagination.pages -ne $pages) {
        throw 'NRB pagination changed during the snapshot.'
    }
    foreach ($entry in $response.data.payload) {
        $usd = @($entry.rates | Where-Object { $_.currency.iso3 -ceq 'USD' })
        if ($usd.Count -ne 1) { throw "Expected one USD quote on $($entry.date)." }
        $records.Add([ordered]@{ date = $entry.date; buy = $usd[0].buy; sell = $usd[0].sell; unit = $usd[0].currency.unit })
    }
    $page++
} while ($page -le $pages)
if ($records.Count -ne $total) { throw "NRB returned $($records.Count) records, expected $total." }
$snapshot = [ordered]@{ source = $endpoint; from = $start; to = $end; retrieved_at_utc = [DateTimeOffset]::UtcNow.ToString('o'); records = @($records | Sort-Object date) }
$json = ConvertTo-Json -InputObject $snapshot -Depth 6
[IO.File]::WriteAllText($nrbPath, $json, [Text.UTF8Encoding]::new($false))
Write-Output "Saved $total public NRB USD quotes from $pages pages."
