
# Valid for Windows 10/11
# Loads WinRT classes to perform OCR

$imagePath = "c:\Users\User\Downloads\日本帝國港灣統計_0001\pages\page_003.png"

# Helper to load WinRT types
Function Load-WinRT {
    Param([string]$TypeName)
    $null = [Windows.System.Launcher] # Force load of some base types
}

# WinRT Types are available in PS 5.1 on Win10+ automatically in many cases, 
# but sometimes need explicit loading.
# Trying simple approach first.

try {
    # Check if we can create the engine
    $lang = [Windows.Globalization.Language]::new("ja-JP")
    $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage($lang)
    
    if ($null -eq $engine) {
        Write-Output "Error: Japanese OCR engine not available."
        exit 1
    }

    # Load file
    # WinRT file access
    $fileTask = [Windows.Storage.StorageFile]::GetFileFromPathAsync($imagePath)
    # Synchronous wait
    while (-not $fileTask.IAsyncOperation.Status -eq 'Completed') { Start-Sleep -Milliseconds 10 }
    $file = $fileTask.GetResults()

    # Open stream
    $streamTask = $file.OpenAsync([Windows.Storage.FileAccessMode]::Read)
    while (-not $streamTask.IAsyncOperation.Status -eq 'Completed') { Start-Sleep -Milliseconds 10 }
    $stream = $streamTask.GetResults()

    # Decode image
    $decoderTask = [Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)
    while (-not $decoderTask.IAsyncOperation.Status -eq 'Completed') { Start-Sleep -Milliseconds 10 }
    $decoder = $decoderTask.GetResults()

    # Get software bitmap
    $bitmapTask = $decoder.GetSoftwareBitmapAsync()
    while (-not $bitmapTask.IAsyncOperation.Status -eq 'Completed') { Start-Sleep -Milliseconds 10 }
    $bitmap = $bitmapTask.GetResults()

    # Recognize
    $ocrTask = $engine.RecognizeAsync($bitmap)
    while (-not $ocrTask.IAsyncOperation.Status -eq 'Completed') { Start-Sleep -Milliseconds 10 }
    $result = $ocrTask.GetResults()

    # Output lines
    $result.Lines | ForEach-Object {
        Write-Output $_.Text
    }

}
catch {
    Write-Output "Exception: $_"
    # Print more details about the exception
    Write-Output $_.Exception.Message
    Write-Output "Stack Trace: "
    Write-Output $_.ScriptStackTrace
}
