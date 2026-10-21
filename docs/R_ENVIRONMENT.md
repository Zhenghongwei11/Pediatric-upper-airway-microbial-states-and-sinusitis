# R environment

The analysis environment uses R 4.4.3 with Bioconductor 3.20. Direct package versions are:

| Package | Version | Source |
| --- | --- | --- |
| phyloseq | 1.50.0 | Bioconductor 3.20 |
| readr | 2.1.5 | CRAN |
| vegan | 2.7-1 | CRAN |
| permute | 0.9-8 | CRAN; dependency of vegan |

Install the exact versions with:

```bash
Rscript scripts/install_r_dependencies.R
```

The script checks the R version, installs or restores the listed package versions, and stops if the resulting environment does not match. `phyloseq` is installed from the Bioconductor 3.20 release corresponding to R 4.4. Python package versions are pinned separately in `requirements.txt`.
