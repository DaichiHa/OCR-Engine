"""
Resumable batch OCR for "日本帝國港灣統計".

This consolidates the behavior of:
- main_batch.py (single-pass batch)
- main_batch_robust.py (resumable, immediate save)
- main_batch_gamma.py (alternate page/output paths)

Usage:
  python main_batch_resumable.py \
    --pages-dir /path/to/pages \
    --intermediate-dir /path/to/intermediate_md \
    --output-file /path/to/Full_Output.md
"""

from __future__ import annotations

import argparse
import concurrent.futures
import glob
import os
import time
from dataclasses import dataclass
from typing import List, Tuple

import hybrid_extractor


@dataclass(frozen=True)
class BatchConfig:
    pages_dir: str
    intermediate_dir: str
    output_file: str
    text_page_min: int = 1
    text_page_max: int = 6
    max_workers: int = 4
    skip_existing: bool = True


def parse_args() -> BatchConfig:
    parser = argparse.ArgumentParser(
        description="Resumable batch OCR runner with per-page checkpoints."
    )
    parser.add_argument(
        "--pages-dir",
        required=True,
        help="Directory containing page_XXX.png files.",
    )
    parser.add_argument(
        "--intermediate-dir",
        required=True,
        help="Directory for per-page markdown checkpoints.",
    )
    parser.add_argument(
        "--output-file",
        required=True,
        help="Final combined markdown output file.",
    )
    parser.add_argument(
        "--text-page-min",
        type=int,
        default=1,
        help="First page index to treat as vertical text.",
    )
    parser.add_argument(
        "--text-page-max",
        type=int,
        default=6,
        help="Last page index to treat as vertical text.",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=4,
        help="Number of worker threads.",
    )
    parser.add_argument(
        "--no-skip-existing",
        action="store_true",
        help="Reprocess even if page checkpoint exists.",
    )

    args = parser.parse_args()
    return BatchConfig(
        pages_dir=args.pages_dir,
        intermediate_dir=args.intermediate_dir,
        output_file=args.output_file,
        text_page_min=args.text_page_min,
        text_page_max=args.text_page_max,
        max_workers=args.max_workers,
        skip_existing=not args.no_skip_existing,
    )


def list_page_tasks(pages_dir: str, intermediate_dir: str) -> List[Tuple[int, str, str]]:
    files = sorted([f for f in os.listdir(pages_dir) if f.lower().endswith(".png")])
    page_tasks: List[Tuple[int, str, str]] = []

    for filename in files:
        if filename.startswith("debug_") or filename.startswith("table_") or "debug" in filename:
            continue
        try:
            num_str = filename.split("_")[-1].split(".")[0]
            page_num = int(num_str)
        except ValueError:
            continue
        page_tasks.append((page_num, os.path.join(pages_dir, filename), intermediate_dir))

    page_tasks.sort(key=lambda item: item[0])
    return page_tasks


def process_and_save_page(
    page_info: Tuple[int, str, str],
    config: BatchConfig,
) -> Tuple[int, str, float]:
    page_num, image_path, output_dir = page_info
    md_filename = os.path.join(output_dir, f"page_{page_num:03d}.md")

    if config.skip_existing and os.path.exists(md_filename) and os.path.getsize(md_filename) > 10:
        return page_num, "Skipped", 0.0

    try:
        start_time = time.time()

        if config.text_page_min <= page_num <= config.text_page_max:
            content = hybrid_extractor.extract_vertical_text(image_path)
            result = f"\n\n## Page {page_num}\n\n{content}\n"
        else:
            rows = hybrid_extractor.extract_table_content(image_path)
            if not rows:
                result = f"\n\n## Page {page_num}\n\n(No table data detected)\n"
            else:
                lines = [f"\n\n## Page {page_num}"]
                for row in rows:
                    clean_row = [str(cell).replace("|", "") for cell in row if cell is not None]
                    lines.append("| " + " | ".join(clean_row) + " |")
                result = "\n".join(lines)

        os.makedirs(output_dir, exist_ok=True)
        with open(md_filename, "w", encoding="utf-8") as handle:
            handle.write(result)

        elapsed = time.time() - start_time
        return page_num, "Processed", elapsed
    except Exception as exc:  # noqa: BLE001 - surface processing errors in output
        error_msg = f"\n## Page {page_num}\nError: {exc}\n"
        os.makedirs(output_dir, exist_ok=True)
        with open(md_filename, "w", encoding="utf-8") as handle:
            handle.write(error_msg)
        return page_num, f"Error: {exc}", 0.0


def combine_results(intermediate_dir: str, output_file: str) -> None:
    files = sorted(glob.glob(os.path.join(intermediate_dir, "page_*.md")))
    with open(output_file, "w", encoding="utf-8") as outfile:
        outfile.write(
            "# 日本帝國港灣統計 OCR Result\n\n"
            "Generated by Hybrid Structure-Aware OCR (Resumable Batch)\n\n"
        )
        for md_file in files:
            with open(md_file, "r", encoding="utf-8") as infile:
                outfile.write(infile.read())
                outfile.write("\n\n---\n\n")

    print(f"Combined {len(files)} pages into {output_file}")


def run_batch(config: BatchConfig) -> None:
    os.makedirs(config.intermediate_dir, exist_ok=True)
    page_tasks = list_page_tasks(config.pages_dir, config.intermediate_dir)
    total = len(page_tasks)

    print(f"Starting resumable batch processing for {total} pages...")

    completed = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=config.max_workers) as executor:
        futures = {
            executor.submit(process_and_save_page, task, config): task for task in page_tasks
        }
        for future in concurrent.futures.as_completed(futures):
            page_info = futures[future]
            try:
                page_num, status, duration = future.result()
                completed += 1
                if status == "Skipped":
                    if completed % 10 == 0:
                        print(f"[{completed}/{total}] Skipped existing pages...")
                else:
                    print(f"[{completed}/{total}] Page {page_num} {status} in {duration:.2f}s")
            except Exception as exc:
                print(f"Worker failed for page {page_info[0]}: {exc}")

    print("Processing complete. Combining results...")
    combine_results(config.intermediate_dir, config.output_file)


def main() -> None:
    config = parse_args()
    run_batch(config)


if __name__ == "__main__":
    main()
