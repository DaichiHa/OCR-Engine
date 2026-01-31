
import os
import glob
import subprocess
import time
import cv2
import numpy as np

# --- 設定 (LOCAL-ULTRA 追及テスト) ---
INPUT_DIR = "pages_ultra_preprocessed" # 今回作成した軽量・高精細画像を使用
OUTPUT_DIR = "local_ultra_results"
TESS_LANG = "jpn_vert+jpn" # 縦書き・横書きハイブリッド

# Tesseractの「限界」を引き出すための設定(PSM 6: 単一の均一なテキストブロック)
TESS_CONFIG = "--psm 6 --oem 1 -c preserve_interword_spaces=1"

def process_local_ultra(img_path):
    try:
        filename = os.path.basename(img_path)
        page_base = filename.replace(".png", "")
        out_txt_base = os.path.join(OUTPUT_DIR, page_base)
        
        print(f"[{time.strftime('%H:%M:%S')}] Local-ULTRA analyzing: {filename}...")
        
        # 1. ローカル実行 (Tesseract)
        # プレプロセス済みの画像を使用するため、認識率は通常より格段に上がるはず
        cmd = [
            'tesseract',
            img_path,
            out_txt_base,
            '-l', TESS_LANG,
            '--psm', '6',
            '--oem', '1'
        ]
        
        start = time.time()
        subprocess.run(cmd, check=True, capture_output=True)
        dur = time.time() - start
        
        print(f"   Done in {dur:.1f}s. (API制限なし・最高速)")
        return True
    except Exception as e:
        print(f"   Error: {e}")
        return False

def main():
    if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)
    
    # テスト対象: まだMD化できていないページ (P8, P9, P11, P12, P13)
    test_pages = ["page_008.png", "page_009.png", "page_011.png", "page_012.png", "page_013.png"]
    
    print("--- LOCAL-ULTRA PEAK PRECISION TEST (No API) ---")
    print(f"Testing {len(test_pages)} pages using locally optimized engine...")

    for fname in test_pages:
        img_path = os.path.join(INPUT_DIR, fname)
        if not os.path.exists(img_path):
            img_path = os.path.join("pages", fname) # バックアップ
            
        process_local_ultra(img_path)

    print(f"\n--- Local Test Complete. Check results in {OUTPUT_DIR} ---")

if __name__ == "__main__":
    main()
