$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$sourceDir = Join-Path $projectRoot 'sources_original'

$expectedHashes = @(
    'D238778B61E2941FEA4D6ECE1F09884E677888CCE905A64BA3C415478910D8CF',
    '8C96742112FA7DF521DA74C86D932566CC23C52719810BFC67390981A2228CA2',
    'E20B121789231FA630FD375E1E80CC73E8A6BE514A74CF347A00C6A17F588B3B',
    '2F41048EBD37F94944F36F5405BCB063CFC2C0A4502457F35113DF724DF0B020',
    'ED066CB46B5DD294AC8A261AA60F2C2E88E01C89DEFF00FAA8692C0D9B15049C',
    'D14F514A8FCC3F4A1B7B3B7A0AAF96194522EA1B492C2E9257D2855D100DE77F',
    '069592C11C50020ACDDAE6FFABBF7A2D2052270187EB9CDB65E2201D5883D313',
    '300C9D2BA0656754D7D0D06519410FAC1C8210E50E3AD439018D1243483C3906',
    '9B35B20749C91F5139582EF01A26547A569AD14D3BBBEA6DA6CA1CBCD5C9853D'
)

$files = @(Get-ChildItem -LiteralPath $sourceDir -File)
if ($files.Count -ne 9) {
    Write-Host "FAILED: expected 9 files, found $($files.Count)." -ForegroundColor Red
    exit 1
}

$actualHashes = @($files | Get-FileHash -Algorithm SHA256 | ForEach-Object { $_.Hash })
$missing = @($expectedHashes | Where-Object { $_ -notin $actualHashes })
$unexpected = @($actualHashes | Where-Object { $_ -notin $expectedHashes })

if ($missing.Count -gt 0 -or $unexpected.Count -gt 0) {
    Write-Host 'FAILED: one or more source files changed.' -ForegroundColor Red
    exit 1
}

Write-Host 'OK: all 9 source files match their original SHA-256 hashes.' -ForegroundColor Green

