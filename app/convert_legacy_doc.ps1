param(
    [Parameter(Mandatory = $true)][string]$InputFile,
    [Parameter(Mandatory = $true)][string]$OutputFile
)

$ErrorActionPreference = 'Stop'
Unblock-File -LiteralPath $InputFile -ErrorAction SilentlyContinue

$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
$word.AutomationSecurity = 3
$word.Options.ConfirmConversions = $false
$word.Options.SaveNormalPrompt = $false
$word.Options.UpdateLinksAtOpen = $false

try {
    $document = $word.Documents.Open($InputFile, $false, $true, $false)
    try {
        $document.SaveAs2($OutputFile, 16)
    }
    finally {
        $document.Close($false)
    }
}
finally {
    $word.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null
}

