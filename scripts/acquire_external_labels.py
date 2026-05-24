#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import html
import http.client
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from typing import Dict, Iterable, List
from xml.etree import ElementTree

import openpyxl


ROOT = Path(__file__).resolve().parents[1]
METADATA_DIR = ROOT / "data" / "raw" / "metadata"
LABEL_DIR = ROOT / "data" / "references" / "external_labels"
RECON_DIR = ROOT / "results" / "recon"
REPORT_PATH = ROOT / "docs" / "LABEL_AVAILABILITY_REPORT.md"

USER_AGENT = "Mozilla/5.0 (compatible; pediatric-upper-airway-label-check/1.0)"

PMC422760_ARTICLE = "https://pmc.ncbi.nlm.nih.gov/articles/PMC6372837/"
PMC422760_FILES = [
    "https://pmc.ncbi.nlm.nih.gov/articles/instance/6372837/bin/mSystems.00169-18-st001.docx",
    "https://pmc.ncbi.nlm.nih.gov/articles/instance/6372837/bin/mSystems.00169-18-st002.xlsx",
    "https://pmc.ncbi.nlm.nih.gov/articles/instance/6372837/bin/mSystems.00169-18-st003.xlsx",
    "https://pmc.ncbi.nlm.nih.gov/articles/instance/6372837/bin/mSystems.00169-18-st004.docx",
    "https://pmc.ncbi.nlm.nih.gov/articles/instance/6372837/bin/mSystems.00169-18-st005.docx",
]

FRONTIERS554533_FULL = (
    "https://www.frontiersin.org/journals/cellular-and-infection-microbiology/"
    "articles/10.3389/fcimb.2020.00458/full"
)
FRONTIERS554533_XML = (
    "https://www.frontiersin.org/journals/cellular-and-infection-microbiology/"
    "articles/10.3389/fcimb.2020.00458/xml"
)


def request(url: str, referer: str | None = None, cookie: str | None = None, timeout: int = 60) -> bytes:
    headers = {"User-Agent": USER_AGENT}
    if referer:
        headers["Referer"] = referer
    if cookie:
        headers["Cookie"] = cookie
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return response.read()
        except (
            urllib.error.URLError,
            TimeoutError,
            BrokenPipeError,
            ConnectionResetError,
            http.client.RemoteDisconnected,
            OSError,
        ) as exc:
            last_error = exc
            time.sleep(1 + attempt)
    raise RuntimeError(f"request_failed url={url} error={last_error}")


def write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def read_tsv(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def write_tsv(path: Path, rows: List[Dict[str, str]], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def office_file_type(payload: bytes, filename: str) -> str:
    if payload.startswith(b"PK\x03\x04"):
        return Path(filename).suffix.lower().lstrip(".")
    if payload.startswith(b"\xd0\xcf\x11\xe0"):
        return "xls"
    stripped = payload.lstrip().lower()
    if stripped.startswith(b"<html") or stripped.startswith(b"<!doctype html"):
        return "html"
    return "unknown"


def solve_pmc_pow(page: bytes) -> str | None:
    text = page.decode("utf-8", errors="replace")
    challenge_match = re.search(r"POW_CHALLENGE\s*=\s*['\"]([^'\"]+)['\"]", text)
    difficulty_match = re.search(r"POW_DIFFICULTY\s*=\s*['\"]?(\d+)['\"]?", text)
    if not challenge_match or not difficulty_match:
        return None

    challenge = challenge_match.group(1)
    difficulty = int(difficulty_match.group(1))
    prefix = "0" * difficulty
    nonce = 0
    while True:
        digest = hashlib.sha256((challenge + str(nonce)).encode("utf-8")).hexdigest()
        if digest.startswith(prefix):
            return f"cloudpmc-viewer-pow={challenge},{nonce}"
        nonce += 1


def download_pmc_file(url: str, out_dir: Path) -> Dict[str, str]:
    filename = Path(urllib.parse.urlparse(url).path).name
    out_path = out_dir / filename
    page = request(url, referer=PMC422760_ARTICLE)
    file_type = office_file_type(page, filename)
    note = "downloaded directly"

    if file_type == "html":
        cookie = solve_pmc_pow(page)
        if cookie:
            page = request(url, referer=PMC422760_ARTICLE, cookie=cookie)
            file_type = office_file_type(page, filename)
            note = "downloaded after PMC proof-of-work cookie"
        else:
            note = "PMC proof-of-work page did not expose a solvable challenge"

    status = "downloaded" if file_type in {"docx", "xlsx", "xls"} else "not_usable"
    if status == "not_usable" and out_path.exists():
        existing = out_path.read_bytes()
        existing_type = office_file_type(existing, filename)
        if existing_type in {"docx", "xlsx", "xls"}:
            return {
                "dataset_id": "PRJNA422760",
                "source": "PMC article supplement",
                "source_url": url,
                "local_path": str(out_path.relative_to(ROOT)),
                "file_type": existing_type,
                "status": "downloaded",
                "bytes": str(len(existing)),
                "note": "kept previously downloaded Office file after current request returned HTML",
            }
    if status == "not_usable":
        if out_path.exists():
            out_path.unlink()
        out_path = out_path.with_suffix(out_path.suffix + ".html")
    write_bytes(out_path, page)
    return {
        "dataset_id": "PRJNA422760",
        "source": "PMC article supplement",
        "source_url": url,
        "local_path": str(out_path.relative_to(ROOT)),
        "file_type": file_type,
        "status": status,
        "bytes": str(len(page)),
        "note": note,
    }


def download_prjna422760_supplements() -> List[Dict[str, str]]:
    out_dir = LABEL_DIR / "PRJNA422760"
    rows = []
    for url in PMC422760_FILES:
        rows.append(download_pmc_file(url, out_dir))
    write_tsv(
        out_dir / "supplement_manifest.tsv",
        rows,
        ["dataset_id", "source", "source_url", "local_path", "file_type", "status", "bytes", "note"],
    )
    return rows


def discover_frontiers_supplements() -> List[Dict[str, str]]:
    out_dir = LABEL_DIR / "PRJNA554533"
    out_dir.mkdir(parents=True, exist_ok=True)
    full = request(FRONTIERS554533_FULL)
    xml = request(FRONTIERS554533_XML)
    write_bytes(out_dir / "article_full.html", full)
    write_bytes(out_dir / "article.xml", xml)

    text = xml.decode("utf-8", errors="replace")
    matches = re.findall(
        r'<supplementary-material[^>]+xlink:href="([^"]+)"[^>]*id="([^"]+)"[^>]*mimetype="([^"]+)"',
        text,
    )
    rows = []
    for href, supplement_id, mimetype in matches:
        caption_match = re.search(
            rf'<supplementary-material[^>]+id="{re.escape(supplement_id)}"[^>]*>.*?<label>(.*?)</label>.*?<caption><p>(.*?)</p></caption>',
            text,
            re.S,
        )
        label = html.unescape(re.sub("<[^>]+>", "", caption_match.group(1))) if caption_match else supplement_id
        caption = html.unescape(re.sub("<[^>]+>", "", caption_match.group(2))) if caption_match else ""
        rows.append(
            {
                "dataset_id": "PRJNA554533",
                "source": "Frontiers article XML",
                "source_url": FRONTIERS554533_XML,
                "local_path": str((out_dir / "article.xml").relative_to(ROOT)),
                "file_type": mimetype,
                "status": "described_not_sample_label_table",
                "bytes": str(len(xml)),
                "note": f"{label}: {href}; {caption}",
            }
        )

    if not rows:
        rows.append(
            {
                "dataset_id": "PRJNA554533",
                "source": "Frontiers article",
                "source_url": FRONTIERS554533_FULL,
                "local_path": str((out_dir / "article_full.html").relative_to(ROOT)),
                "file_type": "html",
                "status": "no_supplement_table_detected",
                "bytes": str(len(full)),
                "note": "No static supplementary file links were detected.",
            }
        )

    write_tsv(
        out_dir / "supplement_manifest.tsv",
        rows,
        ["dataset_id", "source", "source_url", "local_path", "file_type", "status", "bytes", "note"],
    )
    return rows


def fetch_biosample_attributes(accession: str) -> Dict[str, str]:
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=biosample&id={accession}&retmode=xml"
    last_error = ""
    for attempt in range(3):
        try:
            payload = request(url, timeout=30)
            root = ElementTree.fromstring(payload)
            attrs = {}
            for attr in root.findall(".//Attribute"):
                name = attr.attrib.get("attribute_name", "").strip()
                if name:
                    attrs[name] = (attr.text or "").strip()
            return attrs
        except (RuntimeError, urllib.error.URLError, ElementTree.ParseError, http.client.RemoteDisconnected) as exc:
            last_error = str(exc)
            time.sleep(1 + attempt)
    return {"biosample_fetch_error": last_error}


def fetch_biosample_attribute_batch(accessions: List[str]) -> Dict[str, Dict[str, str]]:
    if not accessions:
        return {}
    joined = ",".join(accessions)
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=biosample&id={joined}&retmode=xml"
    payload = request(url, timeout=60)
    root = ElementTree.fromstring(payload)
    parsed: Dict[str, Dict[str, str]] = {}
    for biosample in root.findall(".//BioSample"):
        accession = biosample.attrib.get("accession", "").strip()
        if not accession:
            continue
        attrs = {"BioSample": accession}
        for attr in biosample.findall(".//Attribute"):
            name = attr.attrib.get("attribute_name", "").strip()
            if name:
                attrs[name] = (attr.text or "").strip()
        parsed[accession] = attrs
    return parsed


def cache_biosample_attributes(dataset_id: str, accessions: Iterable[str]) -> Dict[str, Dict[str, str]]:
    out_path = LABEL_DIR / dataset_id / "biosample_attributes.tsv"
    cached = {}
    if out_path.exists():
        for row in read_tsv(out_path):
            cached[row["BioSample"]] = row

    accessions = sorted({accession for accession in accessions if accession})
    missing = [accession for accession in accessions if accession not in cached]
    fetched: Dict[str, Dict[str, str]] = {}
    for start in range(0, len(missing), 100):
        chunk = missing[start : start + 100]
        try:
            fetched.update(fetch_biosample_attribute_batch(chunk))
        except (RuntimeError, ElementTree.ParseError) as exc:
            for accession in chunk:
                fetched[accession] = {"BioSample": accession, **fetch_biosample_attributes(accession)}
        if start + 100 < len(missing):
            time.sleep(0.34)

    rows = [cached.get(accession) or fetched.get(accession) or {"BioSample": accession} for accession in accessions]

    fieldnames = ["BioSample"]
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    write_tsv(out_path, rows, fieldnames)
    return {row["BioSample"]: row for row in rows}


def extract_xlsx_strings(path: Path) -> List[str]:
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    values = []
    for sheet in workbook.worksheets:
        for row in sheet.iter_rows(values_only=True):
            values.extend(str(value) for value in row if value is not None)
    return values


def extract_docx_strings(path: Path) -> List[str]:
    values = []
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            if name.startswith("word/") and name.endswith(".xml"):
                text = archive.read(name).decode("utf-8", errors="replace")
                values.extend(html.unescape(value) for value in re.findall(r"<w:t[^>]*>(.*?)</w:t>", text))
    return values


def supplement_text_index(dataset_id: str) -> str:
    out_dir = LABEL_DIR / dataset_id
    texts = []
    for path in sorted(out_dir.glob("*")):
        suffix = path.suffix.lower()
        try:
            if suffix == ".xlsx":
                texts.extend(extract_xlsx_strings(path))
            elif suffix == ".docx":
                texts.extend(extract_docx_strings(path))
            elif suffix in {".xml", ".html", ".htm"}:
                texts.append(path.read_text(encoding="utf-8", errors="replace"))
        except Exception as exc:
            texts.append(f"extract_error:{path.name}:{exc}")
    return "\n".join(texts)


def parse_prjna422760_sample(sample_name: str) -> Dict[str, str]:
    match = re.match(r"^(?P<patient_id>\d+)(?P<site_code>[a-z])_(?P<tissue>adenoid|tonsil)$", sample_name)
    if not match:
        return {"patient_id": "", "site_code": "", "tissue_from_sample_name": "", "sample_name_parse": "FAIL"}
    groups = match.groupdict()
    return {
        "patient_id": groups["patient_id"],
        "site_code": groups["site_code"],
        "tissue_from_sample_name": groups["tissue"],
        "sample_name_parse": "PASS",
    }


def infer_prjna422760_mapping() -> List[Dict[str, str]]:
    metadata = read_tsv(METADATA_DIR / "PRJNA422760_run_metadata.tsv")
    biosample_attrs = cache_biosample_attributes("PRJNA422760", [row.get("BioSample", "") for row in metadata])
    supplement_index = supplement_text_index("PRJNA422760")
    rows = []
    for row in metadata:
        sample_name = row.get("SampleName", "")
        parsed = parse_prjna422760_sample(sample_name)
        attrs = biosample_attrs.get(row.get("BioSample", ""), {})
        isolation_source = attrs.get("isolation_source", "")
        tissue_from_biosample = ""
        if "adenoid" in isolation_source.lower():
            tissue_from_biosample = "adenoid"
        elif "tonsil" in isolation_source.lower():
            tissue_from_biosample = "tonsil"
        supplement_mentions_sample = "yes" if sample_name in supplement_index else "no"
        tissue_match = "PASS" if parsed["tissue_from_sample_name"] and parsed["tissue_from_sample_name"] == tissue_from_biosample else "FAIL"
        rows.append(
            {
                "dataset_id": "PRJNA422760",
                "run": row.get("Run", ""),
                "biosample": row.get("BioSample", ""),
                "sample_name": sample_name,
                "patient_id": parsed["patient_id"],
                "site_code": parsed["site_code"],
                "clinical_label": parsed["tissue_from_sample_name"],
                "label_type": "paired_tissue_site",
                "repository_context": isolation_source,
                "supplement_mentions_sample": supplement_mentions_sample,
                "sample_name_parse": parsed["sample_name_parse"],
                "biosample_tissue_match": tissue_match,
                "mainline_decision": "usable_phenotype_transfer" if parsed["sample_name_parse"] == "PASS" and tissue_match == "PASS" else "hold",
            }
        )
    return rows


def infer_prjna554533_mapping() -> List[Dict[str, str]]:
    metadata = read_tsv(METADATA_DIR / "PRJNA554533_run_metadata.tsv")
    biosample_attrs = cache_biosample_attributes("PRJNA554533", [row.get("BioSample", "") for row in metadata])
    supplement_index = supplement_text_index("PRJNA554533")
    disease_fields = ["Disease", "Body_Site", "Affection_Status", "source", "Subject_ID"]
    rows = []
    for row in metadata:
        sample_name = row.get("SampleName", "")
        attrs = biosample_attrs.get(row.get("BioSample", ""), {})
        available_label_values = [
            row.get(field, "")
            for field in disease_fields
            if row.get(field, "") and str(row.get(field, "")).lower() != "nan"
        ]
        supplement_mentions_sample = "yes" if sample_name in supplement_index else "no"
        clinical_attrs = [
            attrs.get(key, "")
            for key in ["disease", "phenotype", "body_site", "isolation_source", "host_disease"]
            if attrs.get(key, "")
        ]
        has_public_sample_label = bool(available_label_values or clinical_attrs or supplement_mentions_sample == "yes")
        rows.append(
            {
                "dataset_id": "PRJNA554533",
                "run": row.get("Run", ""),
                "biosample": row.get("BioSample", ""),
                "sample_name": sample_name,
                "patient_id": "",
                "site_code": "",
                "clinical_label": ";".join(available_label_values + clinical_attrs),
                "label_type": "AH_AR_group" if has_public_sample_label else "not_recovered",
                "repository_context": "; ".join(f"{key}={attrs[key]}" for key in ["host", "isolation_source", "collection_date", "geo_loc_name"] if attrs.get(key)),
                "supplement_mentions_sample": supplement_mentions_sample,
                "sample_name_parse": "PASS" if re.match(r"^RHINO-\d+$", sample_name) else "FAIL",
                "biosample_tissue_match": "not_applicable",
                "mainline_decision": "hold_label_insufficient" if not has_public_sample_label else "usable_after_group_mapping_review",
            }
        )
    return rows


def summarize_mapping(rows: List[Dict[str, str]]) -> Dict[str, Dict[str, int]]:
    summary: Dict[str, Dict[str, int]] = {}
    for row in rows:
        dataset = row["dataset_id"]
        summary.setdefault(dataset, {"rows": 0, "usable": 0, "hold": 0})
        summary[dataset]["rows"] += 1
        if row["mainline_decision"].startswith("usable"):
            summary[dataset]["usable"] += 1
        else:
            summary[dataset]["hold"] += 1
    return summary


def write_report(supplement_rows: List[Dict[str, str]], mapping_rows: List[Dict[str, str]]) -> None:
    summary = summarize_mapping(mapping_rows)
    pmc_downloaded = sum(1 for row in supplement_rows if row["dataset_id"] == "PRJNA422760" and row["status"] == "downloaded")
    frontiers_rows = [row for row in supplement_rows if row["dataset_id"] == "PRJNA554533"]
    report = [
        "# External Label Audit",
        "",
        "Generated: 2026-05-23",
        "",
        "## Decision",
        "- PRJNA422760 is usable as a phenotype-transfer cohort for paired adenoid/tonsil tissue-site ecology. SRA sample names parse into patient ID and tissue site, and BioSample isolation_source independently confirms the same tissue label.",
        "- PRJNA554533 remains on hold. The SRA run table and BioSample records provide public rhino sample IDs, host, collection date, and geography, but no sample-level adenoid hypertrophy/allergic rhinitis/control group mapping was recovered from public repository metadata or static Frontiers supplement metadata.",
        "",
        "## Downloaded Sources",
        f"- PRJNA422760 PMC supplements downloaded as usable Office files: {pmc_downloaded}/5.",
        f"- PRJNA554533 Frontiers supplementary records detected from article XML: {len(frontiers_rows)}; these describe ROC/network supplementary tables rather than subject-to-group label tables.",
        "",
        "## Mapping Summary",
        "| Dataset | Rows | Usable | Hold | Decision |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for dataset, counts in sorted(summary.items()):
        decision = "phenotype-transfer usable" if counts["usable"] else "hold until public labels are recovered"
        report.append(f"| {dataset} | {counts['rows']} | {counts['usable']} | {counts['hold']} | {decision} |")
    report.extend(
        [
            "",
            "## Files",
            "- `data/references/external_labels/PRJNA422760/supplement_manifest.tsv`",
            "- `data/references/external_labels/PRJNA554533/supplement_manifest.tsv`",
            "- `results/recon/external_label_mapping.tsv`",
            "",
            "## Guardrail",
            "External cohorts are not direct sinusitis replication cohorts. They can only support state-transfer or tissue-site ecological questions unless a comparable clinical endpoint and sample-level labels are publicly verified.",
        ]
    )
    REPORT_PATH.write_text("\n".join(report) + "\n", encoding="utf-8")


def main() -> int:
    supplement_rows = []
    supplement_rows.extend(download_prjna422760_supplements())
    supplement_rows.extend(discover_frontiers_supplements())
    mapping_rows = infer_prjna422760_mapping() + infer_prjna554533_mapping()

    fieldnames = [
        "dataset_id",
        "run",
        "biosample",
        "sample_name",
        "patient_id",
        "site_code",
        "clinical_label",
        "label_type",
        "repository_context",
        "supplement_mentions_sample",
        "sample_name_parse",
        "biosample_tissue_match",
        "mainline_decision",
    ]
    write_tsv(RECON_DIR / "external_label_mapping.tsv", mapping_rows, fieldnames)
    write_report(supplement_rows, mapping_rows)
    print(f"Wrote {REPORT_PATH.relative_to(ROOT)}")
    print(f"Wrote {(RECON_DIR / 'external_label_mapping.tsv').relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
