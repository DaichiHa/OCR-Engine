# OCR-Engine

## Fixed-rule OCR utilities

`fixed_rules.py` provides three rule-based helpers aligned with the fixed workflow:

1. **Band splitting**: header/body/footer cropping.
2. **OCR quality scoring**: TSV confidence metrics and PASS/WARN/FAIL.
3. **Variant table generation**: corpus frequency + `Unihan_Variants` mapping.

### Example commands

```bash
python fixed_rules.py split-bands --image page.tif --output-dir out
python fixed_rules.py score-tsv --tsv body.tsv
python fixed_rules.py generate-variants --corpus text_raw.txt --unihan Unihan_Variants.txt --output variants.tsv
```

### Optional dependencies

Image-based helpers (`split-bands`, `detect_table_heuristic`) require:

* `opencv-python`
* `numpy`
* `pytesseract`
