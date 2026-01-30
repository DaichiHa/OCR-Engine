"""
Final Cleaner and Merger for "日本帝國港灣統計"
Merges manual high-quality intro with batch OCR results.
Cleans up OCR artifacts.
"""

import os
import glob
import re

def clean_ocr_text(text):
    """
    Clean up common OCR garbage from Tesseract (Japanese vertical/table).
    """
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        # 1. Remove lines that are just single pipes or very short garbage
        # Also remove lines that contain ONLY pipes and whitespace (empty table rows)
        if re.match(r'^[|\s]+$', line) or len(line.strip()) < 2:
            continue
            
        # 2. Fix spaced numbers "1 234" -> "1234" within cells
        # Sort of risky for sentences, but safe for table cells usually.
        # But let's be conservative.
        
        # 3. Remove "Matrix rain" garbage (high density of non-Kanji/Kana symbols)
        # Pass for now, too aggressive.
        
        cleaned_lines.append(line)
        
    return '\n'.join(cleaned_lines)

def merge_files(manual_file, intermediate_dir, output_file):
    
    # 1. Read Manual Intro
    with open(manual_file, 'r', encoding='utf-8') as f:
        manual_content = f.read()
        
    # 2. Read Batch Files
    # Skip pages that are covered by manual file? 
    # Manual file covers Intro (1-7) and Table 1 Start.
    # We will include All Statistics Pages (8-151) as a raw appendix 
    # or just start from Page 8.
    
    files = sorted(glob.glob(os.path.join(intermediate_dir, "page_*.md")))
    
    ocr_content_blocks = []
    
    for file_path in files:
        filename = os.path.basename(file_path)
        try:
            page_num = int(filename.replace('page_', '').replace('.md', ''))
        except:
            continue
            
        # Skip Intro pages (1-7) because Manual File has them better
        if page_num <= 7:
            continue
            
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        cleaned = clean_ocr_text(content)
        ocr_content_blocks.append(cleaned)
        
    # 3. Write Output
    with open(output_file, 'w', encoding='utf-8') as out:
        out.write(manual_content)
        out.write("\n\n" + "="*50 + "\n")
        out.write("## 統計データ (自動OCR処理分)\n")
        out.write("※以下のデータは自動処理により抽出されたものです。誤認識を含みます。\n")
        out.write("="*50 + "\n\n")
        
        for block in ocr_content_blocks:
            out.write(block)
            out.write("\n\n---\n\n")
            
    print(f"Merged Manual Intro + {len(ocr_content_blocks)} OCR Pages into {output_file}")

if __name__ == "__main__":
    manual_path = r"c:\Users\User\Downloads\日本帝國港灣統計_0001\日本帝國港灣統計_OCR.md"
    inter_dir = r"c:\Users\User\Downloads\日本帝國港灣統計_0001\intermediate_md_strong"
    final_path = r"c:\Users\User\Downloads\日本帝國港灣統計_0001\日本帝國港灣統計_Complete.md"
    
    if os.path.exists(manual_path) and os.path.isdir(inter_dir):
        merge_files(manual_path, inter_dir, final_path)
    else:
        print("Required files/directories not found.")
