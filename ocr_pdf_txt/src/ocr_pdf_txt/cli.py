"""Command-line interface for PDF text extraction."""

from __future__ import annotations

import argparse
from pathlib import Path

from .pdf_extract import extract_text_layers


def _write_page_texts(page_texts: list[str], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for index, text in enumerate(page_texts, start=1):
        page_name = f"page_{index:04d}.txt"
        (output_dir / page_name).write_text(text, encoding="utf-8")


def _write_book_text(page_texts: list[str], output_dir: Path) -> None:
    book_path = output_dir / "book.txt"
    book_path.write_text("\n\n".join(page_texts), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extract PDF text-layer into per-page files and a combined book.txt."
    )
    parser.add_argument("input_pdf", type=Path, help="Path to the input PDF file.")
    parser.add_argument(
        "output_dir",
        type=Path,
        help="Directory to write page_XXXX.txt files and book.txt.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    page_texts = extract_text_layers(args.input_pdf)
    _write_page_texts(page_texts, args.output_dir)
    _write_book_text(page_texts, args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
