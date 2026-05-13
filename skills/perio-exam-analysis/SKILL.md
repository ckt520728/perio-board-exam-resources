---
name: perio-exam-analysis
description: Use when analyzing Taiwan periodontal specialist exam questions, collecting public past papers, reviewing Journal of Clinical Periodontology literature, extracting exam trends, creating Traditional Chinese review notes, simulated questions, study strategy, or infographic outputs for periodontal board preparation.
---

# 牙周病專科考試試題分析技能

Use this skill for tasks like:

- 下載或整理臺灣牙周病專科醫師歷屆試題與官方考試資料。
- 分析臺灣牙周病專科筆試題型、命題趨勢、常考數字與高頻文獻。
- 建立或更新 `Journal of Clinical Periodontology` (JCP) 文獻資料庫。
- 依 2017 AAP/EFP 分類、EFP S3 指引與 JCP 文獻做繁體中文複習整理。
- 產生模擬題、C 到 B / B 到 A 應考策略、資訊圖表或可匯入 Notion 的資料表。

## Core Workflow

1. **定位工作資料夾**
   - 優先使用使用者指定的資料夾。
   - 若資料夾已有 `JCP_2022-2025_database` 或 `牙周病專科歷屆試題_近五年`，沿用既有結構。
   - 不要覆蓋使用者手動加入的題本或筆記。

2. **整理歷屆試題**
   - 優先抓官方、學會、考試機構公開來源。
   - 臺灣來源優先：臺灣牙周病醫學會 TAOP。
   - 國外來源可納入 ABP/EFP/AAP 等官方 guideline、candidate guide 或 sample protocol。
   - 不下載需登入、付費、疑似外流或未授權題庫。
   - 若題本是 PDF，先轉文字，再分析題號、題型、主題與常考作者/年份/數字。

3. **建立 JCP 文獻資料庫**
   - 使用 PubMed 或官方 DOI/Wiley metadata 查詢 JCP 指定年份。
   - 典型查詢式：
     `"Journal of Clinical Periodontology"[Journal] AND ("2022"[Date - Publication] : "2025"[Date - Publication])`
   - 保存原始 metadata、CSV 總表、JSON 結構化檔、逐篇摘要索引。
   - 明確標註：若僅使用 PubMed abstract，不可聲稱已讀全文。

4. **考試導向分類**
   - 主題標籤固定使用：
     `診斷/分類｜非手術治療｜手術治療｜再生治療｜植體周圍｜系統疾病｜微生物｜實證醫學｜SPT｜藥理學`
   - 對每篇或每題標註：
     - 研究類型：RCT / 系統性回顧 / 臨床指引 / 世代研究 / 橫斷面研究 / 病例報告 / 其他。
     - 重要程度：★★★ / ★★ / ★。
     - 考點：分類、治療步驟、數字閾值、臨床下一步、證據限制。

5. **輸出複習資料**
   - 使用繁體中文。
   - 筆記要貼近臺灣牙周專科命題風格：文獻導向、數字導向、臨床決策、錯誤選項辨識。
   - 每篇重點文獻建議輸出：
     - A. 核心知識點萃取
     - B. 數字與閾值記憶點
     - C. 與現行標準的對應
     - D. 2 道模擬題
     - E. Notion 標籤建議

6. **輸出資訊圖表**
   - 建議同時產出 SVG 與 PNG。
   - 最少四張：
     1. JCP 文獻內容重點與歷屆試題分析
     2. 應考策略
     3. C 到 B 策略
     4. B 到 A 策略
   - 圖中必須標明資料來源限制，例如「臺灣公開題本目前僅使用 2023 TAOP 公開題本；會員限定題本未納入」。

## Exam Heuristics

臺灣題本常見命題邏輯：

- 題幹常寫「根據某作者某年研究/系統性回顧，下列何者錯誤」。
- 選項常用數字差異測驗記憶：PPD、BOP、CAL、bone loss、抗生素劑量、維護間隔、追蹤年限、存活率。
- 高頻交集：
  - Stage/Grade + EFP S3
  - peri-implant mucositis/peri-implantitis + SPIC
  - non-surgical therapy + adjunctive antibiotics
  - regeneration/GBR + mucogingival surgery
  - microbiome/host markers + diagnosis
  - systemic disease risk + prognosis

## Key Board-Style Anchors

Keep these anchors available when generating review notes or questions:

- Stage IV periodontitis: severe periodontitis plus functional/anatomical sequelae such as `<20 teeth`, `<10 opposing pairs`, `mobility grade >=2`, masticatory dysfunction, bite collapse, pathologic migration, or severe ridge defect.
- EFP S3 periodontitis therapy: Step 1 behavior/risk/biofilm control; Step 2 subgingival instrumentation; Step 3 residual pocket surgery/regeneration/resective therapy; Step 4 SPT.
- Peri-implant mucositis: inflammation with BOP, without continuing marginal bone loss.
- Peri-implantitis: biofilm-associated inflammation plus progressive supporting bone loss; often BOP/suppuration, increased PD, recession, radiographic bone loss.
- Stronger peri-implantitis risk indicators: history of severe periodontitis, poor plaque control, no regular SPIC.
- Periodontitis adjunctive antibiotics are not routine; use cautiously for selected severe/rapidly progressing cases and mention antimicrobial stewardship.

## Bundled Scripts

Use scripts when the task repeats prior workflow:

- `scripts/build_jcp_database.py`: rebuilds PubMed/JCP metadata outputs from already downloaded PubMed XML batches. Patch it if year range or source folder changes.
- `scripts/build_infographics.py`: builds SVG infographics from extracted exam text and JCP database JSON.

If a script assumes a local path, adjust paths conservatively and keep outputs inside the user-specified workspace.

## Output Conventions

- Use Traditional Chinese for user-facing files.
- Preserve source links and DOI/PMID where available.
- Separate confirmed official past papers from guideline/sample/reference documents.
- State limitations clearly when data are abstract-only, member-only, paywalled, or not true past questions.
- Prefer Markdown, CSV, JSON, SVG, PNG, and HTML overview outputs.
