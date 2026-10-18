$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$installer = Join-Path $root 'installer\python-3.12.10-amd64.exe'
$expectedMd5 = '5EDDB0B6F12C852725DE071AE681DDE4'

if (-not (Test-Path -LiteralPath $installer)) {
    throw 'Khong tim thay file cai Python trong goi.'
}

$actualMd5 = (Get-FileHash -LiteralPath $installer -Algorithm MD5).Hash
if ($actualMd5 -ne $expectedMd5) {
    throw "File cai Python khong khop ma kiem tra. Nhan duoc: $actualMd5"
}

$signature = Get-AuthenticodeSignature -LiteralPath $installer
if ($signature.Status -ne 'Valid') {
    throw "Chu ky so cua file cai Python khong hop le: $($signature.Status)"
}

Write-Host 'File cai Python hop le: ma kiem tra va chu ky so deu dat.' -ForegroundColor Green
