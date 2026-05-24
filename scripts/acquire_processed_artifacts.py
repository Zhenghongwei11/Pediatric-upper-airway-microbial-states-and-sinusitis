#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import urllib.request
from pathlib import Path
from typing import Dict, List


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "references" / "sinusitis_microbiome"
MANIFEST_OUT = OUT_DIR / "github_artifacts.tsv"
REPO_API = "https://api.github.com/repos/lynchlab-ucsf/SinusitisMicrobiome/contents"


def fetch_json(url: str) -> List[Dict[str, object]]:
    request = urllib.request.Request(url, headers={"User-Agent": "sihai2-research-pipeline/0.1"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def download(url: str, path: Path, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        return
    request = urllib.request.Request(url, headers={"User-Agent": "sihai2-research-pipeline/0.1"})
    with urllib.request.urlopen(request, timeout=120) as response:
        path.write_bytes(response.read())


def write_manifest(rows: List[Dict[str, str]]) -> None:
    MANIFEST_OUT.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["name", "size_bytes", "download_url", "local_path", "status"]
    with MANIFEST_OUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> int:
    parser = argparse.ArgumentParser(description="Download small processed artifacts from the public SinusitisMicrobiome GitHub repository.")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    contents = fetch_json(REPO_API)
    rows: List[Dict[str, str]] = []
    for item in contents:
        if item.get("type") != "file":
            continue
        url = str(item.get("download_url") or "")
        name = str(item.get("name") or "")
        if not url or not name:
            continue
        path = OUT_DIR / name
        download(url, path, args.overwrite)
        rows.append(
            {
                "name": name,
                "size_bytes": str(item.get("size") or ""),
                "download_url": url,
                "local_path": str(path.relative_to(ROOT)),
                "status": "available" if path.exists() else "missing",
            }
        )

    write_manifest(rows)
    print(f"Wrote {MANIFEST_OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

