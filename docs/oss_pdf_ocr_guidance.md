# OSSでPDF-OCRを安定運用するための上限と実戦ガイド

## 結論
**OSSでPDF-OCRの「絶対上限」はほぼ無い。限界はPC資源（RAM/SSD/時間）と運用設計。**
でかいPDFは「分割→並列→再結合」で勝てる。

---

## OSSで詰まりやすい限界点

* **RAM不足**：高dpi画像PDF＋500pで食う。落ちる/激遅。
* **I/O**：SSD遅いと待ち地獄。HDDはほぼ無理。
* **画像品質**：傾き/裏写り/小さい文字→OCR精度が頭打ち。
* **縦書き/旧字体**：辞書・学習無しだと誤り増。
* **“一括で1ファイル”思想**：巨大1本を通すと失敗率↑。

---

## 最速で安定するOSS運用（実戦）

### 1) まず「OCR不要」を確認

* PDFにテキスト層があるなら **抽出だけ**で終わる
  * `pdftotext`（Poppler/Xpdf系）でOK

### 2) 巨大PDFは分割して回す（基本）

* 目安：**25〜50ページ/チャンク**
* OSS：`qpdf` or `pdfseparate`（Poppler）

例（qpdf）

```powershell
winget install qpdf.qpdf
qpdf in.pdf --split-pages -- out_%03d.pdf
```

### 3) OCRはチャンク単位で並列

* OSS：OCRmyPDF + Tesseract

```powershell
pip install ocrmypdf
ocrmypdf --language jpn+jpn_vert --rotate-pages --deskew --jobs 4 out_001.pdf ocr_001.pdf
```

* 失敗しても「そのチャンクだけやり直し」＝復旧が早い

### 4) 最後に結合

```powershell
qpdf ocr_*.pdf -- ocr_all.pdf
```

---

## “大容量でも止まらん”ためのコツ

* `--jobs` は **CPUコア数-1** くらい
* 画像が重すぎる場合：**スキャンdpiを落とす**（400→300）
* 旧字体/縦書きは **まず重要ページだけOCR**（10–20%）で燃料化
* 出力は **PDFだけに拘らず**、`sidecar.txt`やページ別TXTにする（後でDBへ）

---

## 結論（君の質問への答え）

* OSSで「PDFがデカいから無理」は **運用の問題**。
* **分割＋並列＋再結合**にした瞬間、限界が実質消える。

---

## DoD×3

* 50p分割→OCR→結合が一発で通る
* 失敗チャンクだけ再実行できる
* 出力からページ番号へ戻れる（manifest）

---

## 抜けTop3

* 縦書き最適psm設定の固定
* 旧字体辞書/異体字の扱い
* 画像前処理（傾き/コントラスト）の最小セット

---

## 代替＋トレードオフ

* 全部1本OCR：手間↓／失敗率↑
* 分割運用：手間↑／安定性↑

---

## 信頼度

高

---

## Go/No-Go

Go（分割運用に切り替えたら勝ち確じゃ）
