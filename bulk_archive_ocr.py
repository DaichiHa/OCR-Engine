import glob
import os
import subprocess
import time

import google.generativeai as genai
from PIL import Image

# --- 設定 ---
KEY_FILE = "gemini_api_key.txt"
PDF_DIR = "./"  # 直下の全PDFが対象
OUTPUT_ROOT = "digital_archives_ultra"  # 全成果物のルート
EXTRACT_DIR = "temp_extracted_pages"  # 画像抽出用
INTERVAL = 65  # 無料枠の最安定インターバル（1分超え）
MODELS = ["gemini-3-flash-preview", "gemini-2.0-flash"]  # 交互に使用

PROMPT = """
あなたは歴史的な公文書（明治時代の日本の統計資料）をデジタル化する専門家です。
この画像を解析し、以下の指示に従ってMarkdown形式で出力してください。

1. **テキストページ（序文・凡例など）**:
   - 縦書きの文章を、日本語の自然な順序で正しく書き起こしてください。
   - 旧字体や助詞（ニ、ヲ、ハ）もそのまま再現してください。

2. **統計表ページ**:
   - 表の行列を1マスもずらさずにMarkdownテーブルで再現してください。
   - 単位、コンマの位置を正確に維持。

3. **出力形式**:
   - Markdownの本文のみ。
"""


def load_key():
    with open(KEY_FILE, "r") as f:
        return f.read().strip()


def extract_pdf_pages(pdf_path):
    pdf_name = os.path.basename(pdf_path).replace(".pdf", "")
    target_dir = os.path.join(EXTRACT_DIR, pdf_name)
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
        print(f"Extracting: {pdf_path} ...")
        # ImageMagickを使用して全ページを300dpiでPNG化
        # [0-999] は全ページを意味する一般的な指定
        cmd = f'magick -density 300 "{pdf_path}" "{target_dir}/page_%03d.png"'
        subprocess.run(cmd, shell=True)
    return target_dir


def process_single_image(task):
    img_path, md_path, model_name = task
    if os.path.exists(md_path) and os.path.getsize(md_path) > 100:
        return True

    print(f"[Queue] Processing {os.path.basename(img_path)} via {model_name}")
    api_key = load_key()
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)

    for attempt in range(5):
        try:
            img = Image.open(img_path)
            img.thumbnail((2560, 2560))
            response = model.generate_content([PROMPT, img])

            with open(md_path, "w", encoding="utf-8") as f:
                f.write(response.text)

            print(f"[Success] {os.path.basename(img_path)}")
            time.sleep(INTERVAL)  # 固定インターバルで極限まで安定させる
            return True
        except Exception as e:
            if "429" in str(e):
                wait = 180  # 制限時は3分休む
                print(f"[Wait] Quota Hit. Sleeping {wait}s...")
                time.sleep(wait)
            else:
                print(f"[Error] {e}")
                time.sleep(10)
    return False


def main():
    if not os.path.exists(OUTPUT_ROOT):
        os.makedirs(OUTPUT_ROOT)

    # 1. PDFを検索
    pdf_files = glob.glob(os.path.join(PDF_DIR, "*.pdf"))
    print(f"Found {len(pdf_files)} PDF files.")

    for pdf_path in pdf_files:
        # 2. PDFから画像を抽出
        img_dir = extract_pdf_pages(pdf_path)
        pdf_name = os.path.basename(pdf_path).replace(".pdf", "")
        out_md_dir = os.path.join(OUTPUT_ROOT, pdf_name)
        if not os.path.exists(out_md_dir):
            os.makedirs(out_md_dir)

        # 3. ページごとにタスクを作成
        img_files = sorted(glob.glob(os.path.join(img_dir, "*.png")))
        print(f"PDF '{pdf_name}' has {len(img_files)} pages. Starting conversion...")

        for i, img_path in enumerate(img_files):
            page_name = os.path.basename(img_path).replace(".png", ".md")
            md_path = os.path.join(out_md_dir, page_name)
            model_name = MODELS[i % len(MODELS)]

            # 安定のため1枚ずつ実行するが、必要に応じて並列化も可能
            # ここでは「究極の安定」のため同期実行（ループ）を選択
            process_single_image((img_path, md_path, model_name))

    print("--- ALL ARCHIVES PROCESSED ---")


if __name__ == "__main__":
    main()
