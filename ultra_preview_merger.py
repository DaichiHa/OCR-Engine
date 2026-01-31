
import os
import glob
import re

OUTPUT_DIR = "intermediate_md_ultra_final"
FINAL_FILE = "日本帝國港灣統計_ULTRA_PREVIEW.md"

def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower() for text in re.split('([0-9]+)', s)]

def merge_ultra_preview():
    files = sorted(glob.glob(os.path.join(OUTPUT_DIR, "page_*.md")), key=natural_sort_key)
    
    with open(FINAL_FILE, "w", encoding="utf-8") as outfile:
        outfile.write("# 日本帝國港灣統計 [ULTRA品質 プレビュー]\n\n")
        outfile.write("> 現在、最高精度モードで抽出中のデータを統合した暫定版です。\n\n")
        
        for fpath in files:
            fname = os.path.basename(fpath)
            page_num = re.search(r'page_(\d+)', fname).group(1)
            
            outfile.write(f"\n--- [Page {page_num}] ---\n\n")
            with open(fpath, "r", encoding="utf-8") as infile:
                content = infile.read().strip()
                outfile.write(content)
                outfile.write("\n")
                
    print(f"Merge Complete: {FINAL_FILE} ({len(files)} pages merged)")

if __name__ == "__main__":
    merge_ultra_preview()
