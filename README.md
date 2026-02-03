# OCR-Engine - High Precision Document Processing System

> **New in v2.0**: Qwen-2.5-32B Integration with Local-First Architecture

## 🚀 Overview

OCR-Engine is a comprehensive document processing system specialized for Japanese historical documents. Originally featuring multiple OCR engines, it now incorporates **Qwen-2.5-32B as the primary engine** with local-first processing capabilities.

### 🎯 Engine Architecture

**Primary Engine (Unlimited)**
- 🥇 **Qwen-2.5-32B**: State-of-the-art vision-language model for structured document analysis

**Supporting Engines**
- 🥈 **Tesseract**: Multi-language OCR with Japanese vertical text support
- 🥉 **PaddleOCR**: Chinese-developed OCR with high Asian language accuracy

**API Engines (Limited Use)**
- 🔹 **Gemini API**: Limited to 10 requests/session due to quota restrictions
- 🔹 **OpenAI GPT-4**: For specialized correction tasks

## 🎌 Specialized for Japanese Historical Documents

### Document Types Supported
- **Meiji Era Statistics** (明治時代統計資料)
- **Government Records** (公文書)
- **Traditional Tables** (伝統的表形式)
- **Vertical Text Documents** (縦書き文書)

### Language Features
- Traditional characters preservation (旧字体維持)
- Vertical text reading order (縦書き読み順)
- Historical terminology recognition
- Complex table structure analysis

## 📦 Installation & Quick Start

### Prerequisites
```bash
# Clone the repository
git clone git@github.com:DaichiHa/OCR-Engine.git
cd OCR-Engine

# Install dependencies
pip install -r requirements.txt
```

### Basic Usage
```bash
# Local processing with Qwen (recommended)
python hybrid_ocr_runner.py --input ./images --output ./results

# Single image processing
python hybrid_ocr_runner.py --input document.png --output ./results --single

# Enable limited Gemini support (10 requests max)
python hybrid_ocr_runner.py --input ./images --output ./results --enable-gemini --gemini-key api_key.txt
```

## 🛠️ Available Processing Scripts

### Main Engines
- `hybrid_ocr_runner.py` - **NEW**: Unified processing with Qwen + fallbacks
- `qwen_ocr_engine.py` - **NEW**: Core Qwen-2.5 integration module

### Legacy Engines (Still Available)
- `gemini_ocr.py` - Google Gemini API processing
- `ocr_ensemble.py` - Multi-engine ensemble approach
- `local_ensemble_ocr.py` - Local multi-processing system
- `paddleocr_test.py` - PaddleOCR specialized processing

### Table Extraction
- `table_extractor_v4.py` - Latest table structure detection
- `table_extractor_v3.py` - Projection profile method
- `table_extractor_v2.py` - Robust line detection
- `table_extractor.py` - Basic grid extraction

### Batch Processing
- `bulk_archive_ocr.py` - Large-scale document processing
- `main_batch.py` - Automated batch workflows
- `parallel_test.py` - Multi-threaded processing

## 🔧 Configuration Examples

### High-Precision Mode (Qwen Primary)
```bash
python hybrid_ocr_runner.py \
    --input "historical_documents/" \
    --output "processed/" \
    --qwen-model "Qwen/Qwen2-VL-32B-Instruct" \
    --max-workers 2
```

### Resource-Optimized Mode
```bash
python hybrid_ocr_runner.py \
    --input "documents/" \
    --output "results/" \
    --qwen-model "Qwen/Qwen2-VL-7B-Instruct" \
    --max-workers 4
```

### CPU-Only Mode (No GPU Required)
```bash
python hybrid_ocr_runner.py \
    --input "documents/" \
    --output "results/" \
    --disable-qwen \
    --max-workers 8
```

## 📊 Performance Comparison

| Engine | Accuracy (Japanese) | Speed | Resource | API Limit |
|--------|-------------------|-------|----------|-----------|
| **Qwen-2.5** | 95-98% | Fast | GPU Preferred | None |
| **Tesseract** | 70-85% | Very Fast | CPU Only | None |
| **PaddleOCR** | 80-90% | Fast | CPU/GPU | None |
| **Gemini** | 90-95% | Medium | API Call | 10/session |

## 🚨 API Limitation Strategy

Due to recent API restrictions:

### 🎯 **Recommended Approach**
1. **Primary**: Use Qwen-2.5 for unlimited local processing
2. **Fallback**: Tesseract for basic extraction when needed
3. **Special Cases**: Gemini API for critical verification (sparingly)

### 💰 **Cost Optimization**
- **Free Processing**: Qwen + Tesseract (100% local)
- **Minimal API Cost**: Gemini limited to 10 requests max
- **No Surprise Bills**: Hard limits prevent quota overrun

## 📁 Output Formats

### Structured Output
```json
{
  "document_type": "table",
  "confidence": "high",
  "tables": [
    {
      "caption": "明治三十九年港湾統計",
      "rows": [["品目", "数量", "價額"], ["米", "1,234石", "5,678圓"]]
    }
  ]
}
```

### Markdown Tables
```markdown
| 品目 | 数量 | 價額 |
|------|------|------|
| 米 | 1,234石 | 5,678圓 |
| 大豆 | 987石 | 4,321圓 |
```

## 🔍 Advanced Features

### Hybrid Processing Pipeline
1. **Image Preprocessing**: Noise reduction, orientation correction
2. **Structure Detection**: Table grid identification, text region segmentation  
3. **Multi-Engine OCR**: Qwen primary + Tesseract fallback + optional Gemini
4. **Results Fusion**: Confidence-based selection and error correction
5. **Format Output**: JSON, Markdown, CSV, or plain text

### Quality Assurance
- Multi-variant processing for critical cells
- Confidence scoring and error detection
- Historical character validation
- Structure integrity verification

## 🛟 Troubleshooting

### Common Issues

**GPU Memory Error**
```bash
# Use smaller Qwen model
--qwen-model "Qwen/Qwen2-VL-2B-Instruct"

# Switch to CPU-only
--disable-qwen
```

**API Quota Exceeded**
```bash
# System automatically continues with local engines
# No action needed - processing won't stop
```

**Poor OCR Quality**
```bash
# Enable ensemble mode for difficult documents
python ocr_ensemble.py --input document.png
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)  
5. Open Pull Request

## 📜 License

This project is open source and available under the [MIT License](LICENSE).

## 🔗 Related Projects

- [Docling](https://github.com/docling-project/docling) - Document AI processing
- [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) - Practical OCR tools
- [Tesseract](https://github.com/tesseract-ocr/tesseract) - Open source OCR engine

---

> **Philosophy**: "Local first, unlimited capability, API assist when needed"

Built for researchers, archivists, and developers working with Japanese historical documents in the post-API-limitation era.
