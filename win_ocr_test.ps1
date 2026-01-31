
# PowerShell script to use Windows.Media.Ocr
# Requires Windows 10/11

$imagePath = "c:\Users\User\Downloads\日本帝國港灣統計_0001\pages\page_003.png"

# Load assemblies
[void][Windows.Globalization.Language, Windows.Foundation, ContentType = WindowsRuntime]
[void][Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics, ContentType = WindowsRuntime]
[void][Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime]
[void][Windows.Storage.StorageFile, ContentType = WindowsRuntime]

async function Get-OcrResult($Path) {
    try {
        $file = await [Windows.Storage.StorageFile]::GetFileFromPathAsync($Path)
        $stream = await $file.OpenAsync([Windows.Storage.FileAccessMode]::Read)
        $decoder = await [Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)
        $bitmap = await $decoder.GetSoftwareBitmapAsync()

        # Create OCR Engine for Japanese
        $lang = [Windows.Globalization.Language]::new("ja-JP")
        $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage($lang)

        if ($null -eq $engine) {
            Write-Output "Error: Japanese OCR engine not found. Please install Japanese Language Pack."
            return
        }

        # Recognize
        $result = await $engine.RecognizeAsync($bitmap)
        
        # Output Text
        $result.Lines | ForEach-Object {
            $_.Text
        }
    }
    catch {
        Write-Output "Error: $_"
    }
}

# Run the async function
$task = Get-OcrResult $imagePath
$task.Wait()
