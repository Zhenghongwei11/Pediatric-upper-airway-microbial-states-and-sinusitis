# Compute plan

## Default workflow

The default workflow runs on a recent laptop after dependencies are installed. It acquires a pinned public primary processed object, a published supplementary abundance workbook, and current public run metadata. It does not download or reprocess raw FASTQ reads.

The analysis performs 2,000 whole-child bootstrap draws and 9,999 restricted permutations for each external-cohort comparison. Figure rendering and construction of the main and supplementary tables follow the analysis stages.

Expected resources are under 30 minutes of compute time after installation, under 8 GB of peak memory, and under 2 GB for downloaded inputs and generated results. These are planning estimates; network speed and processor performance affect elapsed time. Installing Python and R dependencies requires additional disk space.

## Inputs and scope

The primary cohort uses the public `AnalysisPhyloseq.rds` object pinned to a source repository commit. The anatomical cohort uses published PRJNA422760 genus percentages and NCBI RunInfo metadata. SHA-256 checksums are verified for the pinned RDS object, workbook, and derived input tables where stable checksums are available. Live RunInfo is checked for expected sample identity and count; its source response can change over time.

The workflow reproduces the reported tables and figures from these public processed inputs. Raw-read quality control, denoising, and taxonomic assignment are outside the workflow.

## Outputs

The pipeline writes analysis tables to `results/primary/` and `results/external/`, main tables to `results/tables/`, supplementary tables to `results/supplementary/`, and publication figures to `plots/publication/`. It also writes figure and table provenance records under `docs/`.
