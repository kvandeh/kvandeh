# Exports the resume straight from Word: real text layer, embedded fonts,
# tagged for reading order, no header/footer. Run after every edit to the .docx.
#
#   powershell -File .\export-resume-pdf.ps1
#
$docx = "$PSScriptRoot\Kieran-van-der-Heijde-Resume.docx"
$pdf  = "$PSScriptRoot\resume.pdf"

$word = New-Object -ComObject Word.Application
$word.Visible = $false
$doc = $word.Documents.Open($docx, $false, $true)
# wdExportFormatPDF=17, wdExportOptimizeForPrint=0, wdExportDocumentContent=0,
# CreateBookmarks=1 (headings), DocStructureTags=$true, BitmapMissingFonts=$false.
$doc.ExportAsFixedFormat($pdf, 17, $false, 0, 0, 0, 0, 0, $true, $true, 1, $true, $false, $false)
$doc.Close(0)
$word.Quit()
[Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null

Write-Output "Exported $pdf"
