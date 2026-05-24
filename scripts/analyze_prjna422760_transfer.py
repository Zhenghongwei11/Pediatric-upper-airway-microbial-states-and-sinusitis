#!/usr/bin/env python3
from __future__ import annotations

import csv
import math
import re
from pathlib import Path
from typing import Dict, List

import matplotlib.pyplot as plt
import numpy as np
import openpyxl
import pandas as pd
from scipy.spatial.distance import pdist, squareform
from scipy.stats import fisher_exact, mannwhitneyu, wilcoxon


ROOT = Path(__file__).resolve().parents[1]
WORKBOOK = ROOT / "data" / "references" / "external_labels" / "PRJNA422760" / "mSystems.00169-18-st003.xlsx"
METADATA_PATH = ROOT / "data" / "raw" / "metadata" / "PRJNA422760_run_metadata.tsv"
PROCESSED_DIR = ROOT / "data" / "processed"
RESULTS_DIR = ROOT / "results" / "replication"
DIAGNOSTIC_FIGURE_DIR = ROOT / "plots" / "diagnostic"

CANDIDATE_GENERA = [
    "Moraxella",
    "Haemophilus",
    "Streptococcus",
    "Fusobacterium",
    "Neisseria",
    "Alloprevotella",
    "Porphyromonas",
    "Prevotella",
    "Gemella",
]


def write_tsv(path: Path, rows: List[Dict[str, object]], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def benjamini_hochberg(p_values: List[float]) -> List[float]:
    indexed = sorted((p, index) for index, p in enumerate(p_values))
    adjusted = [math.nan] * len(p_values)
    running = 1.0
    total = len(indexed)
    for rank, (p_value, index) in enumerate(reversed(indexed), start=1):
        original_rank = total - rank + 1
        running = min(running, p_value * total / original_rank)
        adjusted[index] = min(running, 1.0)
    return adjusted


def merged_label_for_column(worksheet, row: int, column: int) -> str:
    value = worksheet.cell(row=row, column=column).value
    if value is not None:
        return str(value)
    for merged_range in worksheet.merged_cells.ranges:
        if merged_range.min_row <= row <= merged_range.max_row and merged_range.min_col <= column <= merged_range.max_col:
            anchor = worksheet.cell(row=merged_range.min_row, column=merged_range.min_col).value
            return str(anchor) if anchor is not None else ""
    return ""


def extract_genus_table() -> tuple[pd.DataFrame, pd.DataFrame]:
    workbook = openpyxl.load_workbook(WORKBOOK, read_only=False, data_only=True)
    worksheet = workbook["Genus"]
    sample_columns = []
    for column in range(2, worksheet.max_column + 1):
        sample_id = worksheet.cell(row=4, column=column).value
        if sample_id is None:
            continue
        sample_id = str(sample_id).strip()
        if not re.match(r"^\d+[ac]$", sample_id):
            continue
        group_label = merged_label_for_column(worksheet, 3, column)
        clinical_group = "HP" if group_label.startswith("HP") else "SOM" if group_label.startswith("SOM") else ""
        tissue = "adenoid" if sample_id.endswith("a") else "tonsil"
        patient_id = sample_id[:-1]
        sample_name = f"{patient_id}{sample_id[-1]}_{tissue}"
        sample_columns.append(
            {
                "column": column,
                "sample_id": sample_id,
                "sample_name": sample_name,
                "patient_id": patient_id,
                "tissue": tissue,
                "clinical_group": clinical_group,
                "published_group_label": group_label,
            }
        )

    abundance_rows = []
    for row in range(5, worksheet.max_row + 1):
        genus = worksheet.cell(row=row, column=1).value
        if genus is None:
            continue
        genus = str(genus).strip()
        if not genus:
            continue
        for sample in sample_columns:
            value = worksheet.cell(row=row, column=sample["column"]).value
            abundance_rows.append(
                {
                    "sample_name": sample["sample_name"],
                    "sample_id": sample["sample_id"],
                    "genus": genus,
                    "relative_abundance": float(value or 0.0),
                }
            )

    sample_metadata = pd.DataFrame(sample_columns).drop(columns=["column"])
    genus_abundance = pd.DataFrame(abundance_rows)
    return sample_metadata, genus_abundance


def attach_run_metadata(sample_metadata: pd.DataFrame) -> pd.DataFrame:
    run_metadata = pd.read_csv(METADATA_PATH, sep="\t", dtype=str)
    run_metadata = run_metadata[["Run", "BioSample", "SampleName", "Model", "LibraryStrategy"]].rename(
        columns={"Run": "run", "BioSample": "biosample", "SampleName": "sample_name", "Model": "instrument_model"}
    )
    return sample_metadata.merge(run_metadata, on="sample_name", how="left")


def dominant_state(sample_table: pd.DataFrame) -> Dict[str, object]:
    ordered = sample_table.sort_values("relative_abundance", ascending=False)
    top = ordered.iloc[0]
    second = ordered.iloc[1] if len(ordered) > 1 else top
    dominant_genus = str(top["genus"])
    dominant_abundance = float(top["relative_abundance"])
    margin = dominant_abundance - float(second["relative_abundance"])
    if dominant_abundance >= 30:
        state = f"{dominant_genus}_dominant"
    elif dominant_abundance >= 20 and margin >= 10:
        state = f"{dominant_genus}_enriched"
    else:
        state = "mixed"
    return {
        "dominant_genus": dominant_genus,
        "dominant_abundance": dominant_abundance,
        "second_genus": str(second["genus"]),
        "dominance_margin": margin,
        "ecological_state": state,
    }


def summarize_states(sample_metadata: pd.DataFrame, genus_abundance: pd.DataFrame) -> pd.DataFrame:
    state_rows = []
    for sample_name, sample_table in genus_abundance.groupby("sample_name"):
        state_rows.append({"sample_name": sample_name, **dominant_state(sample_table)})
    states = pd.DataFrame(state_rows)
    return sample_metadata.merge(states, on="sample_name", how="left")


def group_effects(sample_metadata: pd.DataFrame, genus_abundance: pd.DataFrame) -> pd.DataFrame:
    wide = genus_abundance.pivot_table(
        index="sample_name", columns="genus", values="relative_abundance", aggfunc="sum", fill_value=0
    )
    annotated = sample_metadata.set_index("sample_name")
    rows = []
    for tissue in ["adenoid", "tonsil"]:
        samples = annotated[annotated["tissue"] == tissue]
        for genus in [g for g in CANDIDATE_GENERA if g in wide.columns]:
            hp = wide.loc[samples[samples["clinical_group"] == "HP"].index, genus]
            som = wide.loc[samples[samples["clinical_group"] == "SOM"].index, genus]
            statistic, p_value = mannwhitneyu(hp, som, alternative="two-sided")
            rows.append(
                {
                    "comparison": f"SOM_vs_HP_within_{tissue}",
                    "genus": genus,
                    "n_hp": len(hp),
                    "n_som": len(som),
                    "median_hp": hp.median(),
                    "median_som": som.median(),
                    "median_difference_som_minus_hp": som.median() - hp.median(),
                    "p_value": p_value,
                    "test": "Mann-Whitney U",
                }
            )
    adjusted = benjamini_hochberg([float(row["p_value"]) for row in rows])
    for row, fdr in zip(rows, adjusted):
        row["fdr"] = fdr
    return pd.DataFrame(rows)


def paired_tissue_effects(sample_metadata: pd.DataFrame, genus_abundance: pd.DataFrame) -> pd.DataFrame:
    wide = genus_abundance.pivot_table(
        index="sample_name", columns="genus", values="relative_abundance", aggfunc="sum", fill_value=0
    )
    annotated = sample_metadata.set_index("sample_name")
    rows = []
    for clinical_group in ["HP", "SOM", "all"]:
        if clinical_group == "all":
            patients = sorted(set(sample_metadata["patient_id"]))
        else:
            patients = sorted(set(sample_metadata.loc[sample_metadata["clinical_group"] == clinical_group, "patient_id"]))
        for genus in [g for g in CANDIDATE_GENERA if g in wide.columns]:
            paired = []
            for patient_id in patients:
                adenoid = f"{patient_id}a_adenoid"
                tonsil = f"{patient_id}c_tonsil"
                if adenoid in wide.index and tonsil in wide.index:
                    paired.append((wide.loc[adenoid, genus], wide.loc[tonsil, genus]))
            if not paired:
                continue
            adenoid_values = pd.Series([item[0] for item in paired])
            tonsil_values = pd.Series([item[1] for item in paired])
            differences = tonsil_values - adenoid_values
            try:
                statistic, p_value = wilcoxon(differences)
            except ValueError:
                statistic, p_value = math.nan, 1.0
            rows.append(
                {
                    "comparison": f"tonsil_minus_adenoid_{clinical_group}",
                    "genus": genus,
                    "n_pairs": len(paired),
                    "median_adenoid": adenoid_values.median(),
                    "median_tonsil": tonsil_values.median(),
                    "median_paired_difference": differences.median(),
                    "p_value": p_value,
                    "test": "Wilcoxon signed-rank",
                }
            )
    adjusted = benjamini_hochberg([float(row["p_value"]) for row in rows])
    for row, fdr in zip(rows, adjusted):
        row["fdr"] = fdr
    return pd.DataFrame(rows)


def state_prevalence_tests(state_table: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for tissue in ["adenoid", "tonsil"]:
        tissue_table = state_table[state_table["tissue"] == tissue]
        for state in sorted(tissue_table["ecological_state"].unique()):
            hp = tissue_table[tissue_table["clinical_group"] == "HP"]
            som = tissue_table[tissue_table["clinical_group"] == "SOM"]
            table = np.array(
                [
                    [(hp["ecological_state"] == state).sum(), (hp["ecological_state"] != state).sum()],
                    [(som["ecological_state"] == state).sum(), (som["ecological_state"] != state).sum()],
                ]
            )
            _, p_value = fisher_exact(table)
            rows.append(
                {
                    "comparison": f"SOM_vs_HP_within_{tissue}",
                    "ecological_state": state,
                    "hp_with_state": int(table[0, 0]),
                    "hp_without_state": int(table[0, 1]),
                    "som_with_state": int(table[1, 0]),
                    "som_without_state": int(table[1, 1]),
                    "p_value": p_value,
                    "test": "Fisher exact",
                }
            )
    adjusted = benjamini_hochberg([float(row["p_value"]) for row in rows]) if rows else []
    for row, fdr in zip(rows, adjusted):
        row["fdr"] = fdr
    return pd.DataFrame(rows)


def permanova(distance_matrix: np.ndarray, labels: List[str], permutations: int = 999, seed: int = 42) -> Dict[str, float]:
    labels = np.asarray(labels)
    unique_labels = np.unique(labels)
    n = len(labels)
    if len(unique_labels) < 2:
        return {"pseudo_f": math.nan, "p_value": math.nan, "permutations": permutations}

    def pseudo_f(current_labels: np.ndarray) -> float:
        squared = distance_matrix**2
        total_ss = squared.sum() / n
        within_ss = 0.0
        for label in np.unique(current_labels):
            index = np.where(current_labels == label)[0]
            if len(index) > 1:
                within_ss += squared[np.ix_(index, index)].sum() / len(index)
        among_ss = total_ss - within_ss
        df_among = len(np.unique(current_labels)) - 1
        df_within = n - len(np.unique(current_labels))
        return (among_ss / df_among) / (within_ss / df_within)

    observed = pseudo_f(labels)
    rng = np.random.default_rng(seed)
    permuted = [pseudo_f(rng.permutation(labels)) for _ in range(permutations)]
    p_value = (sum(value >= observed for value in permuted) + 1) / (permutations + 1)
    return {"pseudo_f": observed, "p_value": p_value, "permutations": permutations}


def beta_tests(sample_metadata: pd.DataFrame, genus_abundance: pd.DataFrame) -> pd.DataFrame:
    wide = genus_abundance.pivot_table(
        index="sample_name", columns="genus", values="relative_abundance", aggfunc="sum", fill_value=0
    )
    annotated = sample_metadata.set_index("sample_name").loc[wide.index]
    distance_matrix = squareform(pdist(wide.to_numpy(), metric="braycurtis"))
    rows = []
    for label_name in ["tissue", "clinical_group"]:
        result = permanova(distance_matrix, annotated[label_name].tolist())
        rows.append({"comparison": label_name, "metric": "Bray-Curtis", **result})
    for tissue in ["adenoid", "tonsil"]:
        subset = annotated[annotated["tissue"] == tissue].index
        subset_matrix = squareform(pdist(wide.loc[subset].to_numpy(), metric="braycurtis"))
        result = permanova(subset_matrix, annotated.loc[subset, "clinical_group"].tolist())
        rows.append({"comparison": f"clinical_group_within_{tissue}", "metric": "Bray-Curtis", **result})
    return pd.DataFrame(rows)


def plot_state_summary(state_table: pd.DataFrame) -> None:
    DIAGNOSTIC_FIGURE_DIR.joinpath("pdf").mkdir(parents=True, exist_ok=True)
    DIAGNOSTIC_FIGURE_DIR.joinpath("png").mkdir(parents=True, exist_ok=True)
    summary = (
        state_table.groupby(["tissue", "clinical_group", "dominant_genus"], dropna=False)
        .size()
        .reset_index(name="n")
    )
    genera = list(summary.groupby("dominant_genus")["n"].sum().sort_values(ascending=False).head(8).index)
    plot_data = summary[summary["dominant_genus"].isin(genera)].copy()
    plot_data["panel"] = plot_data["tissue"] + " / " + plot_data["clinical_group"]
    pivot = plot_data.pivot_table(index="panel", columns="dominant_genus", values="n", aggfunc="sum", fill_value=0)
    pivot = pivot.reindex(columns=genera)

    colors = plt.cm.Set3(np.linspace(0, 1, len(genera)))
    fig, ax = plt.subplots(figsize=(8, 4.5))
    bottom = np.zeros(len(pivot))
    for color, genus in zip(colors, genera):
        values = pivot[genus].to_numpy()
        ax.bar(pivot.index, values, bottom=bottom, label=genus, color=color, edgecolor="white", linewidth=0.6)
        bottom += values
    ax.set_ylabel("Number of samples")
    ax.set_xlabel("")
    ax.set_title("PRJNA422760 dominant genus states by tissue and clinical group")
    ax.tick_params(axis="x", rotation=25)
    ax.legend(frameon=False, bbox_to_anchor=(1.02, 1), loc="upper left")
    fig.tight_layout()
    fig.savefig(DIAGNOSTIC_FIGURE_DIR / "pdf" / "prjna422760_state_transfer_diagnostic.pdf")
    fig.savefig(DIAGNOSTIC_FIGURE_DIR / "png" / "prjna422760_state_transfer_diagnostic.png", dpi=300)
    plt.close(fig)


def write_interpretation(
    state_table: pd.DataFrame,
    group_df: pd.DataFrame,
    paired_df: pd.DataFrame,
    beta_df: pd.DataFrame,
    state_tests: pd.DataFrame,
) -> None:
    top_group = group_df.sort_values("fdr").head(6)
    top_paired = paired_df.sort_values("fdr").head(6)
    state_counts = state_table["dominant_genus"].value_counts().head(8)
    lines = [
        "# PRJNA422760 Phenotype-Transfer Analysis",
        "",
        "Generated: 2026-05-24",
        "",
        "## Design Use",
        "`PRJNA422760` is used as a pediatric ENT phenotype-transfer cohort, not as direct sinusitis replication. The usable public labels are tissue site, patient-paired adenoid/tonsil sampling, and published HP/SOM group assignments from the supplementary genus table.",
        "",
        "## Sample Support",
        f"- Samples analyzed: {len(state_table)}.",
        f"- Patients with paired adenoid/tonsil samples: {state_table['patient_id'].nunique()}.",
        f"- Clinical groups: {', '.join(f'{k}={v}' for k, v in state_table['clinical_group'].value_counts().sort_index().items())}.",
        f"- Dominant genera most often observed: {', '.join(f'{k} ({v})' for k, v in state_counts.items())}.",
        "",
        "## Statistical Readout",
        "- Bray-Curtis PERMANOVA is reported for tissue and HP/SOM labels, with within-tissue HP/SOM tests to avoid treating paired tissues as one endpoint.",
        "- Candidate-genera tests are non-parametric and FDR-adjusted. They are descriptive external-transfer evidence, not mechanistic validation.",
        "",
        "## Strongest HP/SOM Genus-Level Contrasts",
        "| Comparison | Genus | Median HP | Median SOM | Difference | FDR |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for _, row in top_group.iterrows():
        lines.append(
            f"| {row['comparison']} | {row['genus']} | {row['median_hp']:.3f} | {row['median_som']:.3f} | {row['median_difference_som_minus_hp']:.3f} | {row['fdr']:.4f} |"
        )
    lines.extend(
        [
            "",
            "## Strongest Paired Tissue Contrasts",
            "| Comparison | Genus | Median Adenoid | Median Tonsil | Paired Difference | FDR |",
            "| --- | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for _, row in top_paired.iterrows():
        lines.append(
            f"| {row['comparison']} | {row['genus']} | {row['median_adenoid']:.3f} | {row['median_tonsil']:.3f} | {row['median_paired_difference']:.3f} | {row['fdr']:.4f} |"
        )
    lines.extend(
        [
            "",
            "## Output Files",
            "- `data/processed/prjna422760_sample_metadata.tsv`",
            "- `data/processed/prjna422760_genus_abundance.tsv`",
            "- `results/replication/prjna422760_state_summary.tsv`",
            "- `results/replication/prjna422760_group_effects.tsv`",
            "- `results/replication/prjna422760_paired_tissue_effects.tsv`",
            "- `results/replication/prjna422760_beta_tests.tsv`",
            "- `results/replication/prjna422760_state_prevalence_tests.tsv`",
            "- `plots/diagnostic/pdf/prjna422760_state_transfer_diagnostic.pdf`",
            "",
            "## Claim Boundary",
            "This module supports recurrence and clinical transportability of interpretable upper-airway ecological states across a pediatric ENT tissue cohort. It does not establish causality, a shared mechanism across diseases, or diagnostic readiness.",
        ]
    )
    (ROOT / "docs" / "PRJNA422760_TRANSFER_ANALYSIS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    sample_metadata, genus_abundance = extract_genus_table()
    sample_metadata = attach_run_metadata(sample_metadata)
    state_table = summarize_states(sample_metadata, genus_abundance)
    group_df = group_effects(sample_metadata, genus_abundance)
    paired_df = paired_tissue_effects(sample_metadata, genus_abundance)
    beta_df = beta_tests(sample_metadata, genus_abundance)
    state_tests = state_prevalence_tests(state_table)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    sample_metadata.to_csv(PROCESSED_DIR / "prjna422760_sample_metadata.tsv", sep="\t", index=False)
    genus_abundance.to_csv(PROCESSED_DIR / "prjna422760_genus_abundance.tsv", sep="\t", index=False)
    state_table.to_csv(RESULTS_DIR / "prjna422760_state_summary.tsv", sep="\t", index=False)
    group_df.to_csv(RESULTS_DIR / "prjna422760_group_effects.tsv", sep="\t", index=False)
    paired_df.to_csv(RESULTS_DIR / "prjna422760_paired_tissue_effects.tsv", sep="\t", index=False)
    beta_df.to_csv(RESULTS_DIR / "prjna422760_beta_tests.tsv", sep="\t", index=False)
    state_tests.to_csv(RESULTS_DIR / "prjna422760_state_prevalence_tests.tsv", sep="\t", index=False)

    combined = pd.DataFrame(
        [
            {
                "dataset_id": "PRJNA422760",
                "role": "phenotype_transfer",
                "n_samples": len(state_table),
                "n_independent_patients": state_table["patient_id"].nunique(),
                "usable_label": "paired adenoid/tonsil tissue and HP/SOM group",
                "primary_readout": "genus-level ecological state transfer",
                "decision": "include_descriptive_external_transfer",
            }
        ]
    )
    combined.to_csv(RESULTS_DIR / "combined_summary.tsv", sep="\t", index=False)

    plot_state_summary(state_table)
    write_interpretation(state_table, group_df, paired_df, beta_df, state_tests)
    print("Wrote PRJNA422760 phenotype-transfer outputs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
