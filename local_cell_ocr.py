import os

import cv2
import pytesseract

# --- LOCAL-ULTRA: CELL-BY-CELL RECONSTRUCTION ---
# APIを一切使わず、ローカルで画像を物理的に裁断してセルごとに認識
TARGET_PAGE = "pages/page_008.png"
OUTPUT_FILE = "extreme_quality_test/page_008_LOCAL_CELLS.md"
TESS_CONFIG = "-l jpn+eng --psm 7 --oem 1"  # 1行認識モード


def process_cell_ocr():
    if not os.path.exists("extreme_quality_test"):
        os.makedirs("extreme_quality_test")

    # 画像読み込み
    img = cv2.imread(TARGET_PAGE)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 二値化 (線を強調)
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

    # 横線の検出
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
    detect_horizontal = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, horizontal_kernel, iterations=2)

    # 縦線の検出
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
    detect_vertical = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, vertical_kernel, iterations=2)

    # 罫線の結合
    table_mask = cv2.addWeighted(detect_horizontal, 0.5, detect_vertical, 0.5, 0)
    table_mask = cv2.threshold(table_mask, 0, 255, cv2.THRESH_BINARY)[1]

    # セルの輪郭を抽出
    contours, _ = cv2.findContours(table_mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    # 矩形情報の取得
    rects = [cv2.boundingRect(c) for c in contours]
    # 小さすぎるノイズを除去、かつ座標順にソート (Y, X)
    rects = sorted(
        [r for r in rects if r[2] > 20 and r[3] > 10],
        key=lambda x: (x[1], x[0]),
    )

    print(f"Detected {len(rects)} cells. Starting Local-Cell-OCR...")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("# Page 008 Local Cell-by-Cell OCR\n\n")

        current_y = -1
        row_text = []

        for r in rects:
            x, y, w, h = r
            # 新しい行の判定
            if current_y == -1 or abs(y - current_y) > 15:
                if row_text:
                    f.write("| " + " | ".join(row_text) + " |\n")
                row_text = []
                current_y = y

            # セル画像を切り出し
            cell = gray[y : y + h, x : x + w]
            # 認識精度向上のための余白追加
            cell = cv2.copyMakeBorder(cell, 10, 10, 10, 10, cv2.BORDER_CONSTANT, value=255)

            # OCR実行
            text = pytesseract.image_to_string(cell, config=TESS_CONFIG).strip()
            # 改行やパイプをエスケープ
            clean_text = text.replace("\n", " ").replace("|", "\\|")
            row_text.append(clean_text)

        if row_text:
            f.write("| " + " | ".join(row_text) + " |\n")

    print(f"Success: {OUTPUT_FILE}")


if __name__ == "__main__":
    process_cell_ocr()
