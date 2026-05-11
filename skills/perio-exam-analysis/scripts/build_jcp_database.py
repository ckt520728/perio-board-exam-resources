# -*- coding: utf-8 -*-
import csv
import json
import os
import re
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict


BASE = os.path.join(os.getcwd(), "JCP_2022-2025_database")
RAW = os.path.join(BASE, "raw_pubmed2")
QUERY = '"Journal of Clinical Periodontology"[Journal] AND ("2022"[Date - Publication] : "2025"[Date - Publication])'


def text_of(node):
    return "".join(node.itertext()).strip() if node is not None else ""


def classify(title, abstract, mesh, publication_types):
    text = (title + " " + abstract + " " + " ".join(mesh)).lower()
    tags = []

    def add(tag, words):
        if any(word in text for word in words):
            tags.append(tag)

    add("診斷/分類", ["classification", "diagnosis", "stage", "grade", "case definition", "periodontal health"])
    add("非手術治療", ["non-surgical", "nonsurgical", "scaling", "root planing", "subgingival instrumentation", "mechanical therapy", "debridement"])
    add("手術治療", ["surgical", "flap", "surgery", "implantoplasty"])
    add("再生治療", ["regeneration", "regenerative", "intrabony", "intra-bony", "bone graft", "membrane", "enamel matrix", "ridge preservation"])
    add("植體周圍", ["peri-implant", "implant", "periimplantitis", "peri-implantitis", "mucositis"])
    add("系統疾病", ["diabetes", "cardiovascular", "systemic", "pregnancy", "obesity", "smoking", "metabolic", "arthritis", "hypertension"])
    add("微生物", ["microbiota", "microbiome", "bacteria", "microbial", "porphyromonas", "tannerella", "treponema", "aggregatibacter", "dysbiosis"])
    add("實證醫學", ["systematic review", "meta-analysis", "clinical practice guideline", "guideline", "consensus", "review"])
    add("SPT", ["supportive", "maintenance", "recall", "long-term care"])
    add("藥理學", ["antibiotic", "antimicrobial", "amoxicillin", "metronidazole", "doxycycline", "chlorhexidine", "probiotic", "statin"])
    if not tags:
        tags = ["其他/基礎或流病"]
    tags = list(dict.fromkeys(tags))

    if "Randomized Controlled Trial" in publication_types:
        study = "RCT"
    elif "Systematic Review" in publication_types or "Meta-Analysis" in publication_types:
        study = "系統性回顧"
    elif any("Guideline" in item or "Practice Guideline" in item for item in publication_types):
        study = "臨床指引"
    elif "Review" in publication_types:
        study = "敘述性回顧"
    elif "Case Reports" in publication_types:
        study = "病例報告"
    elif "Clinical Trial" in publication_types:
        study = "臨床試驗"
    elif "Observational Study" in publication_types:
        study = "觀察性研究"
    else:
        study = "原始研究/其他"

    weights = {
        "診斷/分類": 3,
        "非手術治療": 3,
        "手術治療": 2,
        "再生治療": 2,
        "植體周圍": 3,
        "系統疾病": 2,
        "微生物": 2,
        "實證醫學": 2,
        "SPT": 3,
        "藥理學": 2,
    }
    score = sum(weights.get(tag, 1) for tag in tags)
    if study in ["臨床指引", "系統性回顧", "RCT"]:
        score += 3
    importance = "★★★" if score >= 7 else "★★" if score >= 4 else "★"
    return study, tags, importance


def parse_records():
    articles = []
    for filename in sorted(name for name in os.listdir(RAW) if name.startswith("efetch_") and name.endswith(".xml")):
        root = ET.parse(os.path.join(RAW, filename)).getroot()
        for pubmed_article in root.findall(".//PubmedArticle"):
            medline = pubmed_article.find("MedlineCitation")
            article = medline.find("Article")
            journal = article.find("Journal")
            pubdate = journal.find("JournalIssue/PubDate") if journal is not None else None
            year = ""
            if pubdate is not None:
                year = pubdate.findtext("Year") or (pubdate.findtext("MedlineDate", "")[:4] if pubdate.findtext("MedlineDate") else "")

            abstract_parts = []
            for abstract_text in article.findall("Abstract/AbstractText"):
                label = abstract_text.attrib.get("Label")
                value = text_of(abstract_text)
                if value:
                    abstract_parts.append((label + ": " if label else "") + value)
            abstract = "\n".join(abstract_parts)

            authors = []
            for author in article.findall("AuthorList/Author")[:8]:
                last = author.findtext("LastName") or ""
                fore = author.findtext("ForeName") or ""
                collective = author.findtext("CollectiveName") or ""
                name = (fore + " " + last).strip() or collective
                if name:
                    authors.append(name)

            doi = ""
            for article_id in pubmed_article.findall("PubmedData/ArticleIdList/ArticleId"):
                if article_id.attrib.get("IdType") == "doi":
                    doi = article_id.text or ""

            publication_types = [item.text for item in article.findall("PublicationTypeList/PublicationType") if item.text]
            mesh = [item.findtext("DescriptorName") for item in medline.findall("MeshHeadingList/MeshHeading") if item.findtext("DescriptorName")]
            title = text_of(article.find("ArticleTitle"))
            if year not in {"2022", "2023", "2024", "2025"}:
                continue

            study, tags, importance = classify(title, abstract, mesh, publication_types)
            pmid = medline.findtext("PMID", "")

            articles.append(
                {
                    "PMID": pmid,
                    "Year": year,
                    "Title": title,
                    "Authors": "; ".join(authors),
                    "Journal": "Journal of Clinical Periodontology",
                    "Volume": journal.findtext("JournalIssue/Volume", "") if journal is not None else "",
                    "Issue": journal.findtext("JournalIssue/Issue", "") if journal is not None else "",
                    "Pages": article.findtext("Pagination/MedlinePgn", ""),
                    "DOI": doi,
                    "PublicationTypes": "|".join(publication_types),
                    "StudyType": study,
                    "Tags": "|".join(tags),
                    "Importance": importance,
                    "Abstract": abstract,
                    "PubMedURL": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    "DOIURL": f"https://doi.org/{doi}" if doi else "",
                }
            )
    articles.sort(key=lambda item: (item["Year"], item["Title"]), reverse=True)
    return articles


def write_outputs(articles):
    with open(os.path.join(BASE, "JCP_2022-2025_pubmed_records.json"), "w", encoding="utf-8") as handle:
        json.dump({"query": QUERY, "count": len(articles), "records": articles}, handle, ensure_ascii=False, indent=2)

    with open(os.path.join(BASE, "JCP_2022-2025_文獻總表.csv"), "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(articles[0].keys()))
        writer.writeheader()
        writer.writerows(articles)

    counts_year = Counter(item["Year"] for item in articles)
    counts_study = Counter(item["StudyType"] for item in articles)
    counts_tag = Counter(tag for item in articles for tag in item["Tags"].split("|"))
    by_tag = defaultdict(list)
    for item in articles:
        for tag in item["Tags"].split("|"):
            by_tag[tag].append(item)

    summary = [
        "# JCP 2022-2025 文獻資料庫總覽\n",
        "資料擷取日：2026-05-05",
        "資料來源：PubMed E-utilities",
        f"查詢式：`{QUERY}`",
        f"總筆數：{len(articles)}\n",
        "## 年度分布",
    ]
    for year, count in sorted(counts_year.items()):
        summary.append(f"- {year}：{count} 篇")
    summary.append("\n## 研究類型分布")
    for study, count in counts_study.most_common():
        summary.append(f"- {study}：{count} 篇")
    summary.append("\n## 考試主題分布")
    for tag, count in counts_tag.most_common():
        summary.append(f"- {tag}：{count} 篇")
    summary.append("\n## 各主題高優先閱讀清單")
    priority_tags = ["診斷/分類", "非手術治療", "手術治療", "再生治療", "植體周圍", "系統疾病", "微生物", "實證醫學", "SPT", "藥理學"]
    for tag in priority_tags:
        selected = sorted(by_tag.get(tag, []), key=lambda item: ({"★★★": 3, "★★": 2, "★": 1}[item["Importance"]], item["Year"]), reverse=True)[:15]
        if not selected:
            continue
        summary.append(f"\n### {tag}")
        for item in selected:
            summary.append(f"- {item['Year']}｜{item['Importance']}｜{item['StudyType']}｜{item['Title']}｜PMID {item['PMID']}｜DOI {item['DOI']}")
    with open(os.path.join(BASE, "00_JCP_2022-2025_文獻資料庫總覽.md"), "w", encoding="utf-8") as handle:
        handle.write("\n".join(summary))

    lines = [
        "# JCP 2022-2025 全文獻摘要索引\n",
        "說明：以下為 PubMed 可取得之 Journal of Clinical Periodontology 2022-2025 紀錄。摘要以公開 PubMed abstract 為依據；無摘要者僅列書目與標籤。\n",
    ]
    for item in articles:
        abstract = re.sub(r"\s+", " ", item["Abstract"]).strip()
        if len(abstract) > 520:
            abstract = abstract[:517] + "..."
        lines.append(f"## {item['Year']}｜{item['Title']}")
        lines.append(f"- PMID/DOI：[{item['PMID']}]({item['PubMedURL']})；{item['DOI']}")
        lines.append(f"- 類型/標籤：{item['StudyType']}；{item['Tags']}；重要度 {item['Importance']}")
        if abstract:
            lines.append(f"- 摘要重點：{abstract}")
        lines.append("")
    with open(os.path.join(BASE, "01_JCP_2022-2025_全文獻摘要索引.md"), "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))

    return counts_year, counts_study, counts_tag


if __name__ == "__main__":
    records = parse_records()
    year_counts, study_counts, tag_counts = write_outputs(records)
    print(json.dumps({
        "base": BASE,
        "count": len(records),
        "year": dict(year_counts),
        "study": dict(study_counts),
        "tags": dict(tag_counts),
    }, ensure_ascii=False))
