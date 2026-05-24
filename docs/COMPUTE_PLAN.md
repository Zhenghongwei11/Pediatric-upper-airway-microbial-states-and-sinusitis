# Compute plan

## Default workflow

The default workflow is designed for a laptop. It uses public run metadata, public supplementary files, and small processed companion artifacts. It does not download raw FASTQ files.

Expected local requirements:

- runtime: usually under 30 minutes after dependencies are installed;
- memory: typically below 8 GB RAM;
- storage: below 2 GB for the lightweight workflow.

## Optional raw-read reprocessing

Full raw-read reprocessing is outside the default reproduction path. If performed, it should use a separate documented workflow with sufficient temporary storage and an established 16S pipeline such as QIIME2 or DADA2.
