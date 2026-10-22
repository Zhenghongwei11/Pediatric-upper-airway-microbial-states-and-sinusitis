# Pediatric upper-airway microbial states and sinusitis

This repository contains the code and derived outputs for a reproducible analysis of public pediatric airway microbiome data. It rebuilds the five publication figures, main Tables 1–3, and supplementary Tables S1–S7 from public processed inputs.

## Reproduce

The complete entrypoint is:

```bash
bash scripts/reproduce_one_click.sh
```

It is equivalent to `make all`. The workflow downloads the pinned primary phyloseq object, the public PRJNA422760 supplementary workbook, and current NCBI RunInfo metadata. It verifies fixed-source checksums where applicable, prepares the external-cohort input tables, runs both cohort analyses, and generates all figures and tables. Outputs are written under `results/` and `plots/publication/`.

The workflow uses public processed data and published abundance percentages. It does not download or reprocess raw FASTQ reads, perform sequence quality control, or infer clinical labels from sequencing data. The primary outcome is the source-defined child follow-up group; it is not a visit-specific diagnosis or a prospective risk endpoint. The secondary analyses are exploratory and observational.

## Environment

Use Python 3.13.7 and R 4.4.3. Install Python packages from the pinned requirements file and install the pinned R packages with:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
Rscript scripts/install_r_dependencies.R
```

The R installation script checks the R version and installs `phyloseq` 1.50.0, `readr` 2.1.5, and `vegan` 2.7-1, with `permute` 0.9-8. See [R_ENVIRONMENT.md](docs/R_ENVIRONMENT.md) for version and installation details.

## Outputs

- `results/primary/` and `results/external/`: analysis tables, diagnostics, and run provenance.
- `results/tables/`: main Tables 1–3. The historical dataset-screen input is `docs/DATASET_SCREEN_FLOW.tsv`.
- `results/supplementary/`: supplementary Tables S1–S7 in XLSX and Markdown formats.
- `plots/publication/pdf/` and `plots/publication/png/`: Figures 1–5.
- `docs/FIGURE_PROVENANCE.tsv` and `docs/TABLE_PROVENANCE.tsv`: source-table and script mapping for each figure and table.

Table 1 summarizes sex and released initial age once per independent primary-cohort child, using the model membership and public metadata. Main table display values are rounded for readability; the TSV analysis outputs retain their recorded precision. The supplementary workbook retains the precision available in its source tables.

## Analysis methods

The primary analysis uses child-cluster robust inference, whole-child bootstrap intervals, defined threshold sensitivities, and independent-child community comparisons. The paired anatomical cohort uses patient-restricted permutations and paired genus comparisons. The endpoint definition, model specification, multiplicity families, seeds, and interpretation limits are documented in [STATISTICAL_DECISION_RULES.md](docs/STATISTICAL_DECISION_RULES.md).

The analysis was not prospectively registered. The primary model omits tobacco exposure because the available data contain only one exposed child, with no exposed child in the sinusitis-associated group; this produces separation and does not support a finite conventional coefficient. The package reports this support limitation and a restricted sensitivity analysis. Viral count is measured concurrently and is used only in a sensitivity model.

## Expected resources

After dependencies are installed, the default run is expected to take under 30 minutes on a recent laptop, excluding network transfer. Peak memory is expected to remain below 8 GB, and downloaded inputs plus generated outputs should require less than 2 GB of disk space. Bootstrap and permutation stages dominate runtime; actual time varies with CPU and network speed.

## Citation

Please cite the exact archived software version and the associated study using the metadata in [CITATION.cff](CITATION.cff).
