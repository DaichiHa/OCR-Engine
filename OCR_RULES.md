# OCR運用ルール（固定設定）

このドキュメントは、日本語OCRの「固定ルール」をまとめたものです。日々の運用でのブレを防ぎ、精度低下や事故を減らすことを目的とします。

## 1) 縦書き：最適PSMの固定

- **縦書き本文は `--psm 5` を固定**します（縦に整列したブロック前提）。
- `jpn` と `jpn_vert` を**同時指定しない**でください。縦が横として読まれやすく失敗報告があります。

推奨コマンド（試写の基準）:

```bash
tesseract in.tif out -l jpn_vert --oem 1 --psm 5 -c preserve_interword_spaces=1
```

例外（固定の分岐だけ持つ）:

- 余白注記・バラ文字: `--psm 11`（疎なテキスト用）
- 表や複雑レイアウト: **ページを切り出してから** `--psm 6`（ブロック）へ

## 2) 旧字体辞書／異体字：扱い方（矛盾回避）

- **原文は絶対に潰さない**方針を取ります。別カラムで“検索用正規化”を保持します。

正規化の考え方:

- `text_raw`: OCRそのまま（一次）
- `text_nfc`: Unicode **NFC**のみ（安全寄り）
- `text_norm`: 独自ルールで字形寄せ（検索・集計用）

実務ルール:

- 集計は `text_norm`、引用は `text_raw`
- 変換表 `variants.tsv（旧→新）` を版管理（MAJOR更新）

## 3) 画像前処理：最小セット（やり過ぎ防止）

**最小セットは (A) 傾き補正 (B) グレースケール (C) 弱い階調正規化**のみです。

ImageMagick最小（効きやすい順）:

```bash
magick in.tif -colorspace Gray -deskew 40% -auto-level -sharpen 0x1 out.tif
```

コントラスト不足だけ追加（必要時のみ）:

```bash
magick in.tif -colorspace Gray -deskew 40% -contrast-stretch 1%x1% out.tif
```

禁止寄り:

- 二値化ゴリ押し（細い筆画が死ぬ）
- 強いノイズ除去（字が溶ける）

---

## DoD（Definition of Done）

- 縦書きは `jpn_vert + psm5` で固定し、例外は2つだけ
- `raw/nfc/norm` の3層をDB列で分離
- 前処理は3手以内（deskew + gray + 軽補正）

## 抜けTop3

- 画像の「切り出し」ルール（表・見出し・注記の分離）
- OCR結果の品質スコア（TSVのconf平均など）
- 異体字変換表の初期セット（頻出100字）

## 代替＋トレードオフ

- 全自動PSM: 手間↓／縦書きで事故↑
- 強前処理: 見かけ改善↑／誤読↑

