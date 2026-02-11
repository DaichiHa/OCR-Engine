
import cv2
import os
import glob
from concurrent.futures import ProcessPoolExecutor

INPUT_DIR = "pages"
OUTPUT_DIR = "pages_ultra_preprocessed"

def preprocess_image(file_path):
    try:
        filename = os.path.basename(file_path)
        out_path = os.path.join(OUTPUT_DIR, filename)
        
        # すでに処理済みの場合はスキップ
        if os.path.exists(out_path):
            return True

        # 画像読み込み
        img = cv2.imread(file_path)
        if img is None:
            return False

        # 1. グレースケール化
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # 2. 適応型二値化 (Adaptive Thresholding)
        # 影や汚れを飛ばし、文字の輪郭だけを浮き上がらせる
        # 統計表の罫線を残すために、ブロックサイズは大きめに(15程度)
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )

        # 3. ノイズ除去 (Denoising)
        # メディアンフィルタで点状の汚れを除去
        denoised = cv2.medianBlur(thresh, 1)

        # 4. サイズ最適化 (解像度を維持しつつ容量削減)
        # 2k〜3k解像度は維持（文字認識のため）
        
        # PNGとして保存。各カラーチャンネルがないため容量が劇的に減る
        cv2.imwrite(out_path, denoised, [cv2.IMWRITE_PNG_COMPRESSION, 9])
        
        return True
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    files = glob.glob(os.path.join(INPUT_DIR, "page_*.png"))
    print(f"Starting Preprocessing of {len(files)} pages...")
    
    # 高速化のためマルチプロセス（並列）で画像処理
    with ProcessPoolExecutor() as executor:
        executor.map(preprocess_image, files)

    print(f"Preprocessing Complete. Ultra-light images stored in {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
