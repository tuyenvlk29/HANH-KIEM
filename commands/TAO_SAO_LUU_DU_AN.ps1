$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$backupFolder = Join-Path $projectRoot 'backups'
New-Item -ItemType Directory -Force -Path $backupFolder | Out-Null

$stamp = Get-Date -Format 'yyyy-MM-dd_HHmmss'
$archive = Join-Path $backupFolder "DU_AN_HE_THONG_HANH_KIEM_TUYEN_BUI_$stamp.zip"

Push-Location $projectRoot
try {
    & tar.exe -a -c -f $archive --exclude=node_modules --exclude=backups .
    if ($LASTEXITCODE -ne 0) {
        throw "Không thể tạo bản sao lưu (mã lỗi $LASTEXITCODE)."
    }
}
finally {
    Pop-Location
}

$sizeMb = [math]::Round((Get-Item -LiteralPath $archive).Length / 1MB, 2)
Write-Host "Đã lưu bản sao: $archive ($sizeMb MB)" -ForegroundColor Green
