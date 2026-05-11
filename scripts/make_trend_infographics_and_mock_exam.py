from __future__ import annotations

import csv
import html
import json
import math
import re
import subprocess
import time
import urllib.parse
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "五年考題_JCP_JOP_趨勢資訊圖表與模擬考"
OUT.mkdir(exist_ok=True)
EXAM_TEXT_DIR = ROOT / "牙周病專科歷屆試題_近五年" / "extracted_text"
JOP_JSON = ROOT / "Journal_of_Periodontology_2023-2026_考試整合" / "JOP_2023-2026_pubmed_records.json"
TODAY = "2026-05-10"

PUBMED_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
JOURNALS = {
    "JCP": "Journal of Clinical Periodontology",
    "JOP": "Journal of Periodontology",
}

TOPICS = {
    "分類/治療指引": [
        "stage", "grade", "classification", "s3", "guideline", "consensus", "2017",
        "分類", "分期", "分級", "牙周炎", "治療指引", "臨床指引", "共識",
    ],
    "植體周圍疾病": [
        "peri-implant", "periimplant", "implantitis", "implant mucositis", "spic",
        "implant", "植體", "種植", "植牙", "植體周圍", "黏膜炎",
    ],
    "再生/黏膜牙齦手術": [
        "regeneration", "regenerative", "intrabony", "intra-bony", "furcation", "root coverage",
        "gingival recession", "mucogingival", "graft", "membrane", "ridge", "emdogain",
        "enamel matrix", "prf", "connective tissue", "再生", "骨內缺損", "根分叉",
        "根面覆蓋", "牙齦萎縮", "黏膜牙齦", "角化", "游離牙齦", "結締組織",
        "補骨", "骨脊", "gbr", "gtr", "emd", "ctg", "fgg", "caf", "tunnel",
    ],
    "非手術/抗菌輔助": [
        "non-surgical", "nonsurgical", "subgingival", "scaling", "root planing",
        "antibiotic", "antimicrobial", "metronidazole", "amoxicillin", "azithromycin",
        "adjunctive", "srp", "刮除", "牙根整平", "非手術", "抗生素", "抗菌",
        "氯己定", "光動力", "益生菌",
    ],
    "SPT/風險/預後": [
        "supportive periodontal", "maintenance", "recurrence", "risk assessment",
        "prediction", "prognosis", "tooth loss", "functional diagram", "supportive",
        "spt", "spc", "維持", "支持性", "回診", "風險", "預後", "失牙", "復發",
        "supportive periodontal care",
    ],
    "全身疾病/危險因子": [
        "diabetes", "smoking", "cardiovascular", "obesity", "pregnancy", "rheumatoid",
        "metabolic", "systemic", "glycemic", "glp-1", "糖尿", "抽菸", "吸菸",
        "心血管", "肥胖", "懷孕", "類風濕", "全身", "血糖", "代謝",
    ],
    "微生物/宿主反應": [
        "microbiome", "microbial", "dysbiosis", "biomarker", "saliva", "salivary",
        "mmp", "cytokine", "host response", "p. gingivalis", "a. actinomycetemcomitans",
        "菌", "微生物", "生物膜", "菌斑", "唾液", "細胞激素", "宿主", "免疫",
        "發炎", "mmp-8", "pg", "aa",
    ],
    "診斷影像/數位工具": [
        "radiograph", "radiographic", "cbct", "diagnosis", "screening", "digital",
        "artificial intelligence", "deep learning", "machine learning", "ai ",
        "x-ray", "影像", "放射", "診斷", "篩檢", "數位", "人工智慧", "深度學習",
        "機器學習", "cbct", "ai",
    ],
}

COLORS = {
    "分類/治療指引": "#2C7A7B",
    "植體周圍疾病": "#4C6FFF",
    "再生/黏膜牙齦手術": "#D97706",
    "非手術/抗菌輔助": "#059669",
    "SPT/風險/預後": "#7C3AED",
    "全身疾病/危險因子": "#DC2626",
    "微生物/宿主反應": "#0F766E",
    "診斷影像/數位工具": "#475569",
}



def run_curl(url: str) -> str:
    return subprocess.check_output(["curl.exe", "-L", "-sS", url], timeout=120).decode("utf-8")


def pubmed_search(journal: str) -> list[str]:
    query = f'"{journal}"[Journal] AND ("2023/01/01"[Date - Publication] : "2026/05/10"[Date - Publication])'
    params = urllib.parse.urlencode({"db": "pubmed", "term": query, "retmode": "json", "retmax": "10000", "sort": "pub date"})
    data = json.loads(run_curl(f"{PUBMED_BASE}/esearch.fcgi?{params}"))
    return data["esearchresult"]["idlist"]


def txt(article: ET.Element, path: str) -> str:
    node = article.find(path)
    if node is None:
        return ""
    return " ".join("".join(node.itertext()).split())


def parse_pubmed(xml_text: str) -> list[dict]:
    root = ET.fromstring(xml_text)
    rows = []
    for article in root.findall(".//PubmedArticle"):
        pmid = txt(article, ".//MedlineCitation/PMID")
        title = html.unescape(txt(article, ".//ArticleTitle"))
        abstract = html.unescape(" ".join(" ".join("".join(n.itertext()).split()) for n in article.findall(".//Abstract/AbstractText")))
        year = txt(article, ".//JournalIssue/PubDate/Year")
        if not year:
            match = re.search(r"(20\d{2})", txt(article, ".//JournalIssue/PubDate/MedlineDate"))
            year = match.group(1) if match else ""
        doi = ""
        for node in article.findall(".//ArticleIdList/ArticleId"):
            if node.attrib.get("IdType") == "doi":
                doi = "".join(node.itertext()).strip()
                break
        pub_types = [" ".join("".join(n.itertext()).split()) for n in article.findall(".//PublicationTypeList/PublicationType")]
        rows.append({
            "pmid": pmid,
            "year": year,
            "title": title,
            "abstract": abstract,
            "doi": doi,
            "publication_types": pub_types,
            "article_group": "Review" if any("review" in p.lower() or "meta-analysis" in p.lower() for p in pub_types) else ("Original Article" if "Journal Article" in pub_types else "Other"),
            "pubmed_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        })
    return rows


def fetch_pubmed(journal_key: str, journal: str) -> list[dict]:
    if journal_key == "JOP" and JOP_JSON.exists():
        return json.loads(JOP_JSON.read_text(encoding="utf-8"))
    ids = pubmed_search(journal)
    records: list[dict] = []
    for start in range(0, len(ids), 200):
        batch = ids[start:start + 200]
        params = urllib.parse.urlencode({"db": "pubmed", "id": ",".join(batch), "retmode": "xml"})
        records.extend(parse_pubmed(run_curl(f"{PUBMED_BASE}/efetch.fcgi?{params}")))
        time.sleep(0.35)
    (OUT / f"{journal_key}_2023-2026_pubmed_records.json").write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    return records


def classify(text: str) -> list[str]:
    lowered = text.lower()
    hits = [topic for topic, keys in TOPICS.items() if any(k.lower() in lowered for k in keys)]
    return hits or ["其他/基礎題"]


def load_exam_questions() -> list[dict]:
    rows = []
    for path in sorted(EXAM_TEXT_DIR.glob("TAOP_20*.txt")):
        year = re.search(r"TAOP_(20\d{2})", path.name).group(1)
        text = path.read_text(encoding="utf-8", errors="replace")
        matches = [m for m in re.finditer(r"(?m)^[ \t\f]*(\d{1,3})[\.、]\s*", text) if 1 <= int(m.group(1)) <= 100]
        seen = set()
        for idx, match in enumerate(matches):
            number = int(match.group(1))
            if number in seen:
                continue
            seen.add(number)
            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
            body = " ".join(text[match.start():end].split())
            rows.append({"year": year, "number": number, "text": body, "topics": classify(body)})
    return rows


def add_topics(records: list[dict]) -> list[dict]:
    for record in records:
        record["topics"] = classify(f"{record.get('title', '')} {record.get('abstract', '')}")
    return records


def count_topics(items: list[dict]) -> Counter:
    c = Counter()
    for item in items:
        for topic in item["topics"]:
            c[topic] += 1
    return c


def count_year_topics(items: list[dict]) -> dict[str, Counter]:
    out = defaultdict(Counter)
    for item in items:
        year = item.get("year", "")
        for topic in item["topics"]:
            out[year][topic] += 1
    return out


def esc(s: str) -> str:
    return html.escape(str(s), quote=False)


def bar_chart(title: str, subtitle: str, data: list[tuple[str, int]], width=1100, height=760) -> str:
    left, top = 330, 130
    bar_h, gap = 42, 20
    max_v = max(v for _, v in data) or 1
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">']
    svg.append('<rect width="100%" height="100%" fill="#FAFAF7"/>')
    svg.append(f'<text x="60" y="66" font-size="34" font-family="Microsoft JhengHei, Arial" font-weight="700" fill="#1F2937">{esc(title)}</text>')
    svg.append(f'<text x="60" y="100" font-size="17" font-family="Microsoft JhengHei, Arial" fill="#475569">{esc(subtitle)}</text>')
    for i, (topic, value) in enumerate(data):
        y = top + i * (bar_h + gap)
        color = COLORS.get(topic, "#64748B")
        length = int((width - left - 130) * value / max_v)
        svg.append(f'<text x="60" y="{y+27}" font-size="20" font-family="Microsoft JhengHei, Arial" fill="#111827">{esc(topic)}</text>')
        svg.append(f'<rect x="{left}" y="{y}" width="{length}" height="{bar_h}" rx="6" fill="{color}"/>')
        svg.append(f'<text x="{left+length+16}" y="{y+28}" font-size="20" font-family="Arial" fill="#111827">{value}</text>')
    svg.append(f'<text x="60" y="{height-40}" font-size="14" font-family="Microsoft JhengHei, Arial" fill="#64748B">整理日期：{TODAY}；題目可多重分類，文獻依 PubMed metadata 與題名/摘要關鍵詞分類。</text>')
    svg.append("</svg>")
    return "\n".join(svg)


def grouped_chart(title: str, subtitle: str, labels: list[str], series: dict[str, list[int]], width=1200, height=780) -> str:
    left, top, bottom = 130, 140, 110
    chart_w, chart_h = width - left - 80, height - top - bottom
    max_v = max(max(vals) for vals in series.values()) or 1
    colors = {"JCP": "#0F766E", "JOP": "#4C6FFF", "考題": "#D97706"}
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">']
    svg.append('<rect width="100%" height="100%" fill="#FBFBF8"/>')
    svg.append(f'<text x="60" y="66" font-size="34" font-family="Microsoft JhengHei, Arial" font-weight="700" fill="#1F2937">{esc(title)}</text>')
    svg.append(f'<text x="60" y="100" font-size="17" font-family="Microsoft JhengHei, Arial" fill="#475569">{esc(subtitle)}</text>')
    for g, color in colors.items():
        x = 700 + list(colors).index(g) * 135
        svg.append(f'<rect x="{x}" y="58" width="20" height="20" fill="{color}" rx="4"/>')
        svg.append(f'<text x="{x+28}" y="75" font-size="16" font-family="Microsoft JhengHei, Arial">{g}</text>')
    for i in range(5):
        val = round(max_v * i / 4)
        y = top + chart_h - chart_h * i / 4
        svg.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left+chart_w}" y2="{y:.1f}" stroke="#E5E7EB"/>')
        svg.append(f'<text x="72" y="{y+5:.1f}" font-size="14" font-family="Arial" fill="#64748B">{val}</text>')
    cluster_w = chart_w / len(labels)
    bar_w = min(34, cluster_w / 5)
    for idx, label in enumerate(labels):
        cx = left + idx * cluster_w + cluster_w / 2
        for sidx, (name, vals) in enumerate(series.items()):
            val = vals[idx]
            h = chart_h * val / max_v
            x = cx - bar_w * 1.7 + sidx * (bar_w + 5)
            y = top + chart_h - h
            svg.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h:.1f}" fill="{colors[name]}" rx="5"/>')
            if val:
                svg.append(f'<text x="{x+bar_w/2:.1f}" y="{y-7:.1f}" font-size="12" text-anchor="middle" font-family="Arial" fill="#111827">{val}</text>')
        svg.append(f'<text x="{cx}" y="{height-62}" font-size="15" text-anchor="middle" font-family="Microsoft JhengHei, Arial" fill="#111827">{esc(label)}</text>')
    svg.append(f'<text x="60" y="{height-30}" font-size="14" font-family="Microsoft JhengHei, Arial" fill="#64748B">整理日期：{TODAY}；JCP/JOP 為 PubMed 2023-01-01 至 2026-05-10。</text>')
    svg.append("</svg>")
    return "\n".join(svg)


def heatmap(title: str, subtitle: str, years: list[str], topics: list[str], data: dict[str, Counter], width=1250, height=820) -> str:
    left, top = 250, 150
    cell_w, cell_h = 110, 48
    max_v = max((data[y][t] for y in years for t in topics), default=1) or 1
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">']
    svg.append('<rect width="100%" height="100%" fill="#FAFAF7"/>')
    svg.append(f'<text x="60" y="66" font-size="34" font-family="Microsoft JhengHei, Arial" font-weight="700" fill="#1F2937">{esc(title)}</text>')
    svg.append(f'<text x="60" y="100" font-size="17" font-family="Microsoft JhengHei, Arial" fill="#475569">{esc(subtitle)}</text>')
    for j, year in enumerate(years):
        svg.append(f'<text x="{left+j*cell_w+cell_w/2}" y="{top-20}" font-size="18" text-anchor="middle" font-family="Arial" fill="#111827">{year}</text>')
    for i, topic in enumerate(topics):
        y = top + i * cell_h
        svg.append(f'<text x="60" y="{y+31}" font-size="18" font-family="Microsoft JhengHei, Arial" fill="#111827">{esc(topic)}</text>')
        for j, year in enumerate(years):
            v = data[year][topic]
            alpha = 0.15 + 0.75 * v / max_v
            x = left + j * cell_w
            svg.append(f'<rect x="{x}" y="{y}" width="{cell_w-8}" height="{cell_h-8}" rx="6" fill="#0F766E" opacity="{alpha:.2f}"/>')
            svg.append(f'<text x="{x+(cell_w-8)/2}" y="{y+27}" font-size="16" text-anchor="middle" font-family="Arial" fill="#111827">{v}</text>')
    svg.append(f'<text x="60" y="{height-40}" font-size="14" font-family="Microsoft JhengHei, Arial" fill="#64748B">顏色越深代表該年度主題命中越多；同一題/文獻可多重分類。</text>')
    svg.append("</svg>")
    return "\n".join(svg)


def save_svg(name: str, content: str) -> Path:
    path = OUT / name
    path.write_text(content, encoding="utf-8")
    return path


def convert_png(svg_path: Path) -> Path | None:
    png_path = svg_path.with_suffix(".png")
    for cmd in (["magick", str(svg_path), str(png_path)], ["rsvg-convert", "-o", str(png_path), str(svg_path)]):
        try:
            subprocess.check_call(cmd, timeout=60, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return png_path
        except Exception:
            pass
    return None




def write_mock_exam(exam_counter: Counter, jcp_counter: Counter, jop_counter: Counter) -> None:
    questions = [
        ("一位進入 maintenance phase 的牙周病患者，BOP 9%，有 6 個 PPD >5 mm 的牙周囊袋，4 顆牙齒喪失，BL/age=0.75，糖尿病且不抽菸。依 periodontal risk assessment，最可能屬於哪一級？", ["Low risk", "Medium risk", "High risk", "無法判斷，因缺少 radiographic bone level"], "C", "多處殘餘深囊袋、糖尿病與既往失牙會把風險推高；此類題型常考 functional diagram 與 SPT interval。"),
        ("Stage IV periodontitis 與 Stage III 最關鍵的差異是什麼？", ["CAL 最大值", "是否有功能性或解剖性複雜度，例如 <20 顆牙、咬合崩解或咀嚼功能障礙", "是否有 BOP", "是否需要 scaling"], "B", "Stage IV 不只是 severe periodontitis，而是合併 rehabilitation complexity。"),
        ("完成 Step 2 subgingival instrumentation 後，仍有 7 mm residual pocket 且 BOP(+)，下一步最合理的是？", ["直接一年後回診", "重做 Step 1 風險控制並評估 Step 3 手術/再生治療", "所有病人例行給抗生素", "改做美白治療"], "B", "EFP S3 強調 stepwise therapy；殘餘深囊袋需評估 access flap、resective 或 regenerative therapy。"),
        ("關於 adjunctive systemic antibiotics，下列何者正確？", ["所有慢性牙周炎都應使用", "通常不作為常規治療，只在特定嚴重或快速進展病例審慎使用", "可取代 mechanical debridement", "不需考慮 antimicrobial stewardship"], "B", "近年文獻與指引均強調選擇性使用與抗生素管理。"),
        ("Peri-implant mucositis 與 peri-implantitis 的核心鑑別是？", ["是否出血", "是否有進行性 supporting bone loss", "植體品牌", "是否在上顎"], "B", "兩者都可有 BOP；peri-implantitis 需有支持骨進行性喪失。"),
        ("Peri-implantitis 較強的風險指標包括哪一組？", ["良好 plaque control、regular SPIC", "severe periodontitis history、poor plaque control、no regular SPIC", "年齡小於 30 歲", "只和植體長度有關"], "B", "歷屆題與 JCP/JOP 都反覆出現 periodontitis history、plaque control 與 supportive care。"),
        ("讀到一篇 root coverage 的 RCT 時，最應優先判讀的是？", ["作者國籍", "recession type、complete root coverage、keratinized tissue gain、patient-reported outcome 與追蹤時間", "期刊封面顏色", "是否使用彩色圖片"], "B", "再生/黏膜牙齦手術是歷屆題高頻主題，考點常在適應症與 outcome selection。"),
        ("Class II furcation defect 的再生治療判斷，最重要的臨床因素是？", ["缺損形態與可清潔性", "病人星座", "只看牙齒顏色", "只看年齡"], "A", "furcation 題目常考 defect morphology、access for hygiene、prognosis 與是否可再生。"),
        ("系統性疾病與牙周炎的文獻判讀，下列何者最完整？", ["只背相關性", "區分 association、risk factor、bi-directional relationship 與 confounding，並連到臨床風險控制", "只背 p value", "一律給抗生素"], "B", "JCP/JOP 近年都有 systemic condition、diabetes、obesity、GLP-1 等主題。"),
        ("關於糖尿病患者的牙周治療計畫，下列何者最合理？", ["不需要問 HbA1c", "需納入 glycemic control、感染控制、SPT 與跨科溝通", "只做植牙", "只給漱口水"], "B", "糖尿病是高頻危險因子，常與治療反應、預後和支持性治療連動。"),
        ("AI 或 prediction model 題目中，AUC 很高時仍需注意什麼？", ["不需看其他指標", "PPV/NPV、盛行率、校正、外部驗證、臨床決策門檻", "模型名稱越新越好", "可直接取代 full-mouth charting"], "B", "2024-2026 題目已出現 AI/prognosis 題型；重點是 evidence appraisal。"),
        ("若文獻使用 CBCT deep learning 偵測 bone loss/furcation，臨床上最保守的解讀是？", ["可直接取代臨床檢查", "可作為輔助工具，但需看 validation、影像品質、族群與誤判風險", "不需 radiographic interpretation", "一定能診斷所有牙周病"], "B", "數位診斷是趨勢，但專科考試會要求知道限制。"),
        ("Systematic review / meta-analysis 在答題時最應補充哪一點？", ["只說結論支持或不支持", "異質性、納入研究品質、endpoint、追蹤時間與 effect size", "只背作者姓名", "忽略臨床可用性"], "B", "Review 是考題引用文獻時的常見題型，不能只背摘要結論。"),
        ("SPT interval 應如何決定？", ["固定每 12 個月", "依 plaque control、BOP、PPD、失牙、risk factor、compliance 個別化", "只看病人方便", "只看保險給付"], "B", "SPT/SPC 與風險評估雖題數不最高，但常是病例題的決策核心。"),
        ("Periodontal regeneration 的 case selection，下列何者較適合？", ["深而窄的 intrabony defect 且 plaque control 可接受", "無法清潔且持續重度發炎", "垂直與水平骨缺損不需區分", "只要病人要求就做"], "A", "再生治療考點在 defect morphology、patient factor、flap/material choice 與 maintenance。"),
        ("對於 microbiome/biomarker 文獻，最符合考試的答法是？", ["可取代 probing 與 radiograph", "可作為風險或疾病活動輔助資訊，但仍需整合臨床與影像", "只要 aMMP-8 陽性就拔牙", "不用考慮 sensitivity/specificity"], "B", "JCP/JOP 近年微生物與宿主反應文獻很多，但臨床轉譯需保守。"),
        ("病人抽菸且 plaque control 差，欲進行 root coverage 手術，最應先做什麼？", ["直接手術", "風險溝通、戒菸/減菸、plaque control 與 realistic outcome expectation", "只增加縫線", "改用任何材料即可抵銷風險"], "B", "危險因子控制是所有手術與再生題的共同底層邏輯。"),
        ("Peri-implantitis 治療後 recurrence 的題目，最應連到哪一個概念？", ["一次手術永久治癒", "SPIC、清潔可及性、prosthetic contour、risk control 與持續監測", "不用追蹤 radiograph", "只看植體廠牌"], "B", "JOP 近期有 peri-implantitis recurrence 與 prosthetic/radiographic 相關主題。"),
        ("若考題引用一篇 cohort study 指出 periodontitis 與某 systemic outcome 相關，最合理的結論是？", ["可直接證明因果", "支持相關性與假說，仍需注意 confounding 與研究設計限制", "完全無意義", "等同 RCT"], "B", "文獻判讀題會考 study design 與因果推論。"),
        ("面對整合性病例題，最穩定的答題順序是？", ["材料先行", "診斷分類、risk/prognosis、病因控制、分階段治療、reevaluation、SPT", "只寫手術名稱", "先決定植體數量"], "B", "這是把歷屆題與文獻趨勢合併後最穩的答題模板。"),
    ]
    md = [
        "# 牙周病專科醫師模擬考題",
        "",
        f"整理日期：{TODAY}",
        "",
        "題型依 2022-2026 TAOP 官方筆試趨勢，並交叉 Journal of Clinical Periodontology 與 Journal of Periodontology 2023-2026 文獻主題製作。",
        "",
        "## 選擇題",
        "",
    ]
    for i, (stem, choices, answer, explanation) in enumerate(questions, 1):
        md.append(f"### 第 {i} 題")
        md.append(stem)
        for letter, choice in zip("ABCD", choices):
            md.append(f"({letter}) {choice}")
        md.append(f"答案：{answer}")
        md.append(f"解析：{explanation}")
        md.append("")
    md += [
        "## 口試/申論題",
        "",
        "1. 請用 Stage/Grade、risk factor、prognosis、治療 phase、SPT interval 五段式，分析一位糖尿病且有多顆殘餘深囊袋的 Stage IV periodontitis 病例。",
        "2. 比較 peri-implant mucositis 與 peri-implantitis 的診斷、危險指標、治療目標與 SPIC 設計。",
        "3. 選一篇 JCP 或 JOP systematic review，說明它對台灣專科考試臨床決策的幫助與限制。",
        "4. 若考題引用 AI 或 prediction model，請說明你會如何評估 AUC、PPV/NPV、外部驗證、臨床決策門檻與倫理限制。",
        "5. 請設計一位 Stage III Grade C 病人的完整治療計畫，並說明何時可考慮 adjunctive antibiotics。",
        "",
        "## 建議練習方式",
        "",
        "- 第一輪：先遮住答案，20 題限時 30 分鐘完成。",
        "- 第二輪：把錯題回填到分類/治療指引、植體周圍疾病、再生/黏膜牙齦手術、SPT/風險四個主軸。",
        "- 第三輪：每題用 2-3 句口試式答案重述，避免只會選選項。",
    ]
    (OUT / "05_牙周病專科醫師_模擬考題20題含解析.md").write_text("\n".join(md), encoding="utf-8")


def write_summary(exam_counter: Counter, jcp_counter: Counter, jop_counter: Counter, records: dict[str, list[dict]], exam_questions: list[dict]) -> None:
    with (OUT / "00_資訊圖表與模擬考總覽.md").open("w", encoding="utf-8") as f:
        f.write(f"# 五年考題、JCP/JOP 文獻趨勢資訊圖表與模擬考\n\n整理日期：{TODAY}\n\n")
        f.write("## 資料範圍\n\n")
        f.write(f"- TAOP 官方筆試題：2022-2026，共 {len(exam_questions)} 題。\n")
        for key, rows in records.items():
            review = sum(1 for r in rows if r.get("article_group") == "Review")
            original = sum(1 for r in rows if r.get("article_group") == "Original Article")
            f.write(f"- {key}：2023-01-01 至 2026-05-10 PubMed metadata，共 {len(rows)} 筆；Review {review} 筆，Original Article {original} 筆。\n")
        f.write("\n## 主要輸出\n\n")
        for name in [
            "01_過去五年TAOP考題主題趨勢.svg",
            "02_JCP_JOP文獻主題趨勢比較.svg",
            "03_考題_JCP_JOP交叉熱點.svg",
            "04_年度主題熱圖_考題.svg",
            "05_牙周病專科醫師_模擬考題20題含解析.md",
            "index.html",
        ]:
            f.write(f"- `{name}`\n")
        f.write("\n## 讀圖重點\n\n")
        f.write("- 考題高頻主軸集中在再生/黏膜牙齦手術、分類/治療指引、植體周圍疾病與 SPT/風險判讀。\n")
        f.write("- JCP 與 JOP 的近年文獻都偏向 systemic risk、microbiome/host response、regeneration、digital diagnosis 與 peri-implant disease。\n")
        f.write("- 模擬題應優先練病例整合：診斷分類、risk/prognosis、分階段治療、文獻判讀、SPT/SPIC。\n")


def write_html(svg_names: list[str]) -> None:
    imgs = "\n".join(f'<section><h2>{esc(Path(name).stem)}</h2><img src="{esc(name)}" alt="{esc(name)}"></section>' for name in svg_names)
    html_text = f"""<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<title>牙周病專科考試趨勢資訊圖表</title>
<style>
body {{ margin: 0; background: #f5f5f1; color: #1f2937; font-family: "Microsoft JhengHei", Arial, sans-serif; }}
main {{ max-width: 1240px; margin: 0 auto; padding: 32px 24px; }}
h1 {{ font-size: 32px; margin: 0 0 8px; }}
p {{ color: #475569; }}
section {{ margin: 28px 0 44px; }}
img {{ width: 100%; height: auto; border: 1px solid #e5e7eb; background: white; }}
a {{ color: #2563eb; }}
</style>
</head>
<body>
<main>
<h1>牙周病專科考試趨勢資訊圖表</h1>
<p>整理日期：{TODAY}。資料包含 2022-2026 TAOP 官方考題，以及 JCP/JOP 2023-2026 PubMed metadata。</p>
<p><a href="05_牙周病專科醫師_模擬考題20題含解析.md">開啟模擬考題 20 題含解析</a></p>
{imgs}
</main>
</body>
</html>"""
    (OUT / "index.html").write_text(html_text, encoding="utf-8")


def main() -> None:
    exam_questions = load_exam_questions()
    records = {key: add_topics(fetch_pubmed(key, journal)) for key, journal in JOURNALS.items()}
    exam_counter = count_topics(exam_questions)
    jcp_counter = count_topics(records["JCP"])
    jop_counter = count_topics(records["JOP"])

    ordered_topics = [t for t in TOPICS if t in exam_counter or t in jcp_counter or t in jop_counter]
    exam_top = [(t, exam_counter[t]) for t in ordered_topics]
    exam_top.sort(key=lambda x: x[1], reverse=True)
    jcp_top = [(t, jcp_counter[t]) for t in ordered_topics]
    jcp_top.sort(key=lambda x: x[1], reverse=True)
    jop_top = [(t, jop_counter[t]) for t in ordered_topics]
    jop_top.sort(key=lambda x: x[1], reverse=True)

    svg_paths = []
    svg_paths.append(save_svg("01_過去五年TAOP考題主題趨勢.svg", bar_chart("過去五年 TAOP 筆試考題主題趨勢", "2022-2026 官方筆試題，共 500 題；同一題可多重分類。", exam_top[:8])))
    svg_paths.append(save_svg("02_JCP_JOP文獻主題趨勢比較.svg", grouped_chart("JCP 與 JOP 近年文獻主題趨勢", "PubMed metadata，2023-01-01 至 2026-05-10。", ordered_topics, {"JCP": [jcp_counter[t] for t in ordered_topics], "JOP": [jop_counter[t] for t in ordered_topics]})))
    svg_paths.append(save_svg("03_考題_JCP_JOP交叉熱點.svg", grouped_chart("考題 x JCP x JOP 交叉熱點", "用來決定模擬考與讀書優先順序。", ordered_topics, {"考題": [exam_counter[t] for t in ordered_topics], "JCP": [jcp_counter[t] for t in ordered_topics], "JOP": [jop_counter[t] for t in ordered_topics]})))
    exam_year_topics = count_year_topics(exam_questions)
    svg_paths.append(save_svg("04_年度主題熱圖_考題.svg", heatmap("2022-2026 官方考題年度主題熱圖", "每年 100 題；顏色越深代表命中越多。", sorted(exam_year_topics), ordered_topics, exam_year_topics)))

    pngs = [convert_png(p) for p in svg_paths]
    write_mock_exam(exam_counter, jcp_counter, jop_counter)
    write_summary(exam_counter, jcp_counter, jop_counter, records, exam_questions)
    write_html([p.name for p in svg_paths])

    with (OUT / "topic_counts.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["topic", "exam_2022_2026", "JCP_2023_2026", "JOP_2023_2026"])
        for topic in ordered_topics:
            writer.writerow([topic, exam_counter[topic], jcp_counter[topic], jop_counter[topic]])
    print(json.dumps({
        "out": str(OUT),
        "exam_questions": len(exam_questions),
        "jcp_records": len(records["JCP"]),
        "jop_records": len(records["JOP"]),
        "png_created": sum(1 for p in pngs if p),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
