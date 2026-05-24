# Pediatric upper-airway microbial states and sinusitis

This repository contains the reproducible analysis code and derived outputs for a public-data study of pediatric upper-airway microbial states in relation to sinusitis-associated profiles. It is intentionally limited to computational reproduction materials: scripts, public data manifests, derived result tables, and exported figures.

## What this repository contains

- `scripts/`: data acquisition, analysis, and figure-generation scripts.
- `data/manifest.tsv`: public data sources and stable accession identifiers.
- `docs/DATA_MANIFEST.tsv`: reviewer-facing copy of the public data manifest.
- `docs/FIGURE_PROVENANCE.tsv`: figure-to-script and figure-to-table provenance.
- `docs/STATISTICAL_DECISION_RULES.md`: thresholds, multiplicity handling, and interpretation boundaries.
- `results/`: lightweight derived tables used as figure and table anchors.
- `plots/publication/`: exported publication figures in PDF and PNG formats.

This repository does not contain manuscript drafts, submission files, internal planning notes, or credentials.

## Public datasets

The default pipeline uses public metadata and processed companion data rather than raw FASTQ reprocessing.

- `PRJEB35160`: primary pediatric nasopharyngeal 16S rRNA cohort with URI/sinusitis annotations.
- `PRJNA422760`: paired pediatric adenoid/tonsil 16S rRNA cohort used for anatomical-context analysis.
- Additional public accessions are listed in `data/manifest.tsv` for dataset screening and context.

## Environment

The analysis was run with:

- Python 3.13.7
- R 4.4.3

Install Python dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Install R dependencies:

```r
install.packages(c("dplyr", "readr", "ggplot2", "lme4", "vegan"))
if (!requireNamespace("BiocManager", quietly = TRUE)) install.packages("BiocManager")
BiocManager::install("phyloseq")
```

## Reproduce the analysis

Run the full lightweight workflow from the repository root:

```bash
bash scripts/reproduce_one_click.sh
```

The script downloads public metadata and processed companion artifacts, runs the primary and anatomical-context analyses, and regenerates the publication figures.

For faster testing, use fewer permutations and bootstrap iterations:

```bash
PERMUTATIONS=9 BOOTSTRAP_ITERATIONS=10 bash scripts/reproduce_one_click.sh
```

## Expected outputs

Key derived tables are written under:

- `results/primary/`
- `results/effect_sizes/`
- `results/replication/`
- `results/figures/`
- `results/tables/`

Publication figures are written under:

- `plots/publication/pdf/`
- `plots/publication/png/`

The default lightweight workflow does not download raw FASTQ files. Full raw-read reprocessing is not required to reproduce the reported tables and figures.
