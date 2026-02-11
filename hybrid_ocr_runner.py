#!/usr/bin/env python3
"""
Hybrid OCR Runner
Main Engine: Qwen-2.5-32B (Local, High Precision)  
Supporting: Tesseract (Local Fallback), Gemini API (Nano Limited Use)
Based on OCR-Engine project patterns with API limitation adaptation
"""

import os
import argparse
import json
import time
from pathlib import Path
from typing import List, Dict, Optional
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from qwen_ocr_engine import QwenOCREngine

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class HybridOCRRunner:
    """
    Hybrid OCR Runner combining multiple engines for optimal results
    """
    
    def __init__(self, use_qwen: bool = True, use_tesseract: bool = True, 
                 use_gemini: bool = False, qwen_model: str = "Qwen/Qwen2-VL-7B-Instruct",
                 gemini_api_key: Optional[str] = None):
        """
        Initialize hybrid OCR system
        
        Args:
            use_qwen: Enable Qwen-2.5 OCR engine (MAIN ENGINE)
            use_tesseract: Enable Tesseract OCR engine  
            use_gemini: Enable Gemini API (LIMITED USE - for nano processing)
            qwen_model: Qwen model identifier
            gemini_api_key: Gemini API key (optional, for limited use)
        """
        self.use_qwen = use_qwen
        self.use_tesseract = use_tesseract
        self.use_gemini = use_gemini
        self.gemini_requests_count = 0  # Track Gemini usage
        self.max_gemini_requests = 10   # Nano limit per session
        
        # Initialize Qwen engine if requested (MAIN ENGINE)
        if self.use_qwen:
            try:
                logger.info("Initializing Qwen OCR Engine...")
                self.qwen_engine = QwenOCREngine(model_name=qwen_model)
                logger.info("Qwen OCR Engine ready")
            except Exception as e:
                logger.error(f"Failed to initialize Qwen: {e}")
                self.use_qwen = False
        
        # Initialize Tesseract if requested
        if self.use_tesseract:
            try:
                import pytesseract
                self.tesseract = pytesseract
                logger.info("Tesseract OCR Engine ready")
            except ImportError:
                logger.warning("Tesseract not available, disabling")
                self.use_tesseract = False
        
        # Initialize Gemini if requested (NANO USE ONLY)
        if self.use_gemini:
            try:
                import google.generativeai as genai
                if gemini_api_key:
                    genai.configure(api_key=gemini_api_key)
                    self.gemini = genai.GenerativeModel('gemini-2.0-flash')
                    logger.info(f"Gemini OCR Engine ready (NANO mode: max {self.max_gemini_requests} requests)")
                else:
                    logger.warning("Gemini API key not provided, disabling Gemini")
                    self.use_gemini = False
            except Exception as e:
                logger.error(f"Failed to initialize Gemini: {e}")
                self.use_gemini = False
    
    def process_single_image(self, image_path: str, output_dir: str, 
                           page_name: Optional[str] = None) -> Dict[str, any]:
        """
        Process single image with all available engines
        
        Args:
            image_path: Path to input image
            output_dir: Output directory
            page_name: Custom page identifier
            
        Returns:
            Processing results dictionary
        """
        if page_name is None:
            page_name = Path(image_path).stem
        
        os.makedirs(output_dir, exist_ok=True)
        
        results = {
            "image_path": image_path,
            "page_name": page_name,
            "timestamp": time.time(),
            "engines_used": [],
            "outputs": {}
        }
        
        # Process with Qwen if available
        if self.use_qwen:
            try:
                logger.info(f"Processing {page_name} with Qwen...")
                qwen_start = time.time()
                
                # Extract both structured and table formats
                structured_result = self.qwen_engine.extract_document(
                    image_path, mode="structured"
                )
                table_result = self.qwen_engine.extract_document(
                    image_path, mode="table"
                )
                
                # Save Qwen results
                qwen_structured_path = os.path.join(output_dir, f"{page_name}_qwen_structured.json")
                qwen_table_path = os.path.join(output_dir, f"{page_name}_qwen_table.md")
                
                with open(qwen_structured_path, 'w', encoding='utf-8') as f:
                    json.dump(structured_result, f, ensure_ascii=False, indent=2)
                
                with open(qwen_table_path, 'w', encoding='utf-8') as f:
                    if 'content' in table_result:
                        f.write(table_result['content'])
                    else:
                        f.write(str(table_result))
                
                qwen_time = time.time() - qwen_start
                
                results["engines_used"].append("qwen")
                results["outputs"]["qwen"] = {
                    "structured_path": qwen_structured_path,
                    "table_path": qwen_table_path,
                    "processing_time": qwen_time,
                    "success": True
                }
                
                logger.info(f"Qwen processing completed in {qwen_time:.2f}s")
                
            except Exception as e:
                logger.error(f"Qwen processing failed for {page_name}: {e}")
                results["outputs"]["qwen"] = {
                    "success": False,
                    "error": str(e)
                }
        
        # Process with Tesseract if available (basic fallback)
        if self.use_tesseract:
            try:
                logger.info(f"Processing {page_name} with Tesseract...")
                tesseract_start = time.time()
                
                from PIL import Image
                img = Image.open(image_path)
                
                # Multiple Tesseract configurations for Japanese
                configs = [
                    ('jpn_vert', '--oem 3 --psm 5'),  # Vertical text
                    ('jpn+eng', '--oem 3 --psm 6'),   # Mixed languages
                    ('jpn', '--oem 3 --psm 3')        # Auto segmentation
                ]
                
                tesseract_results = {}
                for lang, config in configs:
                    try:
                        text = self.tesseract.image_to_string(img, lang=lang, config=config)
                        tesseract_results[f"{lang}_{config.replace(' ', '_')}"] = text.strip()
                    except Exception as e:
                        logger.warning(f"Tesseract config {lang} {config} failed: {e}")
                
                # Save Tesseract results
                tesseract_path = os.path.join(output_dir, f"{page_name}_tesseract.json")
                with open(tesseract_path, 'w', encoding='utf-8') as f:
                    json.dump(tesseract_results, f, ensure_ascii=False, indent=2)
                
                tesseract_time = time.time() - tesseract_start
                
                results["engines_used"].append("tesseract")
                results["outputs"]["tesseract"] = {
                    "output_path": tesseract_path,
                    "processing_time": tesseract_time,
                    "success": True,
                    "configs_tried": len(configs)
                }
                
                logger.info(f"Tesseract processing completed in {tesseract_time:.2f}s")
                
            except Exception as e:
                logger.error(f"Tesseract processing failed for {page_name}: {e}")
                results["outputs"]["tesseract"] = {
                    "success": False,
                    "error": str(e)
                }
        
        # Process with Gemini if available (NANO USE - very limited)
        if (self.use_gemini and 
            self.gemini_requests_count < self.max_gemini_requests):
            try:
                logger.info(f"Processing {page_name} with Gemini (request {self.gemini_requests_count + 1}/{self.max_gemini_requests})...")
                gemini_start = time.time()
                
                from PIL import Image
                img = Image.open(image_path)
                img.thumbnail((2048, 2048))  # Reduce size for API efficiency
                
                # Simple Japanese historical document prompt
                gemini_prompt = """
                この画像は明治時代の日本の統計資料です。
                Markdown形式の表として抽出してください。
                旧字体（價額、数量など）をそのまま再現してください。
                説明は不要です。表のみ出力してください。
                """
                
                response = self.gemini.generate_content([gemini_prompt, img])
                self.gemini_requests_count += 1
                
                # Save Gemini result
                gemini_path = os.path.join(output_dir, f"{page_name}_gemini_nano.md")
                with open(gemini_path, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                
                gemini_time = time.time() - gemini_start
                
                results["engines_used"].append("gemini_nano")
                results["outputs"]["gemini_nano"] = {
                    "output_path": gemini_path,
                    "processing_time": gemini_time,
                    "success": True,
                    "requests_used": self.gemini_requests_count,
                    "requests_remaining": self.max_gemini_requests - self.gemini_requests_count
                }
                
                logger.info(f"Gemini nano processing completed in {gemini_time:.2f}s ({self.gemini_requests_count}/{self.max_gemini_requests} used)")
                
            except Exception as e:
                logger.error(f"Gemini nano processing failed for {page_name}: {e}")
                results["outputs"]["gemini_nano"] = {
                    "success": False,
                    "error": str(e)
                }
        elif self.use_gemini:
            logger.warning(f"Gemini nano quota exhausted ({self.gemini_requests_count}/{self.max_gemini_requests}), skipping")
        
        return results
    
    def batch_process(self, input_dir: str, output_dir: str, 
                     pattern: str = "*.png", max_workers: int = 2) -> List[Dict]:
        """
        Process multiple images in parallel
        
        Args:
            input_dir: Directory containing input images
            output_dir: Output directory
            pattern: File pattern to match
            max_workers: Maximum parallel workers
            
        Returns:
            List of processing results
        """
        import glob
        
        # Find all matching images
        image_files = glob.glob(os.path.join(input_dir, pattern))
        image_files.sort()
        
        logger.info(f"Found {len(image_files)} images to process")
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Process in parallel
        results = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_image = {
                executor.submit(self.process_single_image, img_file, output_dir): img_file
                for img_file in image_files
            }
            
            # Collect results
            for future in as_completed(future_to_image):
                img_file = future_to_image[future]
                try:
                    result = future.result()
                    results.append(result)
                    logger.info(f"Completed: {Path(img_file).name}")
                except Exception as e:
                    logger.error(f"Failed to process {img_file}: {e}")
                    results.append({
                        "image_path": img_file,
                        "success": False,
                        "error": str(e)
                    })
        
        # Save batch summary
        summary_path = os.path.join(output_dir, "batch_summary.json")
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump({
                "total_images": len(image_files),
                "successful": len([r for r in results if r.get("engines_used")]),
                "failed": len([r for r in results if not r.get("engines_used")]),
                "engines_used": list(set().union(*[r.get("engines_used", []) for r in results])),
                "results": results
            }, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Batch processing complete. Summary saved to {summary_path}")
        
        return results

def main():
    """
    Main CLI interface for Hybrid OCR Runner
    """
    parser = argparse.ArgumentParser(description="Hybrid OCR Runner - Qwen + Traditional OCR")
    
    parser.add_argument("--input", required=True, help="Input directory or single image file")
    parser.add_argument("--output", required=True, help="Output directory")
    parser.add_argument("--pattern", default="*.png", help="File pattern for batch processing")
    parser.add_argument("--qwen-model", default="Qwen/Qwen2-VL-7B-Instruct", 
                       help="Qwen model name")
    parser.add_argument("--disable-qwen", action="store_true", help="Disable Qwen OCR (MAIN ENGINE)")
    parser.add_argument("--disable-tesseract", action="store_true", help="Disable Tesseract OCR")
    parser.add_argument("--enable-gemini", action="store_true", help="Enable Gemini API (NANO use - very limited)")
    parser.add_argument("--gemini-key", help="Gemini API key file path")
    parser.add_argument("--max-workers", type=int, default=2, help="Maximum parallel workers")
    parser.add_argument("--single", action="store_true", help="Process single image")
    
    args = parser.parse_args()
    
    # Load Gemini API key if provided
    gemini_key = None
    if args.enable_gemini and args.gemini_key:
        try:
            with open(args.gemini_key, 'r') as f:
                gemini_key = f.read().strip()
        except Exception as e:
            logger.warning(f"Could not load Gemini key: {e}")
    
    # Initialize runner
    runner = HybridOCRRunner(
        use_qwen=not args.disable_qwen,
        use_tesseract=not args.disable_tesseract,
        use_gemini=args.enable_gemini,
        qwen_model=args.qwen_model,
        gemini_api_key=gemini_key
    )
    
    # Process based on mode
    if args.single or os.path.isfile(args.input):
        # Single image processing
        logger.info(f"Processing single image: {args.input}")
        result = runner.process_single_image(args.input, args.output)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        # Batch processing
        logger.info(f"Starting batch processing: {args.input} -> {args.output}")
        results = runner.batch_process(
            args.input, 
            args.output, 
            pattern=args.pattern,
            max_workers=args.max_workers
        )
        logger.info(f"Processed {len(results)} images")

if __name__ == "__main__":
    main()