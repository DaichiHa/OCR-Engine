"""
Main Batch Processor for "日本帝國港灣統計"
Iterates through all 151 pages and applies appropriate OCR strategy.
"""

import concurrent.futures
import os
import time

import cv2
import hybrid_extractor
import ocr_advanced
import ocr_box_utils
import text_structure_analyzer

def process_single_page_task(page_info):
    """
    Process one page based on its number
    """
    page_num, image_path = page_info
    try:
        start_time = time.time()
        
        if 1 <= page_num <= 6:
            # Text Mode
            content = hybrid_extractor.extract_vertical_text(image_path)
            # Wrap in minimal markdown
            result = f"\n\n## Page {page_num}\n\n{content}\n"
            
        else:
            # Table Mode
            rows = hybrid_extractor.extract_table_content(image_path)
            if not rows:
                result = f"\n\n## Page {page_num}\n\n(No table data detected)\n"
            else:
                lines = []
                lines.append(f"\n\n## Page {page_num}")
                # Construct Markdown Table
                for row_idx, row in enumerate(rows):
                    # Clean up: Replace pipes with generic separator or escape them
                    clean_row = [str(c).replace('|', '') for c in row]
                    lines.append("| " + " | ".join(clean_row) + " |")
                result = "\n".join(lines)
        
        elapsed = time.time() - start_time
        return page_num, result, elapsed
        
    except Exception as e:
        return page_num, f"\n## Page {page_num}\nError: {str(e)}\n", 0


def format_table_rows(rows):
    return "\n".join(["\t".join([str(c) for c in row]) for row in rows])


def process_page_with_diagnostics(
    page_num,
    image_path,
    low_conf_threshold,
    wrinkle_density_threshold,
    engine_iou_threshold,
):
    if 1 <= page_num <= 6:
        text, primary_boxes, _ = ocr_advanced.ocr_page_with_boxes(
            image_path,
            page=page_num,
            lang="jpn_vert",
            psm=5,
        )
        secondary_text, secondary_boxes = hybrid_extractor.extract_vertical_text(
            image_path,
            return_boxes=True,
            page=page_num,
            engine_label="tesseract-vertical",
        )
        accepted_text = text
    else:
        rows, primary_boxes = hybrid_extractor.extract_table_content(
            image_path,
            return_boxes=True,
            page=page_num,
            engine_label="tesseract-table",
        )
        secondary_boxes = text_structure_analyzer.collect_tesseract_boxes(
            image_path,
            page=page_num,
            engine_label="tesseract-structure",
        )
        accepted_text = format_table_rows(rows) if rows else ""

    all_boxes = primary_boxes + secondary_boxes
    mismatch_keys = set(
        ocr_box_utils.find_engine_mismatches(
            primary_boxes,
            secondary_boxes,
            iou_threshold=engine_iou_threshold,
        )
    )

    img = hybrid_extractor.read_image_robust(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img is not None else None
    edge_map = ocr_box_utils.compute_edge_map(gray) if gray is not None else None

    diff_queue = []
    for box in all_boxes:
        flags = []
        if box["conf"] < low_conf_threshold:
            flags.append("low_conf")
        key = (box["page"], box["engine"], box["block_id"])
        if key in mismatch_keys:
            flags.append("engine_mismatch")
        if edge_map is not None and ocr_box_utils.is_wrinkle_suspect(
            edge_map,
            box["bbox"],
            density_threshold=wrinkle_density_threshold,
        ):
            flags.append("wrinkle_suspect")
        if flags:
            diff_queue.append({**box, "flags": flags})

    return accepted_text, all_boxes, diff_queue


def run_batch_with_diagnostics(
    pages_dir,
    output_dir,
    low_conf_threshold=60.0,
    wrinkle_density_threshold=0.35,
    engine_iou_threshold=0.5,
    max_workers=4,
):
    files = sorted([f for f in os.listdir(pages_dir) if f.lower().endswith('.png')])
    page_list = []
    for f in files:
        if f.startswith('debug_') or f.startswith('table_') or 'debug' in f:
            continue
        try:
            num_str = f.split('_')[-1].split('.')[0]
            num = int(num_str)
            page_list.append((num, os.path.join(pages_dir, f)))
        except Exception:
            continue

    page_list.sort(key=lambda x: x[0])
    raw_lines = []
    all_boxes = []
    diff_queue = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_page = {
            executor.submit(
                process_page_with_diagnostics,
                page_num,
                image_path,
                low_conf_threshold,
                wrinkle_density_threshold,
                engine_iou_threshold,
            ): (page_num, image_path)
            for page_num, image_path in page_list
        }
        for future in concurrent.futures.as_completed(future_to_page):
            page_num, _ = future_to_page[future]
            text, boxes, diffs = future.result()
            raw_lines.append((page_num, text))
            all_boxes.extend(boxes)
            diff_queue.extend(diffs)

    raw_lines.sort(key=lambda x: x[0])
    raw_text_path = os.path.join(output_dir, "raw.txt")
    boxes_path = os.path.join(output_dir, "boxes.jsonl")
    diff_queue_path = os.path.join(output_dir, "diff_queue.jsonl")

    with open(raw_text_path, "w", encoding="utf-8") as handle:
        for page_num, text in raw_lines:
            handle.write(f"## Page {page_num}\n")
            handle.write(text)
            handle.write("\n\n")

    ocr_box_utils.write_jsonl(boxes_path, all_boxes)
    ocr_box_utils.write_jsonl(diff_queue_path, diff_queue)

    return raw_text_path, boxes_path, diff_queue_path

if __name__ == "__main__":
    pages_dir = r"c:\Users\User\Downloads\日本帝國港灣統計_0001\pages"
    output_dir = pages_dir
    raw_text_path, boxes_path, diff_queue_path = run_batch_with_diagnostics(
        pages_dir,
        output_dir,
    )
    print(f"Processing complete. raw.txt: {raw_text_path}")
    print(f"boxes.jsonl: {boxes_path}")
    print(f"diff_queue.jsonl: {diff_queue_path}")
