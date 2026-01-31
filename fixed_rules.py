"""
Fixed-rule utilities for OCR pipeline:
- Band splitting (header/body/footer)
- Table heuristic detection
- OCR TSV quality scoring
- Variant table generation from corpus + Unihan_Variants
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np


@dataclass(frozen=True)
class BandSplit:
    head: Path
    body: Path
    foot: Path


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def split_fixed_bands(
    image_path: Path,
    output_dir: Path,
    ratios: Tuple[float, float, float] = (0.12, 0.78, 0.10),
    prefix: str | None = None,
) -> BandSplit:
    import cv2
    import numpy as np

    if not image_path.exists():
        raise FileNotFoundError(image_path)

    if len(ratios) != 3 or not np.isclose(sum(ratios), 1.0, atol=1e-3):
        raise ValueError(f"ratios must sum to 1.0, got {ratios}")

    img = cv2.imread(str(image_path), cv2.IMREAD_UNCHANGED)
    if img is None:
        raise ValueError(f"Failed to read image: {image_path}")

    height, width = img.shape[:2]
    head_h = int(round(height * ratios[0]))
    body_h = int(round(height * ratios[1]))
    foot_h = height - head_h - body_h

    if head_h <= 0 or body_h <= 0 or foot_h <= 0:
        raise ValueError("Band heights must be positive")

    prefix = prefix or image_path.stem
    _ensure_dir(output_dir)

    head_path = output_dir / f"{prefix}_head.png"
    body_path = output_dir / f"{prefix}_body.png"
    foot_path = output_dir / f"{prefix}_foot.png"

    cv2.imwrite(str(head_path), img[:head_h, :])
    cv2.imwrite(str(body_path), img[head_h : head_h + body_h, :])
    cv2.imwrite(str(foot_path), img[height - foot_h :, :])

    return BandSplit(head=head_path, body=body_path, foot=foot_path)


def _line_density(binary: "np.ndarray") -> float:
    import cv2
    import numpy as np

    height, width = binary.shape[:2]
    horiz_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(10, width // 30), 1))
    vert_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(10, height // 30)))

    horiz = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horiz_kernel, iterations=1)
    vert = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vert_kernel, iterations=1)

    line_pixels = np.count_nonzero(horiz) + np.count_nonzero(vert)
    return line_pixels / (height * width)


def _ocr_text_for_heuristics(gray: "np.ndarray") -> str:
    import pytesseract

    config = "--oem 1 --psm 6"
    return pytesseract.image_to_string(gray, lang="jpn", config=config)


def detect_table_heuristic(
    image_path: Path,
    text: str | None = None,
    digit_ratio_threshold: float = 0.2,
    whitespace_ratio_threshold: float = 0.05,
    line_ratio_threshold: float = 0.01,
) -> Tuple[bool, Dict[str, float]]:
    import cv2

    img = cv2.imread(str(image_path), cv2.IMREAD_UNCHANGED)
    if img is None:
        raise ValueError(f"Failed to read image: {image_path}")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)

    if text is None:
        text = _ocr_text_for_heuristics(gray)

    stripped = re.sub(r"\s+", "", text)
    total_chars = max(len(stripped), 1)
    digit_ratio = sum(ch.isdigit() for ch in stripped) / total_chars

    whitespace_matches = list(re.finditer(r" {2,}", text))
    whitespace_chars = sum(len(match.group(0)) for match in whitespace_matches)
    whitespace_ratio = whitespace_chars / max(len(text), 1)

    line_ratio = _line_density(binary)

    is_table = (
        digit_ratio >= digit_ratio_threshold
        or whitespace_ratio >= whitespace_ratio_threshold
        or line_ratio >= line_ratio_threshold
    )

    metrics = {
        "digit_ratio": digit_ratio,
        "whitespace_ratio": whitespace_ratio,
        "line_ratio": line_ratio,
    }

    return is_table, metrics


def choose_body_psm(is_table: bool) -> int:
    return 6 if is_table else 5


def _is_blank_like(text: str) -> bool:
    if not text:
        return True
    return re.fullmatch(r"[\W_]+", text) is not None


def score_tsv(
    tsv_path: Path,
    low_conf_threshold: int = 60,
    warn_conf_threshold: int = 70,
    pass_conf_threshold: int = 85,
    warn_low_ratio: float = 0.30,
    pass_low_ratio: float = 0.15,
) -> Dict[str, float | str]:
    with tsv_path.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        confs: List[int] = []
        texts: List[str] = []
        for row in reader:
            try:
                conf = int(row.get("conf", "-1"))
            except ValueError:
                conf = -1
            if conf != -1:
                confs.append(conf)
            texts.append(row.get("text", ""))

    mean_conf = float(sum(confs) / len(confs)) if confs else 0.0
    low_ratio = float(sum(conf < low_conf_threshold for conf in confs) / len(confs)) if confs else 1.0
    blank_ratio = float(sum(_is_blank_like(text.strip()) for text in texts) / len(texts)) if texts else 1.0

    if mean_conf >= pass_conf_threshold and low_ratio <= pass_low_ratio:
        status = "PASS"
    elif mean_conf < warn_conf_threshold or low_ratio > warn_low_ratio:
        status = "FAIL"
    else:
        status = "WARN"

    return {
        "mean_conf": mean_conf,
        "low_ratio": low_ratio,
        "blank_ratio": blank_ratio,
        "status": status,
    }


def _iter_texts(paths: Iterable[Path]) -> str:
    chunks: List[str] = []
    for path in paths:
        chunks.append(path.read_text(encoding="utf-8"))
    return "\n".join(chunks)


def character_frequencies(text: str) -> Counter:
    return Counter(ch for ch in text if not ch.isspace())


def _is_variant_like(char: str) -> bool:
    code = ord(char)
    if 0xFE00 <= code <= 0xFE0F:
        return True
    if 0xF900 <= code <= 0xFAFF:
        return True
    name = unicodedata.name(char, "")
    return "CJK UNIFIED IDEOGRAPH" in name and "COMPATIBILITY" in name


def select_candidate_chars(freqs: Counter, top_n: int = 500) -> List[str]:
    return [char for char, _ in freqs.most_common(top_n)]


def load_unihan_variants(unihan_path: Path) -> Dict[str, Dict[str, List[str]]]:
    variants: Dict[str, Dict[str, List[str]]] = {}
    with unihan_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip() or line.startswith("#"):
                continue
            parts = line.strip().split("\t")
            if len(parts) != 3:
                continue
            codepoint, field, value = parts
            if field not in {"kTraditionalVariant", "kSimplifiedVariant"}:
                continue
            char = chr(int(codepoint[2:], 16))
            values = [v for v in value.split() if v.startswith("U+")]
            mapped = [chr(int(v[2:], 16)) for v in values]
            variants.setdefault(char, {}).setdefault(field, []).extend(mapped)
    return variants


def build_variant_map(
    candidates: Iterable[str],
    unihan_variants: Dict[str, Dict[str, List[str]]],
    prefer_simplified: bool = True,
) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    for char in candidates:
        fields = unihan_variants.get(char, {})
        preferred_field = "kSimplifiedVariant" if prefer_simplified else "kTraditionalVariant"
        fallback_field = "kTraditionalVariant" if prefer_simplified else "kSimplifiedVariant"

        target_list = fields.get(preferred_field) or fields.get(fallback_field) or []
        if not target_list:
            continue
        target = target_list[0]
        if target != char:
            mapping[char] = target
    return mapping


def write_variants_tsv(mapping: Dict[str, str], output_path: Path) -> None:
    lines = [f"{src}\t{dst}" for src, dst in mapping.items()]
    output_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def generate_variants_from_corpus(
    corpus_paths: Iterable[Path],
    unihan_path: Path,
    output_path: Path,
    top_n: int = 500,
    top_k: int = 100,
    prefer_simplified: bool = True,
) -> Dict[str, str]:
    text = _iter_texts(corpus_paths)
    freqs = character_frequencies(text)
    candidates = select_candidate_chars(freqs, top_n)
    variant_candidates = [c for c in candidates if _is_variant_like(c)]
    review_pool = variant_candidates or candidates

    unihan_variants = load_unihan_variants(unihan_path)
    mapping = build_variant_map(review_pool, unihan_variants, prefer_simplified=prefer_simplified)

    limited = dict(list(mapping.items())[:top_k])
    write_variants_tsv(limited, output_path)
    return limited


def _command_split_bands(args: argparse.Namespace) -> None:
    bands = split_fixed_bands(
        Path(args.image),
        Path(args.output_dir),
        ratios=(args.head_ratio, args.body_ratio, args.foot_ratio),
        prefix=args.prefix,
    )
    print(json.dumps({"head": str(bands.head), "body": str(bands.body), "foot": str(bands.foot)}))


def _command_score_tsv(args: argparse.Namespace) -> None:
    result = score_tsv(Path(args.tsv))
    print(json.dumps(result, ensure_ascii=False))


def _command_generate_variants(args: argparse.Namespace) -> None:
    mapping = generate_variants_from_corpus(
        [Path(p) for p in args.corpus],
        Path(args.unihan),
        Path(args.output),
        top_n=args.top_n,
        top_k=args.top_k,
        prefer_simplified=not args.prefer_traditional,
    )
    print(json.dumps({"count": len(mapping), "output": args.output}, ensure_ascii=False))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fixed-rule OCR utilities")
    sub = parser.add_subparsers(dest="command", required=True)

    split_parser = sub.add_parser("split-bands", help="Split image into fixed header/body/footer bands")
    split_parser.add_argument("--image", required=True)
    split_parser.add_argument("--output-dir", required=True)
    split_parser.add_argument("--prefix")
    split_parser.add_argument("--head-ratio", type=float, default=0.12)
    split_parser.add_argument("--body-ratio", type=float, default=0.78)
    split_parser.add_argument("--foot-ratio", type=float, default=0.10)
    split_parser.set_defaults(func=_command_split_bands)

    score_parser = sub.add_parser("score-tsv", help="Score OCR TSV output")
    score_parser.add_argument("--tsv", required=True)
    score_parser.set_defaults(func=_command_score_tsv)

    variants_parser = sub.add_parser("generate-variants", help="Generate variant mapping from corpus")
    variants_parser.add_argument("--corpus", nargs="+", required=True)
    variants_parser.add_argument("--unihan", required=True)
    variants_parser.add_argument("--output", required=True)
    variants_parser.add_argument("--top-n", type=int, default=500)
    variants_parser.add_argument("--top-k", type=int, default=100)
    variants_parser.add_argument("--prefer-traditional", action="store_true")
    variants_parser.set_defaults(func=_command_generate_variants)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
