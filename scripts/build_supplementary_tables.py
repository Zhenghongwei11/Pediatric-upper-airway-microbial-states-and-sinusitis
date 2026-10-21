#!/usr/bin/env python3
"""Build supplementary Tables S1–S7 from the analysis outputs.

The script only formats and joins existing result/source records. It does not
refit models, recalculate estimates, or alter the upstream TSV outputs.
"""

from __future__ import annotations

import csv
import math
import re
from pathlib import Path
from typing import Any, Iterable

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.utils import get_column_letter


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "results/supplementary"
OUTPUT_XLSX = OUTPUT_DIR / "Supplementary_Tables.xlsx"
OUTPUT_MD = OUTPUT_DIR / "Supplementary_Tables.md"

NAVY = "1F4E78"
BLUE = "D9EAF7"
PALE = "F3F6F8"
INK = "1F2933"
MUTED = "52606D"
WHITE = "FFFFFF"
RULE = "B8C7D1"
FONT_NAME = "Arial"

ID_FIELDS = {
    "child_id", "sample_id", "sample_name", "matrix_sample_id", "patient_id",
    "dataset_id", "dataset_id_or_name", "access_link", "omitted_child",
    "genus", "species", "taxon_id", "model", "exposure", "group",
    "outcome_group", "clinical_group", "tissue", "comparison", "analysis",
    "term", "variable", "stage", "flow_stage", "status", "role", "modality",
    "state_key", "state_label", "dominant_genus", "recomputed_genus",
    "StudySubGroup", "healthy_vs_sick", "Visit.Type_Lab", "Surv_Sick_Recov",
    "Sinusitis_Samp", "Date", "exclusion_reason", "covariates", "effect_type",
    "covariance", "weighting", "warnings", "multiplicity_family", "family",
    "interval", "zero_method", "method", "test", "metric", "input",
    "exchangeability_unit", "model", "interpretation", "published_independent_n",
    "population_or_ancestry", "intended_role", "dataset_id_or_name", "provider",
    "platform", "instrument_model", "library_strategy", "library_source",
    "metadata_path", "raw_fastq_downloaded", "clinical_label_full_names",
}


def read_tsv(relative_path: str) -> tuple[list[str], list[dict[str, str]]]:
    path = ROOT / relative_path
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if not reader.fieldnames:
            raise ValueError(f"No header found in {relative_path}")
        return list(reader.fieldnames), list(reader)


def typed(value: Any, field: str = "") -> Any:
    if value is None:
        return None
    if not isinstance(value, str):
        return value
    if value == "":
        return None
    if field in ID_FIELDS:
        return value
    if value in {"NA", "NaN", "nan", "Inf", "-Inf"}:
        return value
    if value in {"True", "TRUE"}:
        return True
    if value in {"False", "FALSE"}:
        return False
    if re.fullmatch(r"[-+]?\d+", value):
        try:
            return int(value)
        except ValueError:
            pass
    if re.fullmatch(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?", value):
        try:
            number = float(value)
            return number if math.isfinite(number) else value
        except ValueError:
            pass
    return value


def set_base_sheet(ws, tab_color: str = NAVY) -> None:
    ws.sheet_view.showGridLines = False
    ws.sheet_properties.tabColor = tab_color
    ws.sheet_view.zoomScale = 90
    ws.sheet_format.defaultRowHeight = 18
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.page_margins.left = 0.25
    ws.page_margins.right = 0.25
    ws.page_margins.top = 0.45
    ws.page_margins.bottom = 0.45


def put_title(ws, title: str, note: str | None = None) -> int:
    ws.cell(1, 1, title)
    ws.cell(1, 1).font = Font(name=FONT_NAME, size=14, bold=True, color=NAVY)
    ws.cell(1, 1).alignment = Alignment(vertical="center")
    ws.row_dimensions[1].height = 25
    if note:
        ws.cell(2, 1, note)
        ws.cell(2, 1).font = Font(name=FONT_NAME, size=9, italic=True, color=MUTED)
        ws.cell(2, 1).alignment = Alignment(vertical="center", wrap_text=False)
        ws.row_dimensions[2].height = 22
    return 4


def number_format(header: str) -> str | None:
    h = header.lower().replace(" ", "_")
    if h in {"threshold_percent", "threshold_(%)"}:
        return "0"
    if any(tag in h for tag in ("pvalue", "p_value", "p_bh", "fdr", "p-value")):
        return "0.0000"
    if any(tag in h for tag in ("percent", "percentage", "percentage points", "median_adenoid", "median_tonsil", "paired_difference", "marginal_medians")):
        return "0.00"
    if any(tag in h for tag in ("fraction", "probability", "fitted_min", "fitted_max", "r2", "_r2", "condition_number", "eigenvalue", "distance", "coefficient", "estimate", "effect", "ci_lower", "ci_upper", "statistic", "constant", "mean_")):
        return "0.000"
    if any(tag in h for tag in ("n_", "_n", "profiles", "children", "samples", "patients", "runs", "permutations", "allocations", "observations", "groups", "_df", "rank", "parameters", "iterations", "successful", "failed", "seed", "changed_profiles", "datasets", "independent_participants")):
        return "#,##0"
    return None


def column_width(header: str, values: Iterable[Any]) -> float:
    h = header.lower()
    if "source path" in h or "source_file" in h:
        return 64
    if "link" in h:
        return 44
    if any(tag in h for tag in ("rationale", "notes", "population", "observed coding", "interpretation", "exchangeability", "covariates", "clinical_label", "description")):
        return 44
    if any(tag in h for tag in ("family", "status", "role", "model", "analysis", "metric", "comparison", "exposure", "state", "reason", "endpoint")):
        return 28
    if any(tag in h for tag in ("id", "genus", "sample", "participant", "child")):
        return 19
    if any(tag in h for tag in ("profile", "patient", "sample", "datasets", "runs", "threshold", "pvalue", "p_value", "fdr", "fraction", "probability", "estimate", "effect", "ci_", "percent", "statistic", "r2", "rank", "seed", "n_", "_n")):
        return 16
    longest = max((len(str(value)) for value in values if value is not None), default=0)
    return max(13, min(25, max(len(header) + 2, longest + 2)))


def style_data_range(ws, header_row: int, headers: list[str], rows: list[list[Any]], table_name: str) -> str:
    if not headers:
        raise ValueError("Cannot add a table without headers")
    first_row = header_row
    last_row = header_row + len(rows)
    last_col = len(headers)
    for c, header in enumerate(headers, start=1):
        cell = ws.cell(header_row, c, header)
        cell.font = Font(name=FONT_NAME, size=10, bold=True, color=WHITE)
        cell.fill = PatternFill("solid", fgColor=NAVY)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = Border(bottom=Side(style="thin", color=WHITE))
    ws.row_dimensions[header_row].height = 34
    for r_offset, row in enumerate(rows, start=1):
        excel_row = header_row + r_offset
        max_lines = 1
        for c, (header, value) in enumerate(zip(headers, row), start=1):
            cell = ws.cell(excel_row, c, value)
            cell.font = Font(name=FONT_NAME, size=10, color=INK)
            is_numeric = isinstance(value, (int, float)) and not isinstance(value, bool)
            cell.alignment = Alignment(horizontal="right" if is_numeric else "left", vertical="center", wrap_text=True)
            fmt = number_format(header)
            if fmt and is_numeric:
                cell.number_format = fmt
            width = column_width(header, [value])
            if isinstance(value, str) and width:
                max_lines = max(max_lines, min(6, math.ceil(len(value) / max(12, width - 2))))
        ws.row_dimensions[excel_row].height = min(78, max(20, 15 * max_lines + 4))
    ref = f"A{first_row}:{get_column_letter(last_col)}{last_row}"
    table = Table(displayName=table_name, ref=ref)
    table.tableStyleInfo = TableStyleInfo(
        name="TableStyleMedium2", showFirstColumn=False, showLastColumn=False,
        showRowStripes=True, showColumnStripes=False,
    )
    ws.add_table(table)
    for c, header in enumerate(headers, start=1):
        values = [row[c - 1] for row in rows]
        ws.column_dimensions[get_column_letter(c)].width = column_width(header, values)
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.print_title_rows = f"1:{header_row}"
    return ref


def values_from_records(headers: list[str], records: list[dict[str, Any]]) -> list[list[Any]]:
    return [[typed(record.get(header), header) for header in headers] for record in records]


def add_tsv_table(ws, header_row: int, relative_path: str, table_name: str,
                  fields: list[str] | None = None,
                  display_headers: list[str] | None = None,
                  transform: Any | None = None) -> tuple[str, list[str], list[list[Any]]]:
    source_headers, source_records = read_tsv(relative_path)
    fields = fields or source_headers
    if not set(fields).issubset(source_headers):
        raise ValueError(f"Missing source field(s) in {relative_path}: {set(fields) - set(source_headers)}")
    headers = display_headers or fields
    if len(headers) != len(fields):
        raise ValueError("Display headers must match the selected source fields")
    rows = []
    for record in source_records:
        if transform is None:
            rows.append([typed(record.get(field), field) for field in fields])
        else:
            rows.append(transform(record, fields))
    ref = style_data_range(ws, header_row, headers, rows, table_name)
    # Preserve a machine-readable source trail in the table's top-right area.
    ws.cell(header_row - 1, 1, f"Source: {relative_path}")
    ws.cell(header_row - 1, 1).font = Font(name=FONT_NAME, size=9, italic=True, color=MUTED)
    return ref, fields, rows


def add_raw_tsv_table(ws, header_row: int, relative_path: str, table_name: str,
                      display_headers: list[str] | None = None) -> tuple[str, list[str], list[list[Any]]]:
    headers, records = read_tsv(relative_path)
    rows = values_from_records(headers, records)
    out_headers = display_headers or headers
    if len(out_headers) != len(headers):
        raise ValueError("Display headers must match source field count")
    ref = style_data_range(ws, header_row, out_headers, rows, table_name)
    ws.cell(header_row - 1, 1, f"Source: {relative_path}")
    ws.cell(header_row - 1, 1).font = Font(name=FONT_NAME, size=9, italic=True, color=MUTED)
    return ref, headers, rows


def same_value(actual: Any, expected: Any) -> bool:
    if isinstance(expected, (int, float)) and not isinstance(expected, bool):
        if not isinstance(actual, (int, float)) or isinstance(actual, bool):
            return False
        return math.isclose(float(actual), float(expected), rel_tol=1e-12, abs_tol=1e-12)
    return actual == expected


def verify_table(wb, ws_name: str, header_row: int, headers: list[str], rows: list[list[Any]],
                 label: str, source_path: str | None = None) -> None:
    ws = wb[ws_name]
    for col, expected in enumerate(headers, start=1):
        actual = ws.cell(header_row, col).value
        if actual != expected:
            raise AssertionError(f"{label}: header mismatch at {ws_name}!{get_column_letter(col)}{header_row}: {actual!r} != {expected!r}")
    for i, row in enumerate(rows, start=1):
        for col, expected in enumerate(row, start=1):
            actual = ws.cell(header_row + i, col).value
            if not same_value(actual, expected):
                raise AssertionError(f"{label}: value mismatch at {ws_name}!{get_column_letter(col)}{header_row+i}: {actual!r} != {expected!r}")
    if source_path:
        source_headers, source_rows = read_tsv(source_path)
        if len(source_rows) != len(rows):
            raise AssertionError(f"{label}: source row count {len(source_rows)} != workbook row count {len(rows)}")
        if label == "S1 coding and missingness":
            source_map: list[str | None] = ["variable", "n_profiles", "missing_profiles", None]
        elif label == "S2 11-candidate landscape":
            source_map = ["dataset_id_or_name", "modality", "sample_size", "population_or_ancestry", "access_link", "intended_role", None, None, "notes"]
        elif label == "S3 primary threshold estimates":
            source_map = ["threshold_percent", "exposed_profiles", "exposed_positive_profiles", "exposed_children", "unexposed_profiles", "unexposed_positive_profiles", "unexposed_children", "effect", "ci_lower", "ci_upper", "pvalue", "fdr", "n_profiles", "n_children", "covariates", "multiplicity_family"]
        elif label == "S5 patient paired differences":
            source_map = ["patient_id", "genus", "adenoid_percent", "tonsil_percent", "difference_tonsil_minus_adenoid"]
        elif headers == source_headers:
            source_map = list(headers)
        else:
            raise AssertionError(f"{label}: source field mapping is required for {source_path}")
        if len(source_map) != len(headers):
            raise AssertionError(f"{label}: invalid source-field map length")
        for i, source_record in enumerate(source_rows, start=1):
            for col, source_field in enumerate(source_map, start=1):
                if source_field is None:
                    continue
                expected = typed(source_record.get(source_field), source_field)
                actual = ws.cell(header_row + i, col).value
                if not same_value(actual, expected):
                    raise AssertionError(f"{label}: source mismatch at {ws_name}!{get_column_letter(col)}{header_row+i} from {source_path}:{source_field}")


def add_source_index(wb, provenance: list[tuple[str, str, int | str, str]]) -> None:
    ws = wb.create_sheet("Read Me", 0)
    set_base_sheet(ws, "7F8FA6")
    put_title(ws, "Supplementary tables", "Results are presented in the numbered tables S1–S7. Companion tabs hold long row-level data for the corresponding table.")
    ws["A4"] = "Table"
    ws["B4"] = "Title"
    ws["C4"] = "Worksheet(s)"
    ws["D4"] = "Source records"
    ws["E4"] = "Reader note"
    index = [
        ["S1", "Covariate coding and missingness", "S1_Covariates", "results/primary/covariate_coding_missingness.tsv", "Profile-level availability in the endpoint analysis set."],
        ["S2", "Dataset landscape and selection flow", "S2_Datasets", "docs/DATASET_LANDSCAPE.tsv; docs/DATASET_SUITABILITY_DECISION.md; docs/DATASET_SCREEN_FLOW.tsv; results/primary/cohort_flow.tsv", "Repository-based candidate landscape; it is not a comprehensive systematic search."],
        ["S3", "Threshold counts and adjusted associations", "S3_Thresholds; S3_ExternalCounts; S3_ExternalLabels", "results/primary/threshold_sensitivity.tsv; threshold_agreement.tsv; results/external/state_counts.tsv; threshold_concordance.tsv", "Nominal P values and BH-adjusted values are shown separately."],
        ["S4", "Model summaries and analysis membership", "S4_Models; S4_Bootstrap; S4_LOO; S4_Membership", "results/primary/adjusted_models.tsv; genus_models.tsv; no_tobacco_model.tsv; bootstrap_summary.tsv; leave_one_child_out*.tsv; model_membership.tsv", "Membership lists the source de-identified sample and child IDs for each fitted model."],
        ["S5", "Paired genus effects, zeros, and ties", "S5_PairedTests; S5_PairValues", "results/external/paired_genus_effects.tsv; patient_paired_differences.tsv", "The reported family contains 27 preselected paired tests."],
        ["S6", "Community-level tests and diagnostics", "S6_Community; S6_CentroidDistances", "results/primary/community_tests.tsv; community_diagnostics.txt; results/external/permanova.tsv; dispersion.tsv; centroid_distances.tsv", "External-cohort PERMANOVA and dispersion results are reported independently."],
        ["S7", "Child-level burden and earliest-profile analyses", "S7_ChildAnalysis; S7_ChildFlow", "results/primary/child_burden.tsv; child_burden_model.tsv; earliest_profile_model.tsv; cohort_flow.tsv; child_flow.tsv", "The earliest-profile model uses one first eligible profile per analyzed child."],
    ]
    for r, row in enumerate(index, start=5):
        for c, value in enumerate(row, start=1):
            ws.cell(r, c, value)
    style_data_range(ws, 4, ["Table", "Title", "Worksheet(s)", "Source records", "Reader note"], index, "SupplementTableIndex")
    ws["A15"] = "Provenance"
    ws["A15"].font = Font(name=FONT_NAME, size=12, bold=True, color=NAVY)
    provenance_headers = ["Table", "Source path", "Rows", "Use"]
    provenance_rows = [[table, path, count, use] for table, path, count, use in provenance]
    style_data_range(ws, 17, provenance_headers, provenance_rows, "SupplementSources")
    ws["A16"] = "Source paths are relative to the project root. All result values are copied from the listed files; no model is re-estimated by this workbook builder."
    ws["A16"].font = Font(name=FONT_NAME, size=9, italic=True, color=MUTED)
    ws["A16"].alignment = Alignment(wrap_text=True)
    ws["A16"].hyperlink = None
    ws["A16"].fill = PatternFill("solid", fgColor=PALE)
    footer_row = 19 + len(provenance)
    ws.cell(footer_row, 1, "Participant identifiers")
    ws.cell(footer_row, 1).font = Font(name=FONT_NAME, size=11, bold=True, color=NAVY)
    ws.cell(footer_row + 1, 1, "Identifiers appear only when they were already present in de-identified public-study result files.")
    ws.cell(footer_row + 1, 1).font = Font(name=FONT_NAME, size=10, color=INK)
    ws.cell(footer_row + 1, 1).alignment = Alignment(wrap_text=False)
    ws.column_dimensions["A"].width = 20
    ws.column_dimensions["B"].width = 40
    ws.column_dimensions["C"].width = 39
    ws.column_dimensions["D"].width = 74
    ws.column_dimensions["E"].width = 54
    ws.freeze_panes = "A5"
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.print_area = f"A1:E{footer_row + 1}"


def add_custom_table(ws, header_row: int, table_name: str, headers: list[str], rows: list[list[Any]]) -> str:
    return style_data_range(ws, header_row, headers, rows, table_name)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    wb.remove(wb.active)
    checks: list[tuple[str, int, list[str], list[list[Any]], str, str | None]] = []
    source_meta: list[tuple[str, str, int | str, str]] = []

    # S1: coding and missingness. Long numerical value enumerations are summarized
    # as variable descriptions; the TSV remains the exact source record.
    ws = wb.create_sheet("S1_Covariates")
    set_base_sheet(ws)
    start = put_title(ws, "S1. Covariate coding and missingness", "Endpoint analysis set: 323 profiles. Observed values use the coding recorded by the analysis output.")
    src = "results/primary/covariate_coding_missingness.tsv"
    _, records = read_tsv(src)
    note_values = {
        "sinusitis_binary": "Binary endpoint; 0 = URI, 1 = sinusitis",
        "moraxella_30": "Binary exposure; 1 = Moraxella-dominant at ≥30%, 0 = otherwise",
        "child_id": "De-identified public child identifiers; memberships are listed in model and child-level tabs",
        "season": "Observed categories: Fall; Spring; Summer; Winter",
        "daycare": "Observed categories: No; Yes",
        "tobacco_exposure": "Observed categories: No; Yes",
        "virus_count": "Observed values: 0; 1; 2; 4",
        "age_init": "Observed ages at initial visit: 4; 5; 6 years",
        "shannon": "Continuous Shannon diversity index; source TSV enumerates observed profile values",
        "AB_Taken": "Binary antibiotic-taken field; observed values: 0; 1",
    }
    s1_headers = ["variable", "n_profiles", "missing_profiles", "observed coding / values"]
    s1_rows = [[r["variable"], typed(r["n_profiles"], "n_profiles"), typed(r["missing_profiles"], "missing_profiles"), note_values[r["variable"]]] for r in records]
    add_custom_table(ws, start, "S1CovariateCoding", s1_headers, s1_rows)
    ws.freeze_panes = "A5"
    checks.append((ws.title, start, s1_headers, s1_rows, "S1 coding and missingness", src))
    source_meta.append(("S1", src, len(records), "Coding and missing-profile counts"))

    # S2: use the existing repository landscape and contemporaneous selection record.
    ws = wb.create_sheet("S2_Datasets")
    set_base_sheet(ws)
    start = put_title(ws, "S2. Public dataset landscape and selection flow", "This is the existing repository-based candidate screen, not an exhaustive database search or systematic review.")
    landscape_path = "docs/DATASET_LANDSCAPE.tsv"
    _, landscape = read_tsv(landscape_path)
    dispositions = {
        "PRJEB35160": ("Included: primary endpoint cohort", "Direct pediatric URI/sinusitis endpoint with child identifiers, selected covariates, and public processed data."),
        "PRJNA422760": ("Included: phenotype-transfer cohort", "Pediatric paired adenoid/tonsil samples; public patient, tissue, and HP/SOM labels support descriptive state-transfer analysis."),
        "PRJNA554533": ("Not analyzed: labels unavailable", "The public records did not provide a verifiable sample-to-AH/AR/control mapping."),
        "PRJEB88727": ("Held pending label verification", "OME cohort is relevant, but clinical labels and timepoints require verification before analysis."),
        "PRJNA275918": ("Adjacent background only", "Large infant nasopharyngeal cohort; age and endpoint differ from the target clinical question."),
        "PRJNA1413967": ("Adjacent-control candidate", "Asthma/control throat-swab cohort; clinical labeling is insufficient for the ENT endpoint."),
        "PRJNA1049442": ("Excluded from 16S mainline", "Shotgun modality and HIV host context differ from the 16S ENT cohorts."),
        "PRJEB72800": ("Unresolved in first run check", "The first ENA run-metadata request returned no rows."),
        "PRJNA861845": ("Unresolved in first accession check", "The first SRA RunInfo request did not resolve the reported accession."),
        "PRJNA1441615": ("Excluded from mainline", "Small special-population tonsil cohort with Down syndrome/OSA context."),
        "PRJNA615768": ("Excluded from mainline", "Tonsil/saliva comparison with modality and metadata ambiguity."),
    }
    s2_headers = ["dataset_id_or_name", "modality", "sample_size", "population_or_ancestry", "access_link", "intended_role", "screening_disposition", "selection_reason", "notes"]
    s2_rows = []
    for r in landscape:
        status, reason = dispositions[r["dataset_id_or_name"]]
        s2_rows.append([r["dataset_id_or_name"], r["modality"], r["sample_size"], r["population_or_ancestry"], r["access_link"], r["intended_role"], status, reason, r["notes"]])
    add_custom_table(ws, start, "S2DatasetLandscape", s2_headers, s2_rows)
    for i, row in enumerate(s2_rows, start=start + 1):
        link = ws.cell(i, 5).value
        if isinstance(link, str) and link.startswith("http"):
            ws.cell(i, 5).hyperlink = link
            ws.cell(i, 5).style = "Hyperlink"
    flow_path = "docs/DATASET_SCREEN_FLOW.tsv"
    cohort_flow_path = "results/primary/cohort_flow.tsv"
    flow_header_row = start + len(s2_rows) + 5
    _, flow_source_records = read_tsv(flow_path)
    _, cohort_flow_records = read_tsv(cohort_flow_path)
    cohort_flow = {record["stage"]: record for record in cohort_flow_records}
    required_stages = {"all_released", "excluded_no_group", "included"}
    if set(cohort_flow) != required_stages:
        raise AssertionError(f"Unexpected finalized cohort flow stages: {sorted(cohort_flow)}")
    if (int(cohort_flow["all_released"]["profiles"]) - int(cohort_flow["excluded_no_group"]["profiles"]) != int(cohort_flow["included"]["profiles"])
            or int(cohort_flow["all_released"]["children"]) - int(cohort_flow["excluded_no_group"]["children"]) != int(cohort_flow["included"]["children"])):
        raise AssertionError("Finalized released, excluded, and included cohort counts do not reconcile")
    flow_headers = ["Flow stage", "Datasets (n)", "Independent participants / children (n)", "Profiles or runs (n)", "Status", "Rationale"]
    released = cohort_flow["all_released"]
    excluded = cohort_flow["excluded_no_group"]
    included = cohort_flow["included"]
    flow_rows = [
        ["Public pediatric airway or ENT datasets screened", 11, None, None, "Screened", "Public access, pediatric relevance, airway or ENT sampling, and label availability were reviewed."],
        ["Primary endpoint cohort: all released", 1, typed(released["children"], "children"), typed(released["profiles"], "profiles"), "Released", "Counts from finalized endpoint cohort flow."],
        ["Primary endpoint cohort: eligible profiles included", 1, typed(included["children"], "children"), typed(included["profiles"], "profiles"), "Analyzed", "URI and sinusitis profiles with eligible outcome labels."],
        ["Primary endpoint profiles excluded for no eligible group", 1, typed(excluded["children"], "children"), typed(excluded["profiles"], "profiles"), "Excluded", "Released children and profiles with no eligible endpoint group."],
    ]
    for record in flow_source_records:
        if record["flow_stage"] in {
            "Secondary pediatric ENT cohort retained",
            "Label-insufficient pediatric ENT cohort not analyzed",
            "Adjacent-control or metadata-only cohorts not used for main claims",
        }:
            flow_rows.append([
                record["flow_stage"], typed(record["datasets"], "datasets"),
                typed(record["independent_participants"], "independent_participants"),
                typed(record["profiles_or_runs"], "profiles_or_runs"), record["status"], record["rationale"],
            ])
    if len(flow_rows) != 7:
        raise AssertionError(f"Expected seven reconciled S2 flow rows, found {len(flow_rows)}")
    ws.cell(flow_header_row - 1, 1, f"Sources: {flow_path} (dataset-level screen and non-primary cohorts); {cohort_flow_path} (primary endpoint flow)")
    ws.cell(flow_header_row - 1, 1).font = Font(name=FONT_NAME, size=9, italic=True, color=MUTED)
    add_custom_table(ws, flow_header_row, "S2DatasetFlow", flow_headers, flow_rows)
    ws.freeze_panes = "A5"
    checks.append((ws.title, start, s2_headers, s2_rows, "S2 11-candidate landscape", landscape_path))
    checks.append((ws.title, flow_header_row, flow_headers, flow_rows, "S2 reconciled dataset and endpoint flow", None))
    if len(landscape) != 11:
        raise AssertionError(f"Expected the documented 11 candidates, found {len(landscape)}")
    source_meta.extend([
        ("S2", landscape_path, len(landscape), "Candidate dataset descriptors and access links"),
        ("S2", "docs/DATASET_SUITABILITY_DECISION.md", "11 decisions", "Disposition and rationale for each candidate"),
        ("S2", flow_path, "4 of 5 records", "Dataset screen and non-primary cohort flow; primary endpoint counts are sourced separately"),
        ("S2", cohort_flow_path, len(cohort_flow_records), "Finalized primary release, exclusion, and analysis flow"),
    ])

    # S3: primary threshold models and external state counts/classifications.
    ws = wb.create_sheet("S3_Thresholds")
    set_base_sheet(ws)
    start = put_title(ws, "S3. Moraxella threshold counts and adjusted associations", "Adjusted odds ratios include season, daycare, and child-cluster robust inference. Raw P values and Benjamini–Hochberg FDR are distinct columns.")
    src = "results/primary/threshold_sensitivity.tsv"
    fields = ["threshold_percent", "exposed_profiles", "exposed_positive_profiles", "exposed_children", "unexposed_profiles", "unexposed_positive_profiles", "unexposed_children", "effect", "ci_lower", "ci_upper", "pvalue", "fdr", "n_profiles", "n_children", "covariates", "multiplicity_family"]
    display = ["Threshold (%)", "Moraxella-positive profiles (n)", "Sinusitis profiles among exposed (n)", "Children with ≥1 exposed profile (n)", "Moraxella-negative profiles (n)", "Sinusitis profiles among unexposed (n)", "Children with ≥1 unexposed profile (n)", "Adjusted odds ratio", "95% CI lower", "95% CI upper", "Raw P value", "Benjamini–Hochberg FDR", "Profiles in model (n)", "Children in model (n)", "Covariates", "Multiplicity family"]
    ref, _, rows = add_tsv_table(ws, start, src, "S3ThresholdSensitivity", fields, display)
    checks.append((ws.title, start, display, rows, "S3 primary threshold estimates", src))
    agree_src = "results/primary/threshold_agreement.tsv"
    agreement_row = start + len(rows) + 4
    agree_headers, agree_records = read_tsv(agree_src)
    agree_rows = values_from_records(agree_headers, agree_records)
    add_custom_table(ws, agreement_row, "S3PrimaryThresholdAgreement", agree_headers, agree_rows)
    checks.append((ws.title, agreement_row, agree_headers, agree_rows, "S3 primary 25-versus-30 agreement", agree_src))
    ws.freeze_panes = "A5"
    source_meta.extend([
        ("S3", src, len(rows), "Primary 25%, 30%, and 50% threshold counts and models"),
        ("S3", agree_src, len(agree_rows), "Primary 25% versus 30% classification agreement"),
    ])

    ws = wb.create_sheet("S3_ExternalCounts")
    set_base_sheet(ws)
    start = put_title(ws, "S3. External-cohort state counts by threshold", "PRJNA422760 counts are descriptive state assignments by tissue and HP/SOM group.")
    src = "results/external/state_counts.tsv"
    fields, rows = read_tsv(src)
    typed_rows = values_from_records(fields, rows)
    add_raw_tsv_table(ws, start, src, "S3ExternalStateCounts")
    ws.freeze_panes = "A5"
    checks.append((ws.title, start, fields, typed_rows, "S3 external state counts", src))
    source_meta.append(("S3", src, len(rows), "External state-count distribution"))

    ws = wb.create_sheet("S3_ExternalLabels")
    set_base_sheet(ws)
    start = put_title(ws, "S3. External-cohort sample states across thresholds", "Sample IDs are the public, de-identified labels present in the source result table.")
    src = "results/external/threshold_concordance.tsv"
    fields, rows = read_tsv(src)
    typed_rows = values_from_records(fields, rows)
    add_raw_tsv_table(ws, start, src, "S3ExternalThresholdLabels")
    ws.freeze_panes = "B5"
    checks.append((ws.title, start, fields, typed_rows, "S3 external sample threshold labels", src))
    source_meta.append(("S3", src, len(rows), "Per-sample external state labels at 25%, 30%, and 50%"))

    # S4: source model summaries, bootstrap intervals, leave-one-child-out fits,
    # and complete model membership. Each companion tab belongs to S4.
    ws = wb.create_sheet("S4_Models")
    set_base_sheet(ws)
    start = put_title(ws, "S4. Primary and focused model summaries", "Model estimates are reported as stored in the finalized result TSVs. Sensitivity and genus-level results retain their source multiplicity labels.")
    summary_headers = ["source_table", "model_family", "model", "exposure", "covariates", "effect_type", "effect", "ci_lower", "ci_upper", "pvalue", "fdr", "n_profiles", "n_children", "positive_profiles", "positive_children", "reference_df", "covariance", "weighting", "multiplicity_family", "genus", "median_fraction_URI", "median_fraction_Sinusitis", "condition_number", "converged", "warnings"]
    source_specs = [
        ("results/primary/adjusted_models.tsv", "profile-level association/sensitivity", ["model", "exposure", "covariates", "effect_type", "effect", "ci_lower", "ci_upper", "pvalue", "fdr", "n_profiles", "n_children", "positive_profiles", "positive_children", "reference_df", "covariance", "weighting", "multiplicity_family", "condition_number", "converged", "warnings"]),
        ("results/primary/genus_models.tsv", "focused genus abundance", ["model", "exposure", "covariates", "effect_type", "effect", "ci_lower", "ci_upper", "pvalue", "n_profiles", "n_children", "positive_profiles", "positive_children", "reference_df", "covariance", "weighting", "fdr", "genus", "median_fraction_URI", "median_fraction_Sinusitis", "multiplicity_family", "condition_number", "converged", "warnings"]),
        ("results/primary/no_tobacco_model.tsv", "tobacco-restricted sensitivity", ["model", "exposure", "covariates", "effect_type", "effect", "ci_lower", "ci_upper", "pvalue", "n_profiles", "n_children", "positive_profiles", "positive_children", "reference_df", "covariance", "weighting", "condition_number", "converged", "warnings"]),
    ]
    output_rows: list[list[Any]] = []
    for src, family, source_fields in source_specs:
        source_headers, records = read_tsv(src)
        if not set(source_fields).issubset(source_headers):
            raise ValueError(f"Missing required model field in {src}")
        for r in records:
            row = [src.rsplit("/", 1)[-1], family]
            for field in summary_headers[2:]:
                row.append(typed(r.get(field), field) if field in source_fields else None)
            output_rows.append(row)
        source_meta.append(("S4", src, len(records), family))
    add_custom_table(ws, start, "S4ModelSummaries", summary_headers, output_rows)
    ws.freeze_panes = "C5"
    checks.append((ws.title, start, summary_headers, output_rows, "S4 model summary records", None))

    ws = wb.create_sheet("S4_Bootstrap")
    set_base_sheet(ws)
    start = put_title(ws, "S4. Child-cluster bootstrap summaries", "Bootstrap intervals and convergence counts are copied from the finalized summary; seed is preserved.")
    src = "results/primary/bootstrap_summary.tsv"
    fields, rows = read_tsv(src)
    typed_rows = values_from_records(fields, rows)
    add_raw_tsv_table(ws, start, src, "S4BootstrapSummary")
    ws.freeze_panes = "A5"
    checks.append((ws.title, start, fields, typed_rows, "S4 bootstrap summary", src))
    source_meta.append(("S4", src, len(rows), "Point estimates, bootstrap intervals, successful and failed resamples"))

    ws = wb.create_sheet("S4_LOO")
    set_base_sheet(ws)
    start = put_title(ws, "S4. Leave-one-child-out model fits", "Each row omits the named de-identified child from the primary covariate-adjusted model. The source summary identifies the range as an influence range, not a confidence interval.")
    src = "results/primary/leave_one_child_out.tsv"
    fields, rows = read_tsv(src)
    typed_rows = values_from_records(fields, rows)
    add_raw_tsv_table(ws, start, src, "S4LeaveOneChildOutFits")
    ws.freeze_panes = "B5"
    checks.append((ws.title, start, fields, typed_rows, "S4 leave-one-child-out fits", src))
    summary_src = "results/primary/leave_one_child_out_summary.tsv"
    summary_row = start + len(rows) + 4
    summary_headers, summary_records = read_tsv(summary_src)
    summary_rows = values_from_records(summary_headers, summary_records)
    add_custom_table(ws, summary_row, "S4LeaveOneChildOutRange", summary_headers, summary_rows)
    checks.append((ws.title, summary_row, summary_headers, summary_rows, "S4 leave-one-child-out range", summary_src))
    source_meta.extend([
        ("S4", src, len(rows), "Exact model fit by omitted child"),
        ("S4", summary_src, len(summary_rows), "Influence range summary"),
    ])

    ws = wb.create_sheet("S4_Membership")
    set_base_sheet(ws)
    start = put_title(ws, "S4. Exact model membership", "One row per sample included in each listed model. Identifiers are from the de-identified public-study output.")
    src = "results/primary/model_membership.tsv"
    fields, rows = read_tsv(src)
    typed_rows = values_from_records(fields, rows)
    add_raw_tsv_table(ws, start, src, "S4ModelMembership")
    ws.freeze_panes = "C5"
    checks.append((ws.title, start, fields, typed_rows, "S4 exact model membership", src))
    source_meta.append(("S4", src, len(rows), "Sample, child, and outcome membership for all fitted models"))

    # S5: all 27 paired tests and row-level paired differences.
    ws = wb.create_sheet("S5_PairedTests")
    set_base_sheet(ws)
    start = put_title(ws, "S5. Paired genus effects, zeros, and tied ranks", "The 27-test family, Wilcoxon zero method, continuity-correction setting, zero differences, and tied absolute ranks are retained from the source table.")
    src = "results/external/paired_genus_effects.tsv"
    fields, rows = read_tsv(src)
    typed_rows = values_from_records(fields, rows)
    add_raw_tsv_table(ws, start, src, "S5PairedGenusEffects")
    ws.freeze_panes = "C5"
    checks.append((ws.title, start, fields, typed_rows, "S5 paired genus tests", src))
    source_meta.append(("S5", src, len(rows), "All preselected paired genus-by-group tests"))

    ws = wb.create_sheet("S5_PairValues")
    set_base_sheet(ws)
    start = put_title(ws, "S5. Paired patient-level genus differences", "Values are percentages; the signed difference is tonsil minus adenoid. Patient IDs remain as recorded in the public output.")
    src = "results/external/patient_paired_differences.tsv"
    fields, rows = read_tsv(src)
    typed_rows = values_from_records(fields, rows)
    pair_headers = ["patient_id", "genus", "Adenoid (%)", "Tonsil (%)", "Tonsil minus adenoid (percentage points)"]
    add_raw_tsv_table(ws, start, src, "S5PatientPairedDifferences", pair_headers)
    ws.freeze_panes = "C5"
    checks.append((ws.title, start, pair_headers, typed_rows, "S5 patient paired differences", src))
    source_meta.append(("S5", src, len(rows), "Patient-level genus values used by paired comparisons"))

    # S6: primary community outputs and external cohort PERMANOVA/dispersion.
    ws = wb.create_sheet("S6_Community")
    set_base_sheet(ws)
    start = put_title(ws, "S6. Community-level tests and diagnostics", "Primary tests use child-mean OTU composition. External cohort tests use published genus percentages; dispersion results are shown alongside PERMANOVA.")
    primary_src = "results/primary/community_tests.tsv"
    p_headers, p_rows = read_tsv(primary_src)
    p_values = values_from_records(p_headers, p_rows)
    add_raw_tsv_table(ws, start, primary_src, "S6PrimaryCommunityTests")
    checks.append((ws.title, start, p_headers, p_values, "S6 primary community tests", primary_src))
    source_meta.append(("S6", primary_src, len(p_rows), "Primary child-level PERMANOVA and PERMDISP"))
    detail_row = start + len(p_rows) + 4
    detail_headers = ["primary diagnostic", "value", "source interpretation"]
    detail_rows = [
        ["Mean distance to median: Sinusitis", 0.5117, "PERMDISP; type=median; bias.adjust=TRUE; Lingoes correction"],
        ["Mean distance to median: URI", 0.5828, "PERMDISP; type=median; bias.adjust=TRUE; Lingoes correction"],
        ["Positive PCoA eigenvalues", 43, "From primary community diagnostics"],
        ["Negative PCoA eigenvalues", 0, "From primary community diagnostics after Lingoes correction"],
    ]
    add_custom_table(ws, detail_row, "S6PrimaryDispersionDetail", detail_headers, detail_rows)
    checks.append((ws.title, detail_row, detail_headers, detail_rows, "S6 transcribed primary diagnostic detail", None))
    diag_path = "results/primary/community_diagnostics.txt"
    source_meta.append(("S6", diag_path, "text report", "Primary distance-to-median and eigenvalue diagnostics"))
    ws.freeze_panes = "A5"

    ws = wb.create_sheet("S6_ExternalTests")
    set_base_sheet(ws)
    start = put_title(ws, "S6. External-cohort PERMANOVA and dispersion", "PRJNA422760: 56 samples from 28 paired patients. Three comparisons are shown for each test family.")
    src = "results/external/permanova.tsv"
    fields, rows = read_tsv(src)
    typed_rows = values_from_records(fields, rows)
    add_raw_tsv_table(ws, start, src, "S6ExternalPermanova")
    checks.append((ws.title, start, fields, typed_rows, "S6 external PERMANOVA", src))
    disp_src = "results/external/dispersion.tsv"
    disp_row = start + len(rows) + 4
    disp_headers, disp_records = read_tsv(disp_src)
    disp_values = values_from_records(disp_headers, disp_records)
    add_raw_tsv_table(ws, disp_row, disp_src, "S6ExternalDispersion")
    checks.append((ws.title, disp_row, disp_headers, disp_values, "S6 external dispersion", disp_src))
    ws.freeze_panes = "C5"
    source_meta.extend([
        ("S6", src, len(rows), "External-cohort Bray–Curtis PERMANOVA results"),
        ("S6", disp_src, len(disp_values), "External-cohort dispersion diagnostics"),
    ])

    ws = wb.create_sheet("S6_CentroidDistances")
    set_base_sheet(ws)
    start = put_title(ws, "S6. External-cohort sample centroid distances", "Per-sample distances are included as supporting diagnostics; labels match the external-cohort comparison table.")
    src = "results/external/centroid_distances.tsv"
    fields, rows = read_tsv(src)
    typed_rows = values_from_records(fields, rows)
    add_raw_tsv_table(ws, start, src, "S6CentroidDistances")
    ws.freeze_panes = "B5"
    checks.append((ws.title, start, fields, typed_rows, "S6 external centroid distances", src))
    source_meta.append(("S6", src, len(rows), "Per-sample distance to group centroid"))

    # S7: child burden, child-level model summaries, and earliest profile model.
    ws = wb.create_sheet("S7_ChildAnalysis")
    set_base_sheet(ws)
    start = put_title(ws, "S7. Child-level burden and earliest-profile analyses", "Child-level outputs use 45 children with eligible URI/sinusitis profiles. Burden is summarized per child; the earliest-profile model uses one first eligible profile per child.")
    src = "results/primary/child_burden.tsv"
    fields, rows = read_tsv(src)
    typed_rows = values_from_records(fields, rows)
    add_raw_tsv_table(ws, start, src, "S7ChildBurden")
    checks.append((ws.title, start, fields, typed_rows, "S7 per-child burden", src))
    source_meta.append(("S7", src, len(rows), "Child-level burden and covariates"))
    model_row = start + len(rows) + 4
    model_headers = ["analysis", "source_table", "model", "exposure", "covariates", "effect_type", "effect", "ci_lower", "ci_upper", "pvalue", "n_profiles", "n_children", "positive_profiles", "positive_children", "reference_df", "covariance", "weighting", "condition_number", "converged"]
    child_model_rows = []
    for path, analysis_label in [
        ("results/primary/child_burden_model.tsv", "Child burden per 25 percentage-point increase"),
        ("results/primary/earliest_profile_model.tsv", "Earliest eligible profile per child"),
    ]:
        _, model_records = read_tsv(path)
        for r in model_records:
            row = [analysis_label, path.rsplit("/", 1)[-1]] + [typed(r.get(h), h) for h in model_headers[2:]]
            child_model_rows.append(row)
        source_meta.append(("S7", path, len(model_records), analysis_label))
    add_custom_table(ws, model_row, "S7ChildModels", model_headers, child_model_rows)
    checks.append((ws.title, model_row, model_headers, child_model_rows, "S7 child-level models", None))
    flow_row = model_row + len(child_model_rows) + 4
    flow_src = "results/primary/cohort_flow.tsv"
    flow_headers, flow_records = read_tsv(flow_src)
    flow_values = values_from_records(flow_headers, flow_records)
    add_tsv_table(ws, flow_row, flow_src, "S7CohortFlow")
    checks.append((ws.title, flow_row, flow_headers, flow_values, "S7 cohort flow", flow_src))
    ws.freeze_panes = "A5"
    source_meta.append(("S7", flow_src, len(flow_records), "Original endpoint cohort profile and child flow"))

    ws = wb.create_sheet("S7_ChildFlow")
    set_base_sheet(ws)
    start = put_title(ws, "S7. Child-level eligibility and profile flow", "The source file lists every de-identified child in the released profile set and the number of URI/sinusitis profiles retained for analysis.")
    src = "results/primary/child_flow.tsv"
    fields, rows = read_tsv(src)
    typed_rows = values_from_records(fields, rows)
    add_raw_tsv_table(ws, start, src, "S7ChildEligibilityFlow")
    ws.freeze_panes = "B5"
    checks.append((ws.title, start, fields, typed_rows, "S7 child flow", src))
    source_meta.append(("S7", src, len(rows), "Child-level released-to-analysis flow"))

    add_source_index(wb, source_meta)
    wb.active = 0

    # Workbook-level consistency and cell/value read-back checks.
    wb.save(OUTPUT_XLSX)

    readback = load_workbook(OUTPUT_XLSX, data_only=False, read_only=False)
    for ws_name, header_row, headers, rows, label, source_path in checks:
        verify_table(readback, ws_name, header_row, headers, rows, label, source_path)
    formula_cells = []
    error_values = {"#REF!", "#DIV/0!", "#VALUE!", "#NAME?", "#N/A", "#NUM!", "#NULL!", "#SPILL!", "#CALC!"}
    for ws in readback.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                if isinstance(cell.value, str) and cell.value.startswith("="):
                    formula_cells.append(f"{ws.title}!{cell.coordinate}")
                if cell.value in error_values:
                    raise AssertionError(f"Unexpected spreadsheet error value at {ws.title}!{cell.coordinate}: {cell.value}")
    if formula_cells:
        raise AssertionError(f"This workbook should contain no formulas; found {formula_cells[:8]}")

    write_markdown(source_meta)
    print(f"Created {OUTPUT_XLSX.relative_to(ROOT)} ({OUTPUT_XLSX.stat().st_size:,} bytes)")
    print(f"Created {OUTPUT_MD.relative_to(ROOT)}")
    print(f"Verified {len(checks)} populated source/table blocks; formulas={len(formula_cells)}; unexpected error values=0")
    print(f"Workbook sheets: {', '.join(readback.sheetnames)}")


def write_markdown(source_meta: list[tuple[str, str, int | str, str]]) -> None:
    def load(path: str) -> list[dict[str, str]]:
        return read_tsv(path)[1]

    def fmt(value: Any, digits: int = 4) -> str:
        if value is None or value == "":
            return "—"
        try:
            number = float(value)
            if not math.isfinite(number):
                return str(value)
            return f"{number:.{digits}g}"
        except (TypeError, ValueError):
            return str(value)

    def md_table(headers: list[str], rows: list[list[Any]]) -> str:
        def clean(value: Any) -> str:
            return str(value).replace("|", "\\|").replace("\n", " ")

        return "\n".join([
            "| " + " | ".join(clean(h) for h in headers) + " |",
            "| " + " | ".join("---" for _ in headers) + " |",
            *["| " + " | ".join(clean(v) for v in row) + " |" for row in rows],
        ])

    # S1: retain readable coding descriptions rather than dumping long numeric
    # enumerations or the complete child-ID list into the Markdown companion.
    s1_notes = {
        "sinusitis_binary": "Binary outcome: URI / sinusitis (0/1)",
        "moraxella_30": "Binary exposure: below / at least 30% (0/1)",
        "child_id": "De-identified public child IDs; memberships are listed in S4 and S7",
        "season": "Fall; Spring; Summer; Winter",
        "daycare": "No; Yes",
        "tobacco_exposure": "No; Yes",
        "virus_count": "0; 1; 2; 4",
        "age_init": "4; 5; 6 years",
        "shannon": "Continuous Shannon diversity index",
        "AB_Taken": "Binary antibiotic-taken field (0/1)",
    }
    s1 = load("results/primary/covariate_coding_missingness.tsv")
    s1_table = md_table(
        ["Variable", "Profiles (n)", "Missing profiles (n)", "Coding / values"],
        [[r["variable"], r["n_profiles"], r["missing_profiles"], s1_notes[r["variable"]]] for r in s1],
    )

    # S2: record all 11 repository candidates, then display dataset-level flow
    # alongside finalized endpoint flow. The old candidate-flow primary row is
    # deliberately not used for the analysis denominator.
    s2_dispositions = {
        "PRJEB35160": ("Included: primary endpoint cohort", "Direct pediatric URI/sinusitis endpoint with child identifiers and selected covariates."),
        "PRJNA422760": ("Included: phenotype-transfer cohort", "Paired adenoid/tonsil samples with patient, tissue, and HP/SOM labels."),
        "PRJNA554533": ("Not analyzed: labels unavailable", "No verifiable public sample-to-AH/AR/control mapping."),
        "PRJEB88727": ("Held pending label verification", "OME cohort; clinical labels and timepoints require verification."),
        "PRJNA275918": ("Adjacent background only", "Large infant nasopharyngeal cohort; age and endpoint differ."),
        "PRJNA1413967": ("Adjacent-control candidate", "Asthma/control throat swabs do not match the ENT endpoint."),
        "PRJNA1049442": ("Excluded from 16S mainline", "Shotgun modality and HIV host context differ from the 16S cohorts."),
        "PRJEB72800": ("Unresolved accession check", "ENA run-metadata request returned no rows."),
        "PRJNA861845": ("Unresolved accession check", "SRA RunInfo request did not resolve the reported accession."),
        "PRJNA1441615": ("Excluded from mainline", "Small special-population tonsil cohort with Down syndrome/OSA context."),
        "PRJNA615768": ("Excluded from mainline", "Tonsil/saliva comparison with modality and metadata ambiguity."),
    }
    landscape = load("docs/DATASET_LANDSCAPE.tsv")
    s2_table = md_table(
        ["Candidate", "Role", "Reported size", "Disposition and selection rationale"],
        [[r["dataset_id_or_name"], r["intended_role"], r["sample_size"], " — ".join(s2_dispositions[r["dataset_id_or_name"]])]
         for r in landscape],
    )
    dataset_flow = load("docs/DATASET_SCREEN_FLOW.tsv")
    cohort_flow = {r["stage"]: r for r in load("results/primary/cohort_flow.tsv")}
    s2_flow_rows = [
        ["Public pediatric airway or ENT datasets screened", "11", "—", "—", "Screened"],
        ["Primary endpoint cohort: all released", "1", cohort_flow["all_released"]["children"], cohort_flow["all_released"]["profiles"], "Released"],
        ["Primary endpoint cohort: eligible profiles included", "1", cohort_flow["included"]["children"], cohort_flow["included"]["profiles"], "Analyzed"],
        ["Primary endpoint profiles excluded for no eligible group", "1", cohort_flow["excluded_no_group"]["children"], cohort_flow["excluded_no_group"]["profiles"], "Excluded"],
    ]
    for r in dataset_flow:
        if r["step"] in {"3", "4", "5"}:
            s2_flow_rows.append([r["flow_stage"], r["datasets"], r["independent_participants"] or "—", r["profiles_or_runs"] or "—", r["status"]])
    s2_flow_table = md_table(
        ["Flow stage", "Datasets (n)", "Participants / children (n)", "Profiles / runs (n)", "Status"],
        s2_flow_rows,
    )

    # S3: threshold counts and model effects, with raw P and BH FDR distinct.
    thresholds = load("results/primary/threshold_sensitivity.tsv")
    s3_table = md_table(
        ["Threshold", "Exposed profiles / sinusitis profiles", "Unexposed profiles / sinusitis profiles", "Adjusted OR (95% CI)", "Raw P", "BH FDR"],
        [[f"{r['threshold_percent']}%", f"{r['exposed_profiles']} / {r['exposed_positive_profiles']}",
          f"{r['unexposed_profiles']} / {r['unexposed_positive_profiles']}",
          f"{fmt(r['effect'], 4)} ({fmt(r['ci_lower'], 4)}–{fmt(r['ci_upper'], 4)})", fmt(r["pvalue"]), fmt(r["fdr"])]
         for r in thresholds],
    )

    # S4: exact model summaries from the finalized model TSVs; exact member rows
    # remain in the workbook's S4_Membership worksheet.
    model_records: list[tuple[str, dict[str, str]]] = []
    for path, label in [
        ("results/primary/adjusted_models.tsv", "Primary/sensitivity"),
        ("results/primary/no_tobacco_model.tsv", "Tobacco-restricted"),
    ]:
        model_records.extend((label, r) for r in load(path))
    s4_profile_table = md_table(
        ["Model family", "Model", "Exposure", "OR (95% CI)", "Raw P", "BH FDR", "Profiles", "Children"],
        [[family, r["model"], r["exposure"], f"{fmt(r['effect'], 4)} ({fmt(r['ci_lower'], 4)}–{fmt(r['ci_upper'], 4)})",
          fmt(r["pvalue"]), fmt(r.get("fdr", "NA")), r["n_profiles"], r["n_children"]] for family, r in model_records],
    )
    genus_records = load("results/primary/genus_models.tsv")
    s4_genus_table = md_table(
        ["Genus", "OR per 10-point increase (95% CI)", "Raw P", "BH FDR", "Median fraction, URI", "Median fraction, sinusitis"],
        [[r["genus"], f"{fmt(r['effect'], 4)} ({fmt(r['ci_lower'], 4)}–{fmt(r['ci_upper'], 4)})", fmt(r["pvalue"]),
          fmt(r["fdr"]), fmt(r["median_fraction_URI"], 4), fmt(r["median_fraction_Sinusitis"], 4)] for r in genus_records],
    )
    membership = load("results/primary/model_membership.tsv")
    membership_note = f"The companion `S4_Membership` worksheet contains all {len(membership):,} model/sample/child/outcome membership records from `model_membership.tsv`."
    bootstrap = load("results/primary/bootstrap_summary.tsv")
    primary_bootstrap = next(r for r in bootstrap if r["model"] == "primary" and r["metric"] == "odds_ratio")
    loo = load("results/primary/leave_one_child_out_summary.tsv")[0]

    # S5: every member of the specified 27-test family, including zeros/ties.
    paired = load("results/external/paired_genus_effects.tsv")
    s5_table = md_table(
        ["Comparison", "Group", "Genus", "Pairs", "Median paired difference (pp)", "Zero differences", "Tied-rank groups / observations", "Raw P", "BH FDR"],
        [[r["comparison"], r["clinical_group"], r["genus"], r["n_pairs"], fmt(r["median_paired_difference"], 4),
          r["n_zero_differences"], f"{r['n_tied_absolute_difference_groups']} / {r['n_observations_in_absolute_ties']}",
          fmt(r["p_value"]), fmt(r["p_bh"])] for r in paired],
    )

    # S6: display primary and external tests side-by-side without pooling them.
    s6_rows: list[list[Any]] = []
    for r in load("results/primary/community_tests.tsv"):
        s6_rows.append(["Primary " + r["analysis"], r["term"], f"{r['n_children']} children; {r['n_profiles']} profiles",
                        fmt(r["r2"], 4), fmt(r["statistic"], 4), fmt(r["pvalue"]), "Not reported", r["permutations"]])
    for r in load("results/external/permanova.tsv"):
        s6_rows.append(["External PERMANOVA", r["comparison"], f"{r['n_patients']} patients; {r['n_samples']} samples",
                        fmt(r["term_r2_total"], 4), fmt(r["pseudo_f"], 4), fmt(r["p_value"]), fmt(r["p_bh_3_tests"]), r["permutations_effective"]])
    for r in load("results/external/dispersion.tsv"):
        s6_rows.append(["External dispersion", r["comparison"], f"{r['n_patients']} patients; {r['n_samples']} samples",
                        "—", fmt(r["statistic_f"], 4), fmt(r["p_value"]), fmt(r["p_bh_3_tests"]), r["permutations_effective"]])
    s6_table = md_table(
        ["Test", "Comparison", "Independent units", "R²", "F statistic", "Raw P", "BH FDR", "Permutations"], s6_rows,
    )
    s6_diag = md_table(
        ["Primary dispersion diagnostic", "Value"],
        [["Mean distance to median: sinusitis", "0.5117"], ["Mean distance to median: URI", "0.5828"],
         ["Positive PCoA eigenvalues", "43"], ["Negative PCoA eigenvalues after Lingoes correction", "0"]],
    )

    # S7: group-level child burden, endpoint flow, and both child model outputs.
    descriptives = load("results/primary/group_descriptives.tsv")
    s7_group_table = md_table(
        ["Group", "Profiles", "Children", "Median profiles / child", "Median Moraxella burden", "Baseline age range"],
        [[r["group"], r["n_profiles"], r["n_children"], fmt(r["profiles_per_child_median"], 3), fmt(r["burden_median"], 3),
          f"{r['baseline_age_min']}–{r['baseline_age_max']} years"] for r in descriptives],
    )
    s7_flow_table = md_table(
        ["Cohort stage", "Profiles", "Children"],
        [[r["stage"], r["profiles"], r["children"]] for r in load("results/primary/cohort_flow.tsv")],
    )
    child_models = []
    for path, label in [
        ("results/primary/child_burden_model.tsv", "Child-level burden model"),
        ("results/primary/earliest_profile_model.tsv", "Earliest eligible profile per child"),
    ]:
        child_models.extend((label, r) for r in load(path))
    s7_models = md_table(
        ["Analysis", "OR (95% CI)", "Raw P", "Profiles", "Children"],
        [[label, f"{fmt(r['effect'], 4)} ({fmt(r['ci_lower'], 4)}–{fmt(r['ci_upper'], 4)})", fmt(r["pvalue"]),
          r["n_profiles"], r["n_children"]] for label, r in child_models],
    )

    source_rows = "\n".join(f"| {table} | `{path}` | {count} | {use} |" for table, path, count, use in source_meta)
    content = f"""# Supplementary Tables

The workbook contains seven numbered tables, S1–S7. Companion worksheets retain long row-level membership, paired-value, and sample-label details under the same table numbers. Markdown values are rounded for readability; the workbook preserves the precision stored in the source TSVs.

| Table | Title | Main worksheet | Supporting worksheets |
|---|---|---|---|
| S1 | Covariate coding and missingness | `S1_Covariates` | — |
| S2 | Public dataset landscape and selection flow | `S2_Datasets` | — |
| S3 | Moraxella threshold counts and adjusted associations | `S3_Thresholds` | `S3_ExternalCounts`, `S3_ExternalLabels` |
| S4 | Primary and focused model summaries | `S4_Models` | `S4_Bootstrap`, `S4_LOO`, `S4_Membership` |
| S5 | Paired genus effects, zeros, and tied ranks | `S5_PairedTests` | `S5_PairValues` |
| S6 | Community-level tests and diagnostics | `S6_Community` | `S6_ExternalTests`, `S6_CentroidDistances` |
| S7 | Child-level burden and earliest-profile analyses | `S7_ChildAnalysis` | `S7_ChildFlow` |

## S1. Covariate coding and missingness

{s1_table}

## S2. Dataset landscape and selection flow

The landscape is the repository-based screen of 11 candidates, not an exhaustive literature search or systematic review. Candidate-level counts and dispositions come from the existing dataset records; primary endpoint flow is reported from the finalized cohort flow.

{s2_table}

{s2_flow_table}

## S3. Threshold counts and adjusted associations

Each row uses the 323-profile, 45-child endpoint set. Exposed and unexposed child counts can overlap because children may contribute profiles to both exposure categories.

{s3_table}

## S4. Model summaries and explicit membership

The profile-level models use child-cluster robust inference where specified in the workbook. Sensitivity models remain labeled as such; genus models belong to a six-model focused family.

{s4_profile_table}

Focused genus models:

{s4_genus_table}

Primary child-cluster bootstrap odds ratio: {fmt(primary_bootstrap['estimate'], 4)} (percentile 95% interval {fmt(primary_bootstrap['ci_lower'], 4)}–{fmt(primary_bootstrap['ci_upper'], 4)}; {primary_bootstrap['successful']} successful / {primary_bootstrap['requested']} requested resamples). Leave-one-child-out primary odds ratios ranged from {fmt(loo['estimate_min'], 4)} to {fmt(loo['estimate_max'], 4)} across {loo['n_fits']} fits; this is an influence range, not a confidence interval. {membership_note}

## S5. Paired genus effects, zeros, and tied ranks

All 27 preselected paired tests are shown. The signed difference is tonsil minus adenoid in percentage points; the source Wilcoxon zero method is `wilcox`, with continuity correction off. The companion worksheet retains patient-level paired values.

{s5_table}

## S6. Community tests and diagnostics

Primary-child and external-patient analyses are presented independently. The primary PERMANOVA uses 45 child-mean compositions; the external cohort has 28 paired patients and 56 samples. PERMANOVA and dispersion tests are both shown.

{s6_table}

{s6_diag}

## S7. Child-level burden and earliest-profile analyses

Group descriptions summarize child-level burden. The earliest-profile model uses one first eligible profile per analyzed child.

{s7_group_table}

{s7_flow_table}

{s7_models}

## Source index

All result values are copied from the listed files; the builder does not refit models or calculate new estimates. Explanatory labels consolidate existing source annotations and decision records. Identifiers appear only when already present in de-identified public-study result files. Blank source fields remain blank in the workbook; literal `NA` values are preserved where reported.

| Table | Source path | Source rows | Use |
|---|---|---:|---|
{source_rows}

Workbook construction: `scripts/build_supplementary_tables.py`.
"""
    OUTPUT_MD.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
