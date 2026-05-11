# -*- coding: utf-8 -*-
import html
import json
import math
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "infographics"
OUT.mkdir(exist_ok=True)


def load_data():
    taop = (OUT / "TAOP_2023_exam_text.txt").read_text(encoding="utf-8", errors="ignore")
    abp = (OUT / "ABP_candidate_guide_text.txt").read_text(encoding="utf-8", errors="ignore")
    abp += "\n" + (OUT / "ABP_oral_protocol_text.txt").read_text(encoding="utf-8", errors="ignore")
    records = json.loads((ROOT / "JCP_2022-2025_pubmed_records.json").read_text(encoding="utf-8"))["records"]
    return taop, abp, records


def split_questions(text):
    starts = [(m.start(), int(m.group(1))) for m in re.finditer(r"(?m)^\s*(\d{1,3})\.\s", text)]
    blocks = []
    for idx, (start, number) in enumerate(starts):
        end = starts[idx + 1][0] if idx + 1 < len(starts) else len(text)
        blocks.append((number, text[start:end]))
    return blocks


EXAM_CATS = {
    "植體周圍/植牙": ["植體", "植牙", "implant", "peri-implant", "上顎竇", "sinus", "GBR", "abutment", "membrane"],
    "分類/診斷/預後": ["分類", "Stage", "Grade", "骨喪失", "bone loss", "risk factor", "prognosis", "預後", "AAP", "EFP"],
    "非手術/藥物": ["抗生素", "amoxicillin", "metronidazole", "azithromycin", "instrumentation", "非手術", "SRP", "chlorhexidine"],
    "手術/再生/膜齦": ["翻瓣", "再生", "移植", "游離", "MIST", "牙齦", "根覆蓋", "intrabony", "furcation", "enamel matrix"],
    "SPT/維護": ["維護", "supportive", "recall", "maintenance", "SPT", "回診"],
    "基礎/微生物/免疫": ["細菌", "microbi", "Porphyromonas", "Tannerella", "免疫", "發炎", "cytokine", "histology", "osteoblast"],
    "系統疾病/風險": ["糖尿病", "抽菸", "smoking", "diabetes", "心血管", "pregnancy", "systemic"],
    "實證/統計/文獻": ["系統性", "meta", "review", "RCT", "random", "統計", "evidence"],
}

JCP_ORDER = ["系統疾病", "診斷/分類", "植體周圍", "手術治療", "實證醫學", "微生物", "再生治療", "非手術治療", "SPT", "藥理學"]


def count_exam_categories(questions):
    counts = {key: 0 for key in EXAM_CATS}
    primary = {key: 0 for key in EXAM_CATS}
    for _, block in questions:
        block_lower = block.lower()
        hits = []
        for cat, keys in EXAM_CATS.items():
            score = sum(block_lower.count(k.lower()) for k in keys)
            if score:
                counts[cat] += 1
                hits.append((score, cat))
        if hits:
            hits.sort(reverse=True)
            primary[hits[0][1]] += 1
    return counts, primary


def count_abp_categories(text):
    lower = text.lower()
    return {cat: sum(lower.count(k.lower()) for k in keys) for cat, keys in EXAM_CATS.items()}


def count_jcp(records):
    tags = {}
    studies = {}
    years = {}
    for record in records:
        years[record["Year"]] = years.get(record["Year"], 0) + 1
        studies[record["StudyType"]] = studies.get(record["StudyType"], 0) + 1
        for tag in record["Tags"].split("|"):
            tags[tag] = tags.get(tag, 0) + 1
    return tags, studies, years


def esc(text):
    return html.escape(str(text), quote=False)


def wrap(text, width):
    # Simple width model: CJK chars are wider than Latin chars.
    lines, current, used = [], "", 0
    for ch in text:
        w = 2 if ord(ch) > 127 else 1
        if used + w > width and current:
            lines.append(current)
            current, used = ch, w
        else:
            current += ch
            used += w
    if current:
        lines.append(current)
    return lines


def text_block(lines, x, y, size=30, color="#263238", weight=500, line_height=1.35):
    out = []
    for idx, line in enumerate(lines):
        out.append(f'<text x="{x}" y="{y + idx * size * line_height:.0f}" font-size="{size}" fill="{color}" font-weight="{weight}">{esc(line)}</text>')
    return "\n".join(out)


def bar_chart(items, x, y, width, row_h, color="#0b7fab", max_value=None, label_w=250, value_suffix=""):
    max_value = max_value or max(v for _, v in items)
    out = []
    for i, (label, value) in enumerate(items):
        yy = y + i * row_h
        bar_w = 1 if max_value == 0 else width * value / max_value
        out.append(f'<text x="{x}" y="{yy + 28}" font-size="25" fill="#263238">{esc(label)}</text>')
        out.append(f'<rect x="{x + label_w}" y="{yy + 5}" width="{width}" height="28" rx="5" fill="#e8eef1"/>')
        out.append(f'<rect x="{x + label_w}" y="{yy + 5}" width="{bar_w:.1f}" height="28" rx="5" fill="{color}"/>')
        out.append(f'<text x="{x + label_w + width + 24}" y="{yy + 28}" font-size="24" fill="#263238" font-weight="700">{value}{value_suffix}</text>')
    return "\n".join(out)


def pill(x, y, text, fill="#e7f3f2", stroke="#97c9c5", color="#174846", w=None):
    w = w or (len(text) * 24 + 34)
    return f'<rect x="{x}" y="{y}" width="{w}" height="48" rx="24" fill="{fill}" stroke="{stroke}" stroke-width="2"/><text x="{x + 20}" y="{y + 32}" font-size="24" fill="{color}" font-weight="700">{esc(text)}</text>'


def svg_frame(title, subtitle, body, height=2100):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="{height}" viewBox="0 0 1600 {height}">
<defs>
  <style>
    text {{ font-family: "Noto Sans TC", "Microsoft JhengHei", Arial, sans-serif; }}
    .small {{ font-size: 22px; fill: #607078; }}
  </style>
</defs>
<rect width="1600" height="{height}" fill="#fbfcfb"/>
<rect x="0" y="0" width="1600" height="18" fill="#0b7fab"/>
<text x="80" y="92" font-size="48" fill="#102a43" font-weight="800">{esc(title)}</text>
<text x="82" y="136" font-size="25" fill="#546a76">{esc(subtitle)}</text>
{body}
<text x="80" y="{height - 58}" class="small">資料來源：TAOP 2023 公開筆試題、ABP 官方指南/口試範例、PubMed JCP 2022-2025 614 篇摘要索引。付費全文未逐篇納入。</text>
</svg>'''


def infographic_1(question_count, exam_counts, abp_counts, jcp_tags):
    exam_items = sorted(exam_counts.items(), key=lambda item: item[1], reverse=True)
    jcp_items = [(tag, jcp_tags.get(tag, 0)) for tag in JCP_ORDER]
    body = []
    body.append('<text x="80" y="220" font-size="34" fill="#0f3d4a" font-weight="800">歷屆題型訊號</text>')
    body.append(f'<text x="80" y="265" font-size="26" fill="#263238">臺灣公開題本：2023 年 100 題；ABP 為國外官方參考。</text>')
    body.append(bar_chart(exam_items, 90, 310, 430, 56, color="#2a9d8f", label_w=245))
    body.append('<text x="820" y="220" font-size="34" fill="#0f3d4a" font-weight="800">JCP 2022-2025 文獻熱區</text>')
    body.append(f'<text x="820" y="265" font-size="26" fill="#263238">JCP 紀錄：614 篇；摘要、MeSH 與題名標籤統計。</text>')
    body.append(bar_chart(jcp_items, 830, 310, 430, 50, color="#e76f51", label_w=190))
    y = 845
    body.append('<text x="80" y="850" font-size="34" fill="#0f3d4a" font-weight="800">交集最高的命題帶</text>')
    chips = ["植體周圍炎 + SPT", "Stage/Grade + EFP S3", "抗生素 + 非手術治療", "再生/GBR + 膜齦手術", "微生物/宿主標記 + 診斷"]
    x, yy = 80, 890
    for chip in chips:
        body.append(pill(x, yy, chip, w=len(chip) * 28 + 46))
        x += len(chip) * 28 + 70
        if x > 1320:
            x, yy = 80, yy + 72
    body.append('<text x="80" y="1060" font-size="34" fill="#0f3d4a" font-weight="800">題目寫法特徵</text>')
    points = [
        ("文獻導向", "題幹常直接點名作者、年份、systematic review 或 guideline；不是單純背課本。"),
        ("數字導向", "PPD、BOP、骨喪失、存活率、抗生素劑量、維護間隔與追蹤年限常成為選項差異。"),
        ("臨床決策", "分類後必須連結治療順序：先控感染，再手術/再生/補綴/植牙，最後 SPT。"),
        ("國外取向", "ABP 強調 diagnosis、etiology、prognosis、implants、therapy、evidence-based practice。"),
    ]
    yy = 1110
    for head, desc in points:
        body.append(f'<circle cx="104" cy="{yy-8}" r="9" fill="#0b7fab"/>')
        body.append(f'<text x="126" y="{yy}" font-size="28" fill="#102a43" font-weight="800">{esc(head)}</text>')
        body.append(text_block(wrap(desc, 86), 300, yy, size=25, color="#37474f", weight=500))
        yy += 105
    body.append('<text x="80" y="1545" font-size="34" fill="#0f3d4a" font-weight="800">2026 準備優先順序</text>')
    ladder = [
        ("1", "先掌握指引", "2017 AAP/EFP 分類、EFP S3 Stage I-IV、EFP S3 peri-implant diseases。"),
        ("2", "再背數字", "Stage IV、PD/BOP、SPT/SPIC、抗生素劑量、植體周圍炎治療追蹤。"),
        ("3", "最後練題", "把每題改寫成：診斷、治療、數字、證據強度、陷阱選項。"),
    ]
    yy = 1600
    for num, head, desc in ladder:
        body.append(f'<circle cx="115" cy="{yy}" r="30" fill="#e76f51"/><text x="105" y="{yy+10}" font-size="30" fill="white" font-weight="800">{num}</text>')
        body.append(f'<text x="170" y="{yy-4}" font-size="30" fill="#102a43" font-weight="800">{esc(head)}</text>')
        body.append(text_block(wrap(desc, 76), 170, yy + 38, size=24, color="#455a64"))
        yy += 135
    return svg_frame("JCP 文獻重點 × 歷屆試題分析", "把臺灣題本、ABP 取向與 JCP 文獻熱區合併成考點地圖", "\n".join(body), 2050)


def infographic_2():
    body = []
    body.append('<text x="80" y="230" font-size="34" fill="#0f3d4a" font-weight="800">總策略：用「分類 → 指引 → 數字 → 題目」四層讀法</text>')
    phases = [
        ("第 1 層", "分類定位", "Stage/Grade、peri-implant health/mucositis/peri-implantitis、furcation、缺損型態。", "#2a9d8f"),
        ("第 2 層", "指引流程", "EFP S3 stepwise therapy、Stage IV 跨科 sequencing、peri-implant SPIC。", "#0b7fab"),
        ("第 3 層", "數字記憶", "PPD、BOP、骨喪失、抗生素劑量、維護間隔、追蹤時間與存活率。", "#f4a261"),
        ("第 4 層", "題目轉換", "把 JCP 摘要變成四選一：最正確、錯誤敘述、下一步治療、證據等級。", "#e76f51"),
    ]
    y = 300
    for label, head, desc, color in phases:
        body.append(f'<rect x="90" y="{y}" width="1420" height="150" rx="14" fill="#ffffff" stroke="#d8e2e7" stroke-width="2"/>')
        body.append(f'<rect x="90" y="{y}" width="180" height="150" rx="14" fill="{color}"/>')
        body.append(f'<text x="126" y="{y+88}" font-size="34" fill="white" font-weight="800">{esc(label)}</text>')
        body.append(f'<text x="310" y="{y+58}" font-size="32" fill="#102a43" font-weight="800">{esc(head)}</text>')
        body.append(text_block(wrap(desc, 84), 310, y + 102, size=25, color="#455a64"))
        y += 185
    body.append('<text x="80" y="1055" font-size="34" fill="#0f3d4a" font-weight="800">每週讀書配置</text>')
    schedule = [
        ("40%", "核心指引", "分類、S3、植體周圍指引"),
        ("25%", "JCP 新文獻", "系統性回顧、RCT、診斷/biomarker"),
        ("25%", "歷屆題拆解", "作者年份、數字、陷阱選項"),
        ("10%", "錯題回補", "建立個人弱點清單"),
    ]
    x = 90
    colors = ["#2a9d8f", "#0b7fab", "#f4a261", "#e76f51"]
    for i, (pct, head, desc) in enumerate(schedule):
        body.append(f'<rect x="{x}" y="1110" width="330" height="310" rx="14" fill="#ffffff" stroke="#d8e2e7" stroke-width="2"/>')
        body.append(f'<text x="{x+28}" y="1185" font-size="52" fill="{colors[i]}" font-weight="900">{pct}</text>')
        body.append(f'<text x="{x+28}" y="1240" font-size="31" fill="#102a43" font-weight="800">{esc(head)}</text>')
        body.append(text_block(wrap(desc, 21), x + 28, 1295, size=24, color="#455a64"))
        x += 360
    body.append('<text x="80" y="1535" font-size="34" fill="#0f3d4a" font-weight="800">考場作答流程</text>')
    flow = ["辨認主題", "抓關鍵數字", "排除絕對語氣", "連回指引", "選最臨床合理"]
    x = 95
    for i, step in enumerate(flow):
        body.append(f'<rect x="{x}" y="1600" width="245" height="88" rx="44" fill="#eef6f7" stroke="#9bcbd0" stroke-width="2"/>')
        body.append(f'<text x="{x+35}" y="1655" font-size="28" fill="#0f3d4a" font-weight="800">{esc(step)}</text>')
        if i < len(flow)-1:
            body.append(f'<path d="M{x+255} 1644 L{x+305} 1644" stroke="#607d8b" stroke-width="5"/><path d="M{x+305} 1644 l-16 -12 v24z" fill="#607d8b"/>')
        x += 295
    body.append(text_block(wrap("提醒：臺灣題目喜歡考「根據某篇文獻/系統性回顧，下列何者錯誤」，所以讀文獻時要同步記下反例與限制。", 96), 80, 1810, size=28, color="#37474f", weight=700))
    return svg_frame("應考策略總圖", "把 JCP 文獻轉換成臺灣牙周專科筆試可用的讀書流程", "\n".join(body), 2050)


def infographic_3():
    body = []
    body.append('<text x="80" y="230" font-size="34" fill="#0f3d4a" font-weight="800">目標：從零散記憶變成穩定拿分</text>')
    columns = [
        ("先停損", ["不追冷門材料", "不逐篇全文硬讀", "不背孤立作者名", "不把 adjunct 當萬用答案"]),
        ("必拿分", ["Stage/Grade 判讀", "EFP S3 四步驟", "peri-implantitis 定義", "抗生素與 SPT 數字"]),
        ("練題法", ["每題標主題", "每題寫一句依據", "錯題整理成數字卡", "每週重做一次"]),
    ]
    x = 90
    for title, items in columns:
        body.append(f'<rect x="{x}" y="300" width="440" height="560" rx="16" fill="#ffffff" stroke="#d8e2e7" stroke-width="2"/>')
        body.append(f'<text x="{x+32}" y="365" font-size="34" fill="#102a43" font-weight="900">{esc(title)}</text>')
        y = 430
        for item in items:
            body.append(f'<circle cx="{x+48}" cy="{y-8}" r="8" fill="#2a9d8f"/>')
            body.append(text_block(wrap(item, 22), x + 70, y, size=27, color="#37474f", weight=700))
            y += 92
        x += 500
    body.append('<text x="80" y="990" font-size="34" fill="#0f3d4a" font-weight="800">C → B 的 14 天衝刺表</text>')
    days = [
        ("Day 1-2", "分類", "2017 AAP/EFP、Stage IV 指標、Grade risk。"),
        ("Day 3-4", "S3", "Step 1-4、reevaluation、residual pocket。"),
        ("Day 5-6", "植體", "mucositis vs peri-implantitis、SPIC、risk factors。"),
        ("Day 7-8", "藥物", "Amox/Metro、adjunct 證據、抗藥性限制。"),
        ("Day 9-10", "手術", "intrabony、furcation、GBR、膜齦移植。"),
        ("Day 11-12", "題本", "2023 TAOP 100 題全拆一次。"),
        ("Day 13-14", "整合", "錯題回補、數字默寫、模擬題限時。"),
    ]
    y = 1050
    for idx, (day, topic, desc) in enumerate(days):
        color = "#0b7fab" if idx % 2 == 0 else "#2a9d8f"
        body.append(f'<rect x="95" y="{y}" width="230" height="72" rx="12" fill="{color}"/>')
        body.append(f'<text x="128" y="{y+47}" font-size="27" fill="white" font-weight="900">{esc(day)}</text>')
        body.append(f'<text x="360" y="{y+45}" font-size="30" fill="#102a43" font-weight="900">{esc(topic)}</text>')
        body.append(text_block(wrap(desc, 72), 520, y + 45, size=24, color="#455a64"))
        y += 95
    body.append('<text x="80" y="1800" font-size="34" fill="#0f3d4a" font-weight="800">最低標準</text>')
    body.append(text_block(wrap("能在 30 秒內判斷題目屬於分類、植體、非手術、手術再生、SPT、藥物或實證；能寫出每類 5 個核心數字。", 92), 80, 1850, size=29, color="#37474f", weight=800))
    return svg_frame("C 到 B：穩定及格策略", "用高頻主題與數字卡，把失分從分散變成可控", "\n".join(body), 2050)


def infographic_4():
    body = []
    body.append('<text x="80" y="230" font-size="34" fill="#0f3d4a" font-weight="800">目標：從會答題變成能辨認陷阱與新文獻趨勢</text>')
    body.append('<text x="80" y="300" font-size="30" fill="#102a43" font-weight="900">B → A 的差異不是多背，而是比較與判斷</text>')
    matrix = [
        ("分類", "能判斷 Stage III/IV 邊界", "能說出功能崩壞、治療複雜度與預後差異"),
        ("植體", "會定義 peri-implantitis", "能分辨確定風險與證據尚不一致的 risk indicators"),
        ("治療", "知道 Step 1-4", "能根據 residual pocket/BOP/defect morphology 選下一步"),
        ("文獻", "看得懂結論", "會看 study design、follow-up、heterogeneity、clinical endpoint"),
        ("新興", "聽過 biomarker", "知道它是輔助工具，不能取代 charting/radiograph"),
    ]
    y = 380
    body.append(f'<rect x="90" y="{y}" width="1420" height="62" fill="#102a43" rx="10"/>')
    body.append('<text x="125" y="421" font-size="25" fill="white" font-weight="900">主題</text>')
    body.append('<text x="360" y="421" font-size="25" fill="white" font-weight="900">B 等級答法</text>')
    body.append('<text x="880" y="421" font-size="25" fill="white" font-weight="900">A 等級答法</text>')
    y += 80
    for topic, b, a in matrix:
        body.append(f'<rect x="90" y="{y-42}" width="1420" height="104" fill="#ffffff" stroke="#d8e2e7" stroke-width="2"/>')
        body.append(f'<text x="125" y="{y+18}" font-size="28" fill="#0f3d4a" font-weight="900">{esc(topic)}</text>')
        body.append(text_block(wrap(b, 28), 360, y, size=24, color="#455a64", weight=700))
        body.append(text_block(wrap(a, 45), 880, y, size=24, color="#263238", weight=700))
        y += 120
    body.append('<text x="80" y="1140" font-size="34" fill="#0f3d4a" font-weight="800">A 等級讀文獻模板</text>')
    template = [
        ("PICO", "患者、介入、比較、主要終點"),
        ("數字", "樣本數、追蹤期、PPD/BOP/CAL/MBL、劑量"),
        ("結論", "支持/修正/挑戰哪個指引"),
        ("限制", "異質性、短追蹤、surrogate endpoint、偏差風險"),
        ("出題", "最可能被問的錯誤選項與臨床下一步"),
    ]
    x = 90
    for i, (head, desc) in enumerate(template):
        body.append(f'<rect x="{x}" y="1200" width="270" height="255" rx="14" fill="#ffffff" stroke="#d8e2e7" stroke-width="2"/>')
        body.append(f'<circle cx="{x+52}" cy="1255" r="30" fill="#e76f51"/><text x="{x+42}" y="1265" font-size="28" fill="white" font-weight="900">{i+1}</text>')
        body.append(f'<text x="{x+28}" y="1325" font-size="30" fill="#102a43" font-weight="900">{esc(head)}</text>')
        body.append(text_block(wrap(desc, 18), x+28, 1380, size=23, color="#455a64", weight=700))
        x += 292
    body.append('<text x="80" y="1590" font-size="34" fill="#0f3d4a" font-weight="800">最後 7 天 A 級校準</text>')
    bullets = [
        "每天 30 分鐘讀 2 篇 JCP 高優先摘要，寫成一題四選一。",
        "每天重做 20 題歷屆/模擬題，錯題只追問：考哪個指引、哪個數字、哪個陷阱。",
        "把植體周圍炎、Stage IV、抗生素、SPT、再生治療各整理成一張 A4 心智圖。",
        "練習用 2 句話回答簡答題：第一句下診斷，第二句連結指引與下一步治療。",
    ]
    y = 1645
    for item in bullets:
        body.append(f'<circle cx="104" cy="{y-8}" r="9" fill="#0b7fab"/>')
        body.append(text_block(wrap(item, 88), 130, y, size=27, color="#37474f", weight=700))
        y += 95
    return svg_frame("B 到 A：高分策略", "把文獻證據、臨床限制與陷阱選項整合成判斷力", "\n".join(body), 2050)


def write_html_index(files):
    body = ["<!doctype html><meta charset='utf-8'><title>JCP 牙周專科資訊圖表</title><style>body{font-family:'Microsoft JhengHei',sans-serif;background:#f5f7f8;margin:0;padding:32px}h1{color:#102a43}img{width:100%;max-width:1100px;display:block;margin:24px 0;border:1px solid #d8e2e7;background:white}</style>"]
    body.append("<h1>JCP 2022-2025 × 牙周專科考試資訊圖表</h1>")
    for file in files:
        body.append(f"<h2>{html.escape(file.stem)}</h2><img src='{html.escape(file.name)}'>")
    (OUT / "資訊圖表總覽.html").write_text("\n".join(body), encoding="utf-8")


def main():
    taop, abp, records = load_data()
    questions = split_questions(taop)
    exam_counts, exam_primary = count_exam_categories(questions)
    abp_counts = count_abp_categories(abp)
    jcp_tags, jcp_studies, jcp_years = count_jcp(records)

    analysis = {
        "taop_public_exam_question_count": len(questions),
        "taop_question_category_hits": exam_counts,
        "taop_primary_question_categories": exam_primary,
        "abp_keyword_counts": abp_counts,
        "jcp_tag_counts": jcp_tags,
        "jcp_study_counts": jcp_studies,
        "jcp_year_counts": jcp_years,
    }
    (OUT / "infographic_analysis_counts.json").write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8")

    outputs = [
        ("01_JCP文獻與歷屆試題分析資訊圖表.svg", infographic_1(len(questions), exam_primary, abp_counts, jcp_tags)),
        ("02_應考策略資訊圖表.svg", infographic_2()),
        ("03_C到B策略資訊圖表.svg", infographic_3()),
        ("04_B到A策略資訊圖表.svg", infographic_4()),
    ]
    files = []
    for name, content in outputs:
        path = OUT / name
        path.write_text(content, encoding="utf-8")
        files.append(path)
    write_html_index(files)
    print(json.dumps({"output_dir": str(OUT), "files": [p.name for p in files], "question_count": len(questions)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
