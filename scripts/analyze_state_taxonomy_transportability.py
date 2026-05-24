#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, Iterable, List

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

PRJEB35160_METADATA = ROOT / "data" / "processed" / "prjeb35160_sample_metadata.tsv"
PRJNA422760_STATE_SUMMARY = ROOT / "results" / "replication" / "prjna422760_state_summary.tsv"

RESULTS_REPLICATION = ROOT / "results" / "replication"
RESULTS_EFFECTS = ROOT / "results" / "effect_sizes"
RESULTS_FIGURES = ROOT / "results" / "figures"
DOCS_DIR = ROOT / "docs"


STATE_DEFINITIONS = [
    {
        "state_label": "Moraxella-dominant state",
        "state_key": "moraxella_dominant",
        "primary_genera": "Moraxella",
        "dominance_rule": "Dominant genus is Moraxella and the dominant-genus fraction is at least 30%.",
        "clinical_interpretation": "Pathobiont-dominant upper-airway state linked to sinusitis-associated profiles in the endpoint cohort.",
        "forbidden_overclaim": "Do not describe as a diagnostic marker, causal mechanism, or treatment-selection rule.",
        "display_order": 1,
    },
    {
        "state_label": "Haemophilus-dominant state",
        "state_key": "haemophilus_dominant",
        "primary_genera": "Haemophilus",
        "dominance_rule": "Dominant genus is Haemophilus and the dominant-genus fraction is at least 30%.",
        "clinical_interpretation": "Recognizable pediatric airway pathobiont state; interpreted as a comparator state rather than a primary sinusitis signal.",
        "forbidden_overclaim": "Do not infer a Haemophilus-specific sinusitis mechanism from these public data.",
        "display_order": 2,
    },
    {
        "state_label": "Streptococcus-dominant state",
        "state_key": "streptococcus_dominant",
        "primary_genera": "Streptococcus",
        "dominance_rule": "Dominant genus is Streptococcus and the dominant-genus fraction is at least 30%.",
        "clinical_interpretation": "Common upper-airway state useful for cross-cohort ecological context.",
        "forbidden_overclaim": "Do not treat as disease-specific without endpoint-level support.",
        "display_order": 3,
    },
    {
        "state_label": "Fusobacterium/anaerobe-dominant state",
        "state_key": "anaerobe_dominant",
        "primary_genera": "Fusobacterium;Porphyromonas;Prevotella;Alloprevotella",
        "dominance_rule": "Dominant genus is a recognized anaerobe-associated oral/ENT genus and the dominant-genus fraction is at least 30%.",
        "clinical_interpretation": "Adenoid/tonsil-relevant anaerobe-enriched state; mainly supports anatomical phenotype-transfer interpretation.",
        "forbidden_overclaim": "Do not interpret as sinusitis replication or anaerobic infection diagnosis.",
        "display_order": 4,
    },
    {
        "state_label": "Neisseria-dominant state",
        "state_key": "neisseria_dominant",
        "primary_genera": "Neisseria",
        "dominance_rule": "Dominant genus is Neisseria and the dominant-genus fraction is at least 30%.",
        "clinical_interpretation": "Upper-airway commensal/pathobiont state used for ecological transportability.",
        "forbidden_overclaim": "Do not describe as protective or harmful without dedicated clinical evidence.",
        "display_order": 5,
    },
    {
        "state_label": "Other-dominant state",
        "state_key": "other_dominant",
        "primary_genera": "Other named dominant genus",
        "dominance_rule": "Dominant-genus fraction is at least 30%, but the dominant genus is outside the pre-specified state genera.",
        "clinical_interpretation": "Named but cohort-specific state kept to avoid forcing all samples into a pathobiont category.",
        "forbidden_overclaim": "Do not use as a clinical subgroup without sufficient sample support.",
        "display_order": 6,
    },
    {
        "state_label": "Mixed community state",
        "state_key": "mixed",
        "primary_genera": "No single dominant genus",
        "dominance_rule": "Dominant-genus fraction is below 30% or a sample is already classified as mixed in the source table.",
        "clinical_interpretation": "No single-genus dominance; used as a conservative comparator state.",
        "forbidden_overclaim": "Do not equate mixed state with health or normality without cohort-specific controls.",
        "display_order": 7,
    },
]

ANAEROBE_GENERA = {"Fusobacterium", "Porphyromonas", "Prevotella", "Alloprevotella"}
PRIMARY_STATE_GENERA = {"Moraxella", "Haemophilus", "Streptococcus", "Neisseria"} | ANAEROBE_GENERA
STATE_LABEL_BY_KEY = {row["state_key"]: row["state_label"] for row in STATE_DEFINITIONS}


def format_subject_id(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value)
    return text[:-2] if text.endswith(".0") else text


def write_tsv(path: Path, rows: List[Dict[str, object]], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def state_key_for(dominant_genus: object, dominant_fraction_percent: float, source_state: str | None = None) -> str:
    if source_state and source_state == "mixed":
        return "mixed"
    if pd.isna(dominant_genus) or dominant_fraction_percent < 30:
        return "mixed"
    genus = str(dominant_genus)
    if genus == "Moraxella":
        return "moraxella_dominant"
    if genus == "Haemophilus":
        return "haemophilus_dominant"
    if genus == "Streptococcus":
        return "streptococcus_dominant"
    if genus == "Neisseria":
        return "neisseria_dominant"
    if genus in ANAEROBE_GENERA:
        return "anaerobe_dominant"
    return "other_dominant"


def load_prjeb35160_states() -> pd.DataFrame:
    metadata = pd.read_csv(PRJEB35160_METADATA, sep="\t")
    analysis = metadata[metadata["outcome_group"].isin(["URI", "Sinusitis"])].copy()
    analysis["dominant_fraction_percent"] = pd.to_numeric(analysis["dominant_genus_fraction"], errors="coerce") * 100
    analysis["state_key"] = analysis.apply(
        lambda row: state_key_for(row["dominant_genus"], row["dominant_fraction_percent"]),
        axis=1,
    )
    analysis["state_label"] = analysis["state_key"].map(STATE_LABEL_BY_KEY)
    analysis["dataset_id"] = "PRJEB35160"
    analysis["cohort_role"] = "Endpoint-discovery"
    analysis["subject_id"] = analysis["child_id"].map(format_subject_id)
    analysis["sample_context"] = "Nasopharyngeal URI/sinusitis profile"
    analysis["clinical_group"] = analysis["outcome_group"]
    analysis["clinical_positive"] = analysis["outcome_group"].eq("Sinusitis").astype(int)
    return analysis[
        [
            "dataset_id",
            "cohort_role",
            "sample_id",
            "subject_id",
            "sample_context",
            "clinical_group",
            "clinical_positive",
            "dominant_genus",
            "dominant_fraction_percent",
            "state_key",
            "state_label",
        ]
    ]


def load_prjna422760_states() -> pd.DataFrame:
    metadata = pd.read_csv(PRJNA422760_STATE_SUMMARY, sep="\t")
    metadata["dominant_fraction_percent"] = pd.to_numeric(metadata["dominant_abundance"], errors="coerce")
    metadata["state_key"] = metadata.apply(
        lambda row: state_key_for(row["dominant_genus"], row["dominant_fraction_percent"], row.get("ecological_state")),
        axis=1,
    )
    metadata["state_label"] = metadata["state_key"].map(STATE_LABEL_BY_KEY)
    metadata["dataset_id"] = "PRJNA422760"
    metadata["cohort_role"] = "Phenotype-transfer"
    metadata["subject_id"] = metadata["patient_id"].astype(str)
    metadata["sample_context"] = metadata["tissue"].str.capitalize() + " tissue profile"
    metadata["clinical_positive"] = metadata["clinical_group"].eq("SOM").astype(int)
    return metadata[
        [
            "dataset_id",
            "cohort_role",
            "sample_name",
            "subject_id",
            "sample_context",
            "clinical_group",
            "clinical_positive",
            "dominant_genus",
            "dominant_fraction_percent",
            "state_key",
            "state_label",
        ]
    ].rename(columns={"sample_name": "sample_id"})


def summarize_states(combined_states: pd.DataFrame) -> pd.DataFrame:
    rows = []
    grouped = combined_states.groupby(["dataset_id", "cohort_role", "state_key", "state_label"], dropna=False)
    for (dataset_id, cohort_role, state_key, state_label), state_table in grouped:
        total_dataset_samples = len(combined_states[combined_states["dataset_id"] == dataset_id])
        clinical_positive_count = int(state_table["clinical_positive"].sum())
        rows.append(
            {
                "dataset_id": dataset_id,
                "cohort_role": cohort_role,
                "state_label": state_label,
                "state_key": state_key,
                "n_profiles": len(state_table),
                "n_subjects": state_table["subject_id"].nunique(),
                "profile_fraction": round(len(state_table) / total_dataset_samples, 4),
                "clinical_positive_profiles": clinical_positive_count,
                "clinical_positive_fraction": round(clinical_positive_count / len(state_table), 4) if len(state_table) else 0,
                "median_dominant_fraction_percent": round(state_table["dominant_fraction_percent"].median(), 3),
            }
        )
    output = pd.DataFrame(rows)
    order_map = {row["state_key"]: row["display_order"] for row in STATE_DEFINITIONS}
    output["display_order"] = output["state_key"].map(order_map)
    return output.sort_values(["display_order", "dataset_id"]).drop(columns=["display_order"])


def build_transportability(state_summary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for definition in STATE_DEFINITIONS:
        state_key = definition["state_key"]
        state_rows = state_summary[state_summary["state_key"] == state_key]
        prjeb_row = state_rows[state_rows["dataset_id"] == "PRJEB35160"]
        prjna_row = state_rows[state_rows["dataset_id"] == "PRJNA422760"]
        prjeb_present = not prjeb_row.empty
        prjna_present = not prjna_row.empty
        rows.append(
            {
                "state_label": definition["state_label"],
                "primary_genera": definition["primary_genera"],
                "present_in_prjeb35160": "yes" if prjeb_present else "no",
                "present_in_prjna422760": "yes" if prjna_present else "no",
                "prjeb35160_profile_fraction": float(prjeb_row["profile_fraction"].iloc[0]) if prjeb_present else 0.0,
                "prjna422760_profile_fraction": float(prjna_row["profile_fraction"].iloc[0]) if prjna_present else 0.0,
                "transportability_interpretation": transportability_interpretation(
                    definition["state_label"], prjeb_present, prjna_present
                ),
            }
        )
    return pd.DataFrame(rows)


def transportability_interpretation(state_label: str, prjeb_present: bool, prjna_present: bool) -> str:
    if prjeb_present and prjna_present:
        return "Observed in both cohorts; supports descriptive ecological-state transportability."
    if prjeb_present:
        return "Observed in endpoint-discovery cohort only; not externally transported in the paired ENT tissue table."
    if prjna_present:
        return "Observed in phenotype-transfer cohort only; interpreted as anatomical or cohort-specific context."
    return "Not observed under the current dominance threshold."


def child_level_burden(prjeb_states: pd.DataFrame) -> pd.DataFrame:
    state_counts = (
        prjeb_states.groupby(["subject_id", "state_label"]).size().reset_index(name="state_profiles")
    )
    predominant = (
        state_counts.sort_values(["subject_id", "state_profiles", "state_label"], ascending=[True, False, True])
        .drop_duplicates("subject_id")
        .rename(columns={"state_label": "predominant_child_state", "state_profiles": "predominant_state_profiles"})
    )
    rows = []
    for subject_id, child_table in prjeb_states.groupby("subject_id"):
        profile_count = len(child_table)
        sinusitis_count = int(child_table["clinical_positive"].sum())
        moraxella_count = int(child_table["state_key"].eq("moraxella_dominant").sum())
        haemophilus_count = int(child_table["state_key"].eq("haemophilus_dominant").sum())
        streptococcus_count = int(child_table["state_key"].eq("streptococcus_dominant").sum())
        rows.append(
            {
                "dataset_id": "PRJEB35160",
                "child_id": subject_id,
                "n_profiles": profile_count,
                "n_sinusitis_profiles": sinusitis_count,
                "sinusitis_profile_fraction": round(sinusitis_count / profile_count, 4),
                "n_moraxella_dominant_profiles": moraxella_count,
                "moraxella_dominant_profile_fraction": round(moraxella_count / profile_count, 4),
                "n_haemophilus_dominant_profiles": haemophilus_count,
                "haemophilus_dominant_profile_fraction": round(haemophilus_count / profile_count, 4),
                "n_streptococcus_dominant_profiles": streptococcus_count,
                "streptococcus_dominant_profile_fraction": round(streptococcus_count / profile_count, 4),
                "ever_sinusitis": "yes" if sinusitis_count > 0 else "no",
                "any_moraxella_dominant": "yes" if moraxella_count > 0 else "no",
            }
        )
    child_table = pd.DataFrame(rows).merge(
        predominant[["subject_id", "predominant_child_state", "predominant_state_profiles"]],
        left_on="child_id",
        right_on="subject_id",
        how="left",
    ).drop(columns=["subject_id"])
    child_table["predominant_child_state_fraction"] = (
        child_table["predominant_state_profiles"] / child_table["n_profiles"]
    ).round(4)
    return child_table.sort_values("child_id")


def child_burden_summary(child_table: pd.DataFrame) -> pd.DataFrame:
    grouped = child_table.groupby("ever_sinusitis")
    rows = []
    for ever_sinusitis, group_table in grouped:
        rows.append(
            {
                "dataset_id": "PRJEB35160",
                "child_group": f"ever_sinusitis_{ever_sinusitis}",
                "n_children": len(group_table),
                "median_profiles_per_child": group_table["n_profiles"].median(),
                "median_sinusitis_profile_fraction": group_table["sinusitis_profile_fraction"].median(),
                "median_moraxella_dominant_profile_fraction": group_table["moraxella_dominant_profile_fraction"].median(),
                "children_with_any_moraxella_dominant": int(group_table["any_moraxella_dominant"].eq("yes").sum()),
            }
        )
    rows.append(
        {
            "dataset_id": "PRJEB35160",
            "child_group": "all_analyzable_children",
            "n_children": len(child_table),
            "median_profiles_per_child": child_table["n_profiles"].median(),
            "median_sinusitis_profile_fraction": child_table["sinusitis_profile_fraction"].median(),
            "median_moraxella_dominant_profile_fraction": child_table["moraxella_dominant_profile_fraction"].median(),
            "children_with_any_moraxella_dominant": int(child_table["any_moraxella_dominant"].eq("yes").sum()),
        }
    )
    return pd.DataFrame(rows)


def write_docs(taxonomy: pd.DataFrame, transportability: pd.DataFrame, child_summary: pd.DataFrame) -> None:
    taxonomy_lines = [
        "# Upper-Airway Ecological-State Taxonomy",
        "",
        "Generated: 2026-05-24",
        "",
        "This taxonomy is a descriptive clinical framework for public pediatric upper-airway microbiome data. It is not a mechanistic classification, diagnostic model, or treatment rule.",
        "",
        "| State | Dominance Rule | Clinical Interpretation | Forbidden Overclaim |",
        "| --- | --- | --- | --- |",
    ]
    for _, row in taxonomy.sort_values("display_order").iterrows():
        taxonomy_lines.append(
            f"| {row['state_label']} | {row['dominance_rule']} | {row['clinical_interpretation']} | {row['forbidden_overclaim']} |"
        )
    (DOCS_DIR / "STATE_TAXONOMY.md").write_text("\n".join(taxonomy_lines) + "\n", encoding="utf-8")

    transport_lines = [
        "# State Transportability Summary",
        "",
        "Generated: 2026-05-24",
        "",
        "`PRJEB35160` is the endpoint-discovery cohort. `PRJNA422760` is an external pediatric ENT phenotype-transfer cohort. Transportability means that the same descriptive state label is observable and interpretable across cohorts; it does not mean sinusitis replication.",
        "",
        "| State | PRJEB35160 | PRJNA422760 | Interpretation |",
        "| --- | ---: | ---: | --- |",
    ]
    for _, row in transportability.iterrows():
        transport_lines.append(
            f"| {row['state_label']} | {row['prjeb35160_profile_fraction']:.3f} | {row['prjna422760_profile_fraction']:.3f} | {row['transportability_interpretation']} |"
        )
    transport_lines.extend(
        [
            "",
            "## Child-Level Context",
            f"Among analyzable `PRJEB35160` children, the median Moraxella-dominant profile fraction was {child_summary.loc[child_summary['child_group'] == 'all_analyzable_children', 'median_moraxella_dominant_profile_fraction'].iloc[0]:.3f}. This child-level view is used to avoid interpreting repeated profiles as independent children.",
        ]
    )
    (DOCS_DIR / "STATE_TRANSPORTABILITY.md").write_text("\n".join(transport_lines) + "\n", encoding="utf-8")


def main() -> int:
    taxonomy = pd.DataFrame(STATE_DEFINITIONS)
    prjeb_states = load_prjeb35160_states()
    prjna_states = load_prjna422760_states()
    combined_states = pd.concat([prjeb_states, prjna_states], ignore_index=True)
    state_summary = summarize_states(combined_states)
    transportability = build_transportability(state_summary)
    child_table = child_level_burden(prjeb_states)
    child_summary = child_burden_summary(child_table)

    RESULTS_REPLICATION.mkdir(parents=True, exist_ok=True)
    RESULTS_EFFECTS.mkdir(parents=True, exist_ok=True)
    RESULTS_FIGURES.mkdir(parents=True, exist_ok=True)

    taxonomy.to_csv(RESULTS_REPLICATION / "state_taxonomy_definitions.tsv", sep="\t", index=False)
    combined_states.to_csv(RESULTS_REPLICATION / "harmonized_state_assignments.tsv", sep="\t", index=False)
    state_summary.to_csv(RESULTS_REPLICATION / "state_taxonomy_summary.tsv", sep="\t", index=False)
    transportability.to_csv(RESULTS_REPLICATION / "state_transportability.tsv", sep="\t", index=False)
    transportability.to_csv(RESULTS_FIGURES / "figure4_state_transportability.tsv", sep="\t", index=False)
    child_table.to_csv(RESULTS_EFFECTS / "prjeb35160_child_state_burden.tsv", sep="\t", index=False)
    child_summary.to_csv(RESULTS_EFFECTS / "prjeb35160_child_state_burden_summary.tsv", sep="\t", index=False)
    write_docs(taxonomy, transportability, child_summary)

    print("Wrote harmonized state taxonomy, transportability, and child-level burden outputs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
