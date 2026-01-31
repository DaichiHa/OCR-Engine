# OCR-Engine

OCR CLI for extracting text from PDFs with an option to fall back to OCR when a text layer is missing.

## Setup

### Create and activate a virtual environment (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Install Python dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install pymupdf pytesseract opencv-python numpy pillow rich pydantic
```

### Verify Tesseract installation

Make sure Tesseract is installed and available on your PATH. Verify with:

```powershell
tesseract --version
```

## Usage

Example CLI invocation:

```bash
pdf2txt in.pdf -o out --lang eng --jobs 8
```

## Output

Expected output folder structure:

```
out/
  pages/
    page-0001.txt
    page-0002.txt
  metadata.json
```

## Extraction behavior

The tool attempts text-layer-first extraction. If a PDF page contains an embedded text layer, it will extract that text directly. If no text layer is present (or extraction yields empty output), the tool falls back to OCR for that page.

## Guides

- [OSSでPDF-OCRを安定運用するための上限と実戦ガイド](docs/oss_pdf_ocr_guidance.md)
