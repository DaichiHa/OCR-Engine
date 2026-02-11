"""
Qwen-2.5-32B OCR Engine Integration
Based on OCR-Engine project structure, adapted for matatabi-engine
"""

import json
import logging
import os
import time
from typing import Dict, List, Optional

import torch
from PIL import Image
from transformers import AutoProcessor, Qwen2VLForConditionalGeneration

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QwenOCREngine:
    """
    Qwen-2.5 Vision Language Model for high-precision OCR
    Supports structured document extraction and table recognition
    """

    def __init__(
        self,
        model_name: str = "Qwen/Qwen2-VL-7B-Instruct",
        device: str = "auto",
    ):
        """
        Initialize Qwen OCR Engine

        Args:
            model_name: Hugging Face model identifier (7B for lighter version)
            device: Device placement ("auto", "cuda", "cpu")
        """
        logger.info(f"Loading Qwen model: {model_name}")

        self.model_name = model_name
        self.device = device

        # Load model with optimizations
        self.model = Qwen2VLForConditionalGeneration.from_pretrained(
            model_name,
            _torch_dtype=(
                torch.float16 if torch.cuda.is_available() else torch.float32
            ),
            _device_map=device,
            trust_remote_code=True,
        )

        self.processor = AutoProcessor.from_pretrained(
            model_name, trust_remote_code=True
        )

        # Japanese historical document prompts
        self.prompts = {
            "structured": self._get_structured_prompt(),
            "table": self._get_table_prompt(),
            "text": self._get_text_prompt(),
        }

    def _get_structured_prompt(self) -> str:
        """Japanese historical document structured extraction prompt"""
        return """
あなたは明治時代の日本の歴史的統計資料をデジタル化する専門家です。
この画像を解析し、以下の指示に従って構造化されたJSON形式で出力してください。

構造化要求:
{
  "document_type": "table|text|mixed",
  "title": "文書のタイトル（ある場合）",
  "sections": [
    {
      "type": "heading|table|paragraph",
      "content": "セクションの内容",
      "coordinates": {"x": 0, "y": 0, "width": 100, "height": 50},
      "confidence": "high|medium|low"
    }
  ],
  "tables": [
    {
      "caption": "表のタイトル",
      "rows": [
        ["セル1", "セル2", "セル3"],
        ["データ1", "データ2", "データ3"]
      ],
      "metadata": {
        "columns": 3,
        "rows": 2,
        "units": "石|圓|噸|斤など単位情報"
      }
    }
  ],
  "text_blocks": [
    {
      "content": "縦書き文章の内容",
      "reading_order": 1,
      "text_direction": "vertical|horizontal"
    }
  ]
}

重要な指示:
- 旧字体（價額、数量など）をそのまま再現
- 縦書き文章は自然な日本語順序で転写
- 表の構造を正確に維持
- 数値の単位（石、圓、噸など）を保持
"""

    def _get_table_prompt(self) -> str:
        """Table-specific extraction prompt"""
        return """
この画像は明治時代の統計表です。以下の形式でMarkdownテーブルとして抽出してください。

要求:
1. **表構造の完全再現**: 行列を1マスもずらさず再現
2. **数値精度**: コンマ、単位（石、圓、噸、斤）を正確に維持
3. **旧字体保持**: 價額、数量、輸出入などそのまま転写
4. **見出し構造**: 複雑な入れ子ヘッダーも階層を保って表現

出力形式: Markdownテーブルのみ（説明文不要）
"""

    def _get_text_prompt(self) -> str:
        """Text document extraction prompt"""
        return """
この画像は明治時代の公文書（序文・凡例など）の縦書き文章です。

要求:
1. **縦書き転写**: 日本語として自然な読み順で転写
2. **旧字体保持**: すべての文字をそのまま再現
3. **助詞保持**: ニ、ヲ、ハなどの助詞も正確に
4. **改行・段落**: 原文の段落構造を保持

出力: プレーンテキスト（Markdown不要）
"""

    def extract_document(
        self,
        image_path: str,
        mode: str = "structured",
        custom_prompt: Optional[str] = None,
    ) -> Dict:
        """
        Extract document content using Qwen vision model

        Args:
            image_path: Path to input image
            mode: Extraction mode ("structured", "table", "text")
            custom_prompt: Override default prompt

        Returns:
            Extraction results as dictionary
        """
        try:
            # Load and prepare image
            image = Image.open(image_path)

            # Use custom prompt or default
            prompt = custom_prompt or self.prompts.get(mode, self.prompts["structured"])

            # Prepare messages for Qwen
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": image},
                        {"type": "text", "text": prompt},
                    ],
                }
            ]

            # Process with Qwen
            text = self.processor.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )

            image_inputs, video_inputs = self.processor.process_vision_info(messages)
            inputs = self.processor(
                text=[text],
                images=image_inputs,
                _videos=video_inputs,
                _padding=True,
                _return_tensors="pt",
            )
            inputs = {k: v.to(self.model.device) for k, v in inputs.items()}

            # Generate response
            with torch.no_grad():
                generated_ids = self.model.generate(
                    **inputs,
                    _max_new_tokens=4096,
                    _do_sample=False,
                    _temperature=0.1,
                    pad_token_id=self.processor.tokenizer.pad_token_id,
                )

                generated_ids_trimmed = [
                    out_ids[len(in_ids) :]
                    for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
                ]

                output_text = self.processor.batch_decode(
                    generated_ids_trimmed,
                    _skip_special_tokens=True,
                    _clean_up_tokenization_spaces=False,
                )[0]

            # Parse result based on mode
            if mode == "structured":
                try:
                    return json.loads(output_text)
                except json.JSONDecodeError:
                    return {"raw_text": output_text, "parse_error": True}
            else:
                return {"content": output_text, "mode": mode}

        except Exception as e:
            logger.error(f"Error processing {image_path}: {e}")
            return {"error": str(e)}

    def batch_process(
        self,
        input_dir: str,
        output_dir: str,
        pattern: str = "*.png",
        mode: str = "structured",
    ) -> List[str]:
        """
        Process multiple images in batch

        Args:
            input_dir: Directory containing images
            output_dir: Directory for output files
            pattern: File pattern to match
            mode: Processing mode

        Returns:
            List of processed file paths
        """
        import glob

        os.makedirs(output_dir, exist_ok=True)

        image_files = glob.glob(os.path.join(input_dir, pattern))
        image_files.sort()

        results = []

        for image_file in image_files:
            logger.info(f"Processing: {os.path.basename(image_file)}")

            # Extract content
            result = self.extract_document(image_file, mode=mode)

            # Save result
            base_name = os.path.splitext(os.path.basename(image_file))[0]
            output_file = os.path.join(output_dir, f"{base_name}_qwen.json")

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

            results.append(output_file)

            # Brief pause to prevent overheating
            time.sleep(0.5)

        return results


# Integration with existing OCR-Engine patterns
def process_page_qwen(image_path: str, output_path: str, model_name: str = None):
    """
    Process single page compatible with OCR-Engine batch processing pattern
    Similar to gemini_ocr.py:process_page_ultra()
    """
    if model_name is None:
        model_name = "Qwen/Qwen2-VL-7B-Instruct"

    try:
        engine = QwenOCREngine(model_name=model_name)
        result = engine.extract_document(image_path, mode="table")

        # Save as markdown (compatible with existing pipeline)
        with open(output_path, "w", encoding="utf-8") as f:
            if "content" in result:
                f.write(result["content"])
            else:
                f.write(json.dumps(result, ensure_ascii=False, indent=2))

        logger.info(f"Saved: {output_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to process {image_path}: {e}")
        return False


def main():
    """
    Main function for testing Qwen OCR Engine
    Compatible with OCR-Engine project patterns
    """
    # Test configuration
    test_image = "pages/page_011.png"  # Table page
    output_dir = "qwen_output"

    if not os.path.exists(test_image):
        logger.warning(f"Test image not found: {test_image}")
        return

    os.makedirs(output_dir, exist_ok=True)

    # Initialize engine
    engine = QwenOCREngine()

    # Test different modes
    modes = ["structured", "table", "text"]

    for mode in modes:
        logger.info(f"Testing mode: {mode}")
        result = engine.extract_document(test_image, mode=mode)

        output_file = os.path.join(output_dir, f"test_{mode}.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        logger.info(f"Result saved to: {output_file}")


if __name__ == "__main__":
    main()
