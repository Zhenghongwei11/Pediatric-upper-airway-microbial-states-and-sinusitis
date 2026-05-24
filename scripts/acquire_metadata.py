#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import sys
import urllib.request
from pathlib import Path
from typing import Dict, Iterable, List


ROOT = Path(__file__).resolve().parents[1]
METADATA_DIR = ROOT / "data" / "raw" / "metadata"
SUMMARY_PATH = ROOT / "results" / "dataset_summary.tsv"
MANIFEST_PATH = ROOT / "data" / "manifest.tsv"


DATASET_ENDPOINTS = {
    "PRJEB35160": {
        "provider": "ENA",
        "url": (
            "https://www.ebi.ac.uk/ena/portal/api/filereport"
            "?accession=PRJEB35160"
            "&result=read_run"
            "&fields=run_accession,sample_accession,study_accession,instrument_platform,"
            "instrument_model,library_strategy,library_source,library_layout,read_count,"
            "base_count,fastq_ftp,first_public"
            "&format=tsv&download=true"
        ),
    },
    "PRJNA275918": {
        "provider": "NCBI",
        "url": "https://trace.ncbi.nlm.nih.gov/Traces/sra-db-be/runinfo?acc=PRJNA275918",
    },
    "PRJNA554533": {
        "provider": "NCBI",
        "url": "https://trace.ncbi.nlm.nih.gov/Traces/sra-db-be/runinfo?acc=PRJNA554533",
    },
    "PRJNA422760": {
        "provider": "NCBI",
        "url": "https://trace.ncbi.nlm.nih.gov/Traces/sra-db-be/runinfo?acc=PRJNA422760",
    },
    "PRJEB88727": {
        "provider": "ENA",
        "url": (
            "https://www.ebi.ac.uk/ena/portal/api/filereport"
            "?accession=PRJEB88727"
            "&result=read_run"
            "&fields=run_accession,sample_accession,study_accession,instrument_platform,"
            "instrument_model,library_strategy,library_source,library_layout,read_count,"
            "base_count,fastq_ftp,first_public"
            "&format=tsv&download=true"
        ),
    },
    "PRJNA1413967": {
        "provider": "NCBI",
        "url": "https://trace.ncbi.nlm.nih.gov/Traces/sra-db-be/runinfo?acc=PRJNA1413967",
    },
    "PRJNA1049442": {
        "provider": "NCBI",
        "url": "https://trace.ncbi.nlm.nih.gov/Traces/sra-db-be/runinfo?acc=PRJNA1049442",
    },
}


def fetch_text(url: str, timeout: int) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "sihai2-research-pipeline/0.1"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def read_tsv(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def delimiter_for(text: str, provider: str) -> str:
    if provider == "ENA":
        return "\t"
    first_line = text.splitlines()[0] if text.splitlines() else ""
    return "\t" if "\t" in first_line and "," not in first_line else ","


def parse_rows(text: str, provider: str) -> List[Dict[str, str]]:
    delimiter = delimiter_for(text, provider)
    return list(csv.DictReader(text.splitlines(), delimiter=delimiter))


def field_values(rows: Iterable[Dict[str, str]], *fields: str) -> List[str]:
    values = []
    for row in rows:
        for field in fields:
            value = row.get(field)
            if value:
                values.append(value)
                break
    return values


def summarize_dataset(
    dataset_id: str,
    manifest_row: Dict[str, str],
    provider: str,
    metadata_path: Path,
    rows: List[Dict[str, str]],
) -> Dict[str, str]:
    run_values = field_values(rows, "run_accession", "Run")
    sample_values = field_values(rows, "sample_accession", "Sample", "BioSample")
    platform_values = field_values(rows, "instrument_platform", "Platform")
    model_values = field_values(rows, "instrument_model", "Model")
    strategy_values = field_values(rows, "library_strategy", "LibraryStrategy")
    source_values = field_values(rows, "library_source", "LibrarySource")

    return {
        "dataset_id": dataset_id,
        "role": manifest_row.get("role", "unknown"),
        "provider": provider,
        "n_runs": str(len(set(run_values))),
        "n_samples": str(len(set(sample_values))),
        "published_independent_n": manifest_row.get("sample_size_independent", ""),
        "published_profile_n": manifest_row.get("sample_size_profiles", ""),
        "platform": ";".join(sorted(set(platform_values))) if platform_values else "not_available",
        "instrument_model": ";".join(sorted(set(model_values))) if model_values else "not_available",
        "library_strategy": ";".join(sorted(set(strategy_values))) if strategy_values else "not_available",
        "library_source": ";".join(sorted(set(source_values))) if source_values else "not_available",
        "metadata_path": str(metadata_path.relative_to(ROOT)),
        "raw_fastq_downloaded": "no",
        "status": "metadata_fetched" if rows else "empty_or_failed",
    }


def write_tsv(path: Path, rows: List[Dict[str, str]], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch public dataset run metadata without downloading raw FASTQ files.")
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--dataset", action="append", choices=sorted(DATASET_ENDPOINTS), help="Limit to one or more datasets.")
    args = parser.parse_args()

    manifest = {row["dataset_id"]: row for row in read_tsv(MANIFEST_PATH)}
    selected = args.dataset or list(DATASET_ENDPOINTS)
    summaries: List[Dict[str, str]] = []

    for dataset_id in selected:
        endpoint = DATASET_ENDPOINTS[dataset_id]
        metadata_path = METADATA_DIR / f"{dataset_id}_run_metadata.tsv"
        print(f"Fetching {dataset_id} metadata from {endpoint['provider']}...", file=sys.stderr)
        text = fetch_text(endpoint["url"], timeout=args.timeout)
        rows = parse_rows(text, endpoint["provider"])

        if endpoint["provider"] == "ENA":
            write_text(metadata_path, text)
        else:
            write_tsv(metadata_path, rows, list(rows[0].keys()) if rows else [])

        summaries.append(summarize_dataset(dataset_id, manifest.get(dataset_id, {}), endpoint["provider"], metadata_path, rows))

    fieldnames = [
        "dataset_id",
        "role",
        "provider",
        "n_runs",
        "n_samples",
        "published_independent_n",
        "published_profile_n",
        "platform",
        "instrument_model",
        "library_strategy",
        "library_source",
        "metadata_path",
        "raw_fastq_downloaded",
        "status",
    ]
    existing = []
    if SUMMARY_PATH.exists() and args.dataset:
        existing = [row for row in read_tsv(SUMMARY_PATH) if row.get("dataset_id") not in selected]
    write_tsv(SUMMARY_PATH, existing + summaries, fieldnames)
    print(f"Wrote {SUMMARY_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
