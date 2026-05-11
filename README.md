# 牙周病專科考試公開整理專區

本 repo 是牙周病專科醫師考試準備用的公開整理專區，內容包含：

- 2022-2026 TAOP 官方筆試題的主題趨勢分析
- Journal of Clinical Periodontology 與 Journal of Periodontology 近年 PubMed metadata 趨勢分析
- 交叉熱點資訊圖表
- 模擬考題與解析
- 可重跑資料整理流程的腳本
- 本次對話產生的 `perio-exam-analysis` Codex skill

## 重要聲明

本公開版不包含臺灣牙周病醫學會會員限定 PDF，也不包含完整官方試題抽文字。官方試題請依學會規範從會員專區取得。

## 專區導覽

- `analysis/`：Markdown/CSV 趨勢整理與模擬題資料
- `infographics/`：SVG/PNG 資訊圖表與 HTML 總覽
- `mock-exam/`：可直接練習的模擬考題
- `skills/perio-exam-analysis/`：牙周病專科考試分析 skill
- `scripts/`：資料抓取、分類、資訊圖表與模擬題產生腳本

## 資料範圍

- TAOP 官方筆試題：2022-2026，共 500 題，僅保留主題統計與衍生整理。
- Journal of Clinical Periodontology：PubMed 2023-01-01 至 2026-05-10，共 562 筆 metadata。
- Journal of Periodontology：PubMed 2023-01-01 至 2026-05-10，共 494 筆 metadata。

## 主要輸出

- `infographics/index.html`
- `infographics/01_過去五年TAOP考題主題趨勢.png`
- `infographics/02_JCP_JOP文獻主題趨勢比較.png`
- `infographics/03_考題_JCP_JOP交叉熱點.png`
- `infographics/04_年度主題熱圖_考題.png`
- `mock-exam/05_牙周病專科醫師_模擬考題20題含解析.md`

## 使用方式

1. 從 `infographics/index.html` 快速看趨勢圖。
2. 用 `mock-exam/05_牙周病專科醫師_模擬考題20題含解析.md` 進行第一輪練習。
3. 回到 `analysis/topic_counts.csv` 決定下一輪複習優先順序。

## 來源

- 臺灣牙周病醫學會歷屆筆試考題頁：https://www.taop.org.tw/download/index.php?t=11
- PubMed：https://pubmed.ncbi.nlm.nih.gov/
