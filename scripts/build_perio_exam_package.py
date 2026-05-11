from __future__ import annotations

import csv
import html
import json
import re
import subprocess
import time
import urllib.parse
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
EXAM_TEXT_DIR = ROOT / "牙周病專科歷屆試題_近五年" / "extracted_text"
OUT_DIR = ROOT / "Journal_of_Periodontology_2023-2026_考試整合"
OUT_DIR.mkdir(exist_ok=True)

TODAY = "2026-05-10"
PUBMED_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
JOURNAL_QUERY = (
    '"Journal of Periodontology"[Journal] '
    'AND ("2023/01/01"[Date - Publication] : "2026/05/10"[Date - Publication])'
)

CATEGORIES = {
    "分類與治療指引": [
        "stage", "grade", "classification", "s3", "guideline", "consensus",
        "periodontitis stage", "periodontitis grade",
    ],
    "植體周圍疾病": [
        "peri-implant", "periimplant", "implantitis", "implant mucositis",
        "supportive peri-implant",
    ],
    "再生與黏膜牙齦手術": [
        "regeneration", "intrabony", "intra-bony", "furcation", "root coverage",
        "gingival recession", "mucogingival", "graft", "membrane", "ridge",
        "emdogain", "enamel matrix", "prf", "connective tissue",
    ],
    "非手術治療與抗菌輔助": [
        "non-surgical", "nonsurgical", "subgingival", "scaling", "root planing",
        "antibiotic", "antimicrobial", "metronidazole", "amoxicillin",
        "azithromycin", "adjunctive",
    ],
    "SPT/SPC 與風險評估": [
        "supportive periodontal", "maintenance", "recurrence", "risk assessment",
        "prediction", "prognosis", "tooth loss", "machine learning", "artificial intelligence",
    ],
    "全身疾病與危險因子": [
        "diabetes", "smoking", "cardiovascular", "obesity", "pregnancy",
        "rheumatoid", "metabolic", "systemic", "glycemic", "risk factor",
    ],
    "微生物與宿主生物標記": [
        "microbiome", "microbial", "dysbiosis", "biomarker", "saliva",
        "salivary", "mmp", "cytokine", "host response", "p. gingivalis",
    ],
    "診斷影像與數位工具": [
        "radiograph", "cbct", "diagnosis", "screening", "digital", "ai ",
        "artificial intelligence", "deep learning",
    ],
}

QUESTION_TEMPLATES = [
    (
        "一位 Stage III/IV periodontitis 病人完成 Step 2 後仍有多處 PPD >=6 mm 且 BOP(+)，下列哪一項最符合 EFP S3 stepwise therapy 的下一步？",
        ["直接進入每 12 個月一次 SPT", "重新建立 Step 1 風險控制並評估 Step 3 手術/再生適應症", "常規給所有病人 amoxicillin + metronidazole", "停止牙周治療並改以植體重建"],
        "B",
        "殘餘深囊袋與發炎需重新確認 plaque/risk control，並針對缺損型態考慮 access flap、resective 或 regenerative therapy。",
    ),
    (
        "關於 peri-implant mucositis 與 peri-implantitis 的區分，下列何者最重要？",
        ["是否有 BOP", "是否有持續或進行性 supporting bone loss", "是否為後牙區植體", "是否使用 screw-retained prosthesis"],
        "B",
        "兩者都可能有發炎與 BOP；peri-implantitis 的核心是發炎合併進行性支持骨喪失。",
    ),
    (
        "近年 JOP 文獻常見的 AI/prognosis 題型中，最不應忽略的解讀陷阱是什麼？",
        ["AUC 高即可代表 PPV 一定高", "模型需看族群盛行率、校正、外部驗證與臨床可行性", "AI 模型可取代 full-mouth charting", "所有模型均可直接外推到台灣考生病例"],
        "B",
        "考題常測試診斷/預後模型的 evidence appraisal，而非只背演算法名稱。",
    ),
    (
        "對於 periodontitis 的 systemic risk，下列哪一組最適合作為答題架構？",
        ["只列相關性即可", "雙向關係、risk indicator/risk factor 區分、控制因子與治療目標", "只需背 odds ratio", "以抗生素作為所有 systemic-risk 病人的主要處置"],
        "B",
        "糖尿病、抽菸與其他全身疾病常以整合病例題出現，重點是風險控制與證據層級。",
    ),
    (
        "若題目引用 systematic review 或 meta-analysis，下列哪一項最能提升答案品質？",
        ["只引用結論方向", "同時指出研究異質性、surrogate endpoint、追蹤時間與臨床效益大小", "把所有 review 當成最高品質證據", "忽略納入研究設計"],
        "B",
        "近年題目常把 review 與 RCT 交錯考，需能辨識 evidence strength 與臨床轉譯限制。",
    ),
]


def fetch_json(url: str) -> dict:
    raw = subprocess.check_output(["curl.exe", "-L", "-sS", url], timeout=90)
    return json.loads(raw.decode("utf-8"))


def fetch_text(url: str) -> str:
    raw = subprocess.check_output(["curl.exe", "-L", "-sS", url], timeout=120)
    return raw.decode("utf-8")


def pubmed_search() -> list[str]:
    params = urllib.parse.urlencode(
        {
            "db": "pubmed",
            "term": JOURNAL_QUERY,
            "retmode": "json",
            "retmax": "10000",
            "sort": "pub date",
        }
    )
    data = fetch_json(f"{PUBMED_BASE}/esearch.fcgi?{params}")
    return data["esearchresult"]["idlist"]


def article_text(article: ET.Element, path: str) -> str:
    node = article.find(path)
    if node is None:
        return ""
    return " ".join("".join(node.itertext()).split())


def parse_pubmed_records(xml_text: str) -> list[dict]:
    root = ET.fromstring(xml_text)
    records = []
    for article in root.findall(".//PubmedArticle"):
        pmid = article_text(article, ".//MedlineCitation/PMID")
        title = html.unescape(article_text(article, ".//ArticleTitle"))
        abstract_parts = [
            " ".join("".join(node.itertext()).split())
            for node in article.findall(".//Abstract/AbstractText")
        ]
        abstract = html.unescape(" ".join(abstract_parts))
        journal = article_text(article, ".//Journal/Title")
        year = article_text(article, ".//JournalIssue/PubDate/Year")
        if not year:
            medline_date = article_text(article, ".//JournalIssue/PubDate/MedlineDate")
            match = re.search(r"(20\d{2})", medline_date)
            year = match.group(1) if match else ""
        doi = ""
        for node in article.findall(".//ArticleIdList/ArticleId"):
            if node.attrib.get("IdType") == "doi":
                doi = "".join(node.itertext()).strip()
                break
        pub_types = [
            " ".join("".join(node.itertext()).split())
            for node in article.findall(".//PublicationTypeList/PublicationType")
        ]
        combined = f"{title} {abstract}".lower()
        categories = [
            name for name, terms in CATEGORIES.items()
            if any(term.lower() in combined for term in terms)
        ]
        if not categories:
            categories = ["其他牙周臨床/基礎研究"]
        is_review = any("review" in pt.lower() or "meta-analysis" in pt.lower() for pt in pub_types)
        is_original = ("Journal Article" in pub_types) and not is_review
        records.append(
            {
                "pmid": pmid,
                "year": year,
                "journal": journal,
                "title": title,
                "doi": doi,
                "publication_types": pub_types,
                "article_group": "Review" if is_review else ("Original Article" if is_original else "Other"),
                "categories": categories,
                "abstract": abstract,
                "pubmed_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else "",
            }
        )
    return records


def pubmed_fetch(ids: list[str]) -> list[dict]:
    records = []
    for start in range(0, len(ids), 200):
        batch = ids[start:start + 200]
        params = urllib.parse.urlencode(
            {"db": "pubmed", "id": ",".join(batch), "retmode": "xml"}
        )
        xml_text = fetch_text(f"{PUBMED_BASE}/efetch.fcgi?{params}")
        records.extend(parse_pubmed_records(xml_text))
        time.sleep(0.35)
    return records


def load_exam_questions() -> list[dict]:
    rows = []
    for path in sorted(EXAM_TEXT_DIR.glob("TAOP_20*.txt")):
        year_match = re.search(r"TAOP_(20\d{2})", path.name)
        year = year_match.group(1) if year_match else path.stem
        text = path.read_text(encoding="utf-8", errors="replace")
        matches = [
            m for m in re.finditer(r"(?m)^[ \t\f]*(\d{1,3})[\.、]\s*", text)
            if 1 <= int(m.group(1)) <= 100
        ]
        seen_numbers = set()
        for idx, match in enumerate(matches):
            number = int(match.group(1))
            if number in seen_numbers:
                continue
            seen_numbers.add(number)
            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
            chunk = text[match.start():end]
            normalized = " ".join(chunk.split())
            lower = normalized.lower()
            categories = [
                name for name, terms in CATEGORIES.items()
                if any(term.lower() in lower for term in terms)
            ]
            if not categories:
                categories = ["其他/基礎與傳統牙周學"]
            rows.append(
                {
                    "year": year,
                    "number": number,
                    "text": normalized,
                    "categories": categories,
                }
            )
    return rows


def counter_table(counter: Counter) -> str:
    lines = ["| 主題 | 數量 |", "|---|---:|"]
    for name, count in counter.most_common():
        lines.append(f"| {name} | {count} |")
    return "\n".join(lines)


def representative(records: list[dict], category: str, group: str, limit: int = 5) -> list[dict]:
    hits = [
        r for r in records
        if category in r["categories"] and (group == "All" or r["article_group"] == group)
    ]
    hits.sort(key=lambda r: (r["year"], r["pmid"]), reverse=True)
    return hits[:limit]


def write_outputs(records: list[dict], questions: list[dict]) -> None:
    (OUT_DIR / "JOP_2023-2026_pubmed_records.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    with (OUT_DIR / "JOP_2023-2026_文獻總表.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "pmid", "year", "journal", "title", "doi", "article_group",
                "categories", "publication_types", "pubmed_url",
            ],
        )
        writer.writeheader()
        for r in records:
            row = dict(r)
            row["categories"] = "; ".join(r["categories"])
            row["publication_types"] = "; ".join(r["publication_types"])
            row.pop("abstract", None)
            writer.writerow(row)

    exam_counter = Counter(cat for q in questions for cat in q["categories"])
    exam_by_year = defaultdict(Counter)
    exam_question_count_by_year = Counter(q["year"] for q in questions)
    for q in questions:
        for cat in q["categories"]:
            exam_by_year[q["year"]][cat] += 1

    article_counter = Counter(cat for r in records for cat in r["categories"])
    group_counter = Counter(r["article_group"] for r in records)
    year_group = defaultdict(Counter)
    for r in records:
        year_group[r["year"]][r["article_group"]] += 1

    exam_md = [
        "# 近五年 TAOP 牙周病專科筆試題型趨勢",
        "",
        f"整理日期：{TODAY}",
        "",
        "資料來源：臺灣牙周病醫學會會員專區「歷屆筆試考題」，已下載 2022、2023、2024、2025、2026 年官方 PDF。2022 檔案標題未標示解答，其餘年度含試題與解答。",
        "",
        f"抽取題目數：{len(questions)} 題。",
        "",
        "## 主題出現頻率",
        counter_table(exam_counter),
        "",
        "## 年度分布",
        "| 年度 | 題數 | 前三大主題 |",
        "|---|---:|---|",
    ]
    for year in sorted(exam_by_year):
        top = "、".join(f"{k}({v})" for k, v in exam_by_year[year].most_common(3))
        count = exam_question_count_by_year[year]
        exam_md.append(f"| {year} | {count} | {top} |")
    exam_md += [
        "",
        "## 備考判讀",
        "- 題目仍以臨床診斷、Stage/Grade、風險評估、非手術與支持性治療為骨架。",
        "- 2024-2026 題幹明顯常引用近年文獻作者與年份，尤其是 AI/prognosis、植體周圍疾病、再生材料與 donor-site morbidity。",
        "- 答題不只背結論，還要會判斷 study design、endpoint、追蹤時間、族群外推性與臨床可用性。",
    ]
    (OUT_DIR / "01_近五年TAOP歷屆題_題型趨勢.md").write_text("\n".join(exam_md), encoding="utf-8")

    jop_md = [
        "# Journal of Periodontology 近三年文獻趨勢",
        "",
        f"整理日期：{TODAY}",
        "",
        f"PubMed 查詢式：`{JOURNAL_QUERY}`",
        f"收錄筆數：{len(records)}。分類以 PubMed publication type 粗分 Review、Original Article、Other。",
        "",
        "## 文獻類型",
        counter_table(group_counter),
        "",
        "## 年度 x 類型",
        "| 年度 | Review | Original Article | Other |",
        "|---|---:|---:|---:|",
    ]
    for year in sorted(year_group):
        c = year_group[year]
        jop_md.append(f"| {year} | {c['Review']} | {c['Original Article']} | {c['Other']} |")
    jop_md += [
        "",
        "## 主題分布",
        counter_table(article_counter),
        "",
        "## 代表文獻",
    ]
    for cat in CATEGORIES:
        jop_md.append(f"### {cat}")
        reps = representative(records, cat, "All", 6)
        if not reps:
            jop_md.append("- 本批 PubMed metadata 未抓到明確命中。")
        for r in reps:
            doi = f" DOI: {r['doi']}." if r["doi"] else ""
            jop_md.append(f"- {r['year']} [{r['article_group']}] PMID {r['pmid']}: {r['title']}.{doi}")
        jop_md.append("")
    (OUT_DIR / "02_Journal_of_Periodontology_近三年文獻趨勢.md").write_text("\n".join(jop_md), encoding="utf-8")

    overlap = []
    for cat in CATEGORIES:
        overlap.append((cat, exam_counter.get(cat, 0), article_counter.get(cat, 0)))
    overlap.sort(key=lambda x: (x[1] > 0 and x[2] > 0, x[1] + x[2]), reverse=True)

    sim_md = [
        "# 歷屆題 x Journal of Periodontology 趨勢模擬題庫",
        "",
        f"整理日期：{TODAY}",
        "",
        "## 出題優先順序",
        "| 優先 | 主題 | 歷屆題命中 | JOP 文獻命中 | 備考策略 |",
        "|---:|---|---:|---:|---|",
    ]
    for idx, (cat, ecount, acount) in enumerate(overlap[:10], start=1):
        strategy = "高優先：整理成病例題與文獻判讀題" if ecount and acount else "中優先：作為補充或鑑別題"
        sim_md.append(f"| {idx} | {cat} | {ecount} | {acount} | {strategy} |")
    sim_md += ["", "## 模擬選擇題", ""]
    for idx, (stem, choices, answer, rationale) in enumerate(QUESTION_TEMPLATES, start=1):
        sim_md.append(f"### 第 {idx} 題")
        sim_md.append(stem)
        for letter, choice in zip("ABCD", choices):
            sim_md.append(f"({letter}) {choice}")
        sim_md.append(f"答案：{answer}")
        sim_md.append(f"解析：{rationale}")
        sim_md.append("")
    sim_md += [
        "## 模擬申論/口試題",
        "1. 請用 Stage/Grade、risk factor、prognosis、治療 phase、SPT interval 五段式，分析一位糖尿病且有多顆殘餘深囊袋的 Stage IV periodontitis 病例。",
        "2. 比較 peri-implant mucositis 與 peri-implantitis 的診斷、危險指標、治療目標與 SPIC 設計。",
        "3. 選一篇近年 JOP systematic review，說明它對台灣專科考試臨床決策的幫助與限制。",
        "4. 若考題引用 AI 或 prediction model，請說明你會如何評估 AUC、PPV/NPV、外部驗證、臨床決策門檻與倫理限制。",
    ]
    (OUT_DIR / "03_歷屆題xJOP趨勢_模擬題庫.md").write_text("\n".join(sim_md), encoding="utf-8")

    notion_md = [
        "# 考試總覽",
        f"整理日期：{TODAY}",
        "",
        "本頁整合 2022-2026 臺灣牙周病醫學會專科筆試官方題與 2023-2026 Journal of Periodontology PubMed 文獻趨勢。使用時請把它當成讀書地圖，不取代官方試題 PDF 與原始文獻。",
        "",
        "# 必讀主軸",
        "1. 2017 AAP/EFP Stage/Grade：Stage III/IV 區分、Grade B/C、risk modifier、病例整合。",
        "2. EFP S3 stepwise therapy：Step 1 risk/biofilm control、Step 2 subgingival instrumentation、Step 3 residual pocket surgery/regeneration、Step 4 SPT/SPC。",
        "3. Peri-implant diseases：mucositis vs peri-implantitis、progressive bone loss、history of periodontitis、plaque control、SPIC。",
        "4. 文獻判讀：Review vs Original Article、RCT vs cohort、surrogate endpoint、追蹤期、heterogeneity、外部效度。",
        "5. 新興題型：AI/prognosis、biomarkers/microbiome、digital diagnosis、risk prediction。",
        "",
        "# 高命中讀書清單",
        "| 主題 | 為什麼重要 | 準備方式 |",
        "|---|---|---|",
    ]
    for cat, ecount, acount in overlap[:8]:
        notion_md.append(f"| {cat} | 歷屆題 {ecount}、JOP 文獻 {acount} | 做一張病例決策表，並挑 2-3 篇代表文獻讀摘要與方法 |")
    notion_md += [
        "",
        "# 一週衝刺安排",
        "- Day 1：Stage/Grade + EFP S3，完成官方 2022-2026 題目中分類與治療計畫題。",
        "- Day 2：非手術治療、抗菌輔助、SPT/SPC，整理適應症與禁忌。",
        "- Day 3：Peri-implant disease，背診斷定義、危險指標、SPIC 與治療限制。",
        "- Day 4：Regeneration、furcation、mucogingival/root coverage，整理缺損型態與材料選擇。",
        "- Day 5：Systemic risk、diabetes、smoking、host response，練習把 risk control 放入治療計畫。",
        "- Day 6：JOP Review/Original Article 判讀，練習作者年份題與 evidence appraisal。",
        "- Day 7：做模擬題與錯題表，將錯題回填到 Stage/Grade、SPT、implant、regeneration 四大框架。",
        "",
        "# 模擬題入口",
        "請搭配本機檔案 `03_歷屆題xJOP趨勢_模擬題庫.md` 使用；內含選擇題、解析與口試題。",
        "",
        "# 資料來源",
        "- 臺灣牙周病醫學會：會員專區歷屆筆試考題，2022-2026。",
        "- PubMed：Journal of Periodontology，2023-01-01 至 2026-05-10。",
    ]
    (OUT_DIR / "04_牙周病專科考試_Notion筆記.md").write_text("\n".join(notion_md), encoding="utf-8")


def main() -> None:
    ids = pubmed_search()
    records = pubmed_fetch(ids)
    questions = load_exam_questions()
    write_outputs(records, questions)
    print(json.dumps({"pubmed_records": len(records), "exam_questions": len(questions), "output_dir": str(OUT_DIR)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
