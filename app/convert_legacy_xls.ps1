param(
    [Parameter(Mandatory=$true)][string]$InputFile,
    [Parameter(Mandatory=$true)][string]$OutputFile
)

$ErrorActionPreference = 'Stop'
$excel = $null
$book = $null
try {
    $excel = New-Object -ComObject Excel.Application
    $excel.Visible = $false
    $excel.DisplayAlerts = $false
    $book = $excel.Workbooks.Open($InputFile, 0, $true)
    # 51 = .xlsx (Excel Open XML Workbook), deliberately written to a temporary path.
    $book.SaveAs($OutputFile, 51)
}
finally {
    if ($book) { $book.Close($false) }
    if ($excel) { $excel.Quit() }
}
