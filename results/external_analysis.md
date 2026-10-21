# PRJNA422760 patient-aware external analysis

This exploratory external analysis concerns paired adenoid/tonsil tissue ecology and the published HP/SOM groups. It does not provide a comparable sinusitis outcome or direct disease replication.

## Data and labels

There are 56 sequencing profiles from 28 children aged 15–65 months (Table 1), with one adenoid and one palatine-tonsil profile per child. HP and SOM each contain 14 children (28 profiles), with 14 children per group within each tissue. Patient-level group labels are constant. HP means hyperplasia group: significant palatine-tonsil and/or adenoid lymphoid hyperplasia with obstructive symptoms, without acute otitis media (AOM) or SOM in the preceding year. SOM means secretory otitis media, verified by middle-ear fluid, tympanometry, paracentesis and ENT clinical evaluation. No child had an acute infection at sampling. The source reports 112 eligible collected specimens because each child provided separate sequencing and culture specimens at both tissue sites; these are distinct from the 56 sequencing profiles analyzed here. Source: doi:10.1128/mSystems.00169-18, Table 1 and Subjects and Sample collection.

The table contains 79 distinct reported genus columns after summing the two source Fusobacterium rows. The duplicate source rows are exported; all statistics and classifications use the same genus aggregation. The original Genus sheet header explicitly says sequences not classified to genus level are not shown. Per-sample sums range from 93.401379% to 100.000000% (median 100.000000%). Published percentages are preserved for all abundance comparisons, classifications and Bray–Curtis distances. There is no renormalization or imputation of the unreported fraction; the missing fraction cannot safely be assigned to a named genus. The dominant reported genus therefore concerns the supplied genus table, not independently reprocessed reads.

## Classification

A single reported genus with maximum percentage at least the threshold defines dominance (25%, 30%, and 50% are exported; 30% is the working definition). Exact ties are resolved lexicographically by genus name and are flagged. An unclassified/unknown/uncultured-prefix, empty or missing top genus is mixed; a named maximum below threshold is mixed. Moraxella, Haemophilus, Streptococcus and Neisseria are separate states. A highest single genus in Fusobacterium/Porphyromonas/Prevotella/Alloprevotella defines the anaerobe state; these genera are never pooled to reach the threshold. Remaining named dominant genera are other.

## Community tests and exchangeability

The tissue PERMANOVA fits patient + tissue, testing the one-degree-of-freedom tissue term after patient (27 residual degrees of freedom). Patient effects account for the paired design. Labels swap independently within each of 28 pairs. Group tests fit HP/SOM separately in each tissue (28 independent patients; 26 residual degrees of freedom), holding group sizes at 14/14. The group comparison assumes patients are exchangeable under the null; diagnosis is observational, so unmeasured confounding and enrollment differences remain possible. Tissue swaps assume the two tissue profiles within a patient are exchangeable under the no-tissue-effect null.

Each test uses 9,999 distinct randomly sampled label allocations excluding the observed allocation. All allocations change the tested label; pair restrictions and group counts are checked. Seeds are 20261020 (tissue), 20261021 (adenoid group) and 20261022 (tonsil group). Monte Carlo P = (1 + number of permuted statistics at least observed)/(9999 + 1), with 1e-12 numerical tolerance. Distinct labels need not yield distinct statistics; the exported count records this distinction. R² is term SS / total SS; partial R² for tissue divides by total SS minus patient SS. Raw and BH P values across the three community tests are supplied.

| Comparison | F | Total R² | Partial R² | P | BH P |
| --- | ---: | ---: | ---: | ---: | ---: |
| tissue_paired_all | 6.507402 | 0.063308 | 0.194208 | 0.0001 | 0.0003 |
| HP_vs_SOM_adenoid | 2.204450 | 0.078160 | 0.078160 | 0.0380 | 0.0570 |
| HP_vs_SOM_tonsil | 1.436816 | 0.052368 | 0.052368 | 0.1854 | 0.1854 |

The paired tissue contrast supports a tissue-associated compositional difference. The adenoid HP/SOM comparison has raw P=0.0380 and BH P=0.0570 across the three community tests; its dispersion diagnostic also differs (raw P=0.0095). It therefore does not cleanly establish a group difference in community centroid. The tonsil comparison remains uncertain (P=0.1854). None of the 18 individual genus HP/SOM contrasts survives its BH family (minimum BH P=0.1617).

## Dispersion diagnostic

PERMDISP uses Euclidean principal coordinates after Lingoes correction of the squared Bray–Curtis distances, retaining every positive axis; constants and the original negative eigenvalue mass are exported. Distances to the observed group centroid are multiplied by sqrt(n/(n−1)) for finite-group bias adjustment. The null is tested by permuting fixed centroid-distance residuals: within-patient swaps for tissue, and independent-patient permutations separately within each tissue for HP/SOM. Tissue uses squared paired t (equivalently F with 1 and 27 df); group tests use one-way F (1 and 26 df). This residual permutation diagnostic assumes exchangeable residual distances and, for tissue, symmetric within-patient differences. Centroids are estimated; this is a sensitivity diagnostic, not independent evidence of equal distributions or a guarantee that PERMANOVA reflects only centroid location. Do not interpret a nonsignificant diagnostic as proof of equal dispersion.

| Comparison | F | P | BH P | Mean distance level 0 | Mean distance level 1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| tissue_paired_all | 4.036532 | 0.0528 | 0.0792 | 0.562926 | 0.529938 |
| HP_vs_SOM_adenoid | 7.591071 | 0.0095 | 0.0285 | 0.526953 | 0.460260 |
| HP_vs_SOM_tonsil | 0.000173 | 0.9894 | 0.9894 | 0.400787 | 0.400340 |

## Genus contrasts

Nine candidate genera are tested: Moraxella, Haemophilus, Streptococcus, Fusobacterium, Neisseria, Alloprevotella, Porphyromonas, Prevotella and Gemella. The 27 paired tests (9 genera × all/HP/SOM) form one BH family; the 18 between-group tests (9 genera × 2 tissues) form a separate BH family. The all-patient and within-group paired analyses overlap, so subgroup findings are exploratory.

The paired effect is the median of patient-specific tonsil minus adenoid percentage-point differences. Both tissue medians and their separate marginal-median difference are exported and must not be substituted for the median paired difference. Patient-level differences are also exported. Wilcoxon uses zero_method="wilcox" (drop zero differences), method="approx", two-sided, no continuity correction, and tie-adjusted normal variance. Differences are rounded to 12 decimal percentage points before ranking solely to avoid floating-point artifacts in equal values; counts of zeros, tied absolute differences and effective nonzero pairs are exported. All-zero contrasts return P=1 by convention. HP/SOM genus comparisons use a two-sided asymptotic, tie-corrected Mann–Whitney test with continuity correction.

| Genus (all 28 pairs) | Adenoid median % | Tonsil median % | Median paired difference pp | Raw P | BH P |
| --- | ---: | ---: | ---: | ---: | ---: |
| Moraxella | 1.378181 | 0.000000 | -1.303547 | 1.87264e-05 | 0.000505612 |
| Haemophilus | 7.768239 | 3.351260 | -4.249002 | 0.000171767 | 0.00231885 |
| Streptococcus | 21.875521 | 22.140987 | 4.316068 | 0.0271866 | 0.0667308 |
| Fusobacterium | 3.281981 | 9.214548 | 2.326852 | 0.538668 | 0.619789 |
| Neisseria | 3.352649 | 3.727148 | -0.296329 | 0.254882 | 0.362201 |
| Alloprevotella | 5.799546 | 4.246657 | -0.110416 | 0.438796 | 0.538522 |
| Porphyromonas | 4.578900 | 6.551178 | 2.164712 | 0.0241728 | 0.0652667 |
| Prevotella | 2.889521 | 6.649601 | 2.013246 | 0.0227777 | 0.0652667 |
| Gemella | 2.585794 | 4.722067 | 1.225154 | 0.151401 | 0.240461 |

## Reproduction and limits

Input provenance: `data/processed/prjna422760_sample_metadata.tsv`, `data/processed/prjna422760_genus_abundance.tsv`; original genus source: `data/references/external_labels/PRJNA422760/mSystems.00169-18-st003.xlsx`, Genus sheet. The workbook column headers supply HP/SOM labels and sample codes preserve pairing; the source article (doi:10.1128/mSystems.00169-18, Subjects and Sample collection) defines the clinical groups.

`python3 scripts/analyze_external_cohort.py` recreates the dedicated output directory. `run_metadata.json` records input and script SHA-256, software versions, seeds and passed design checks. Outputs include sample support, original abundance totals, per-sample state/threshold records, state counts, threshold concordance, all paired differences, paired and group genus results, PERMANOVA, dispersion diagnostics and centroid distances. A full-rank projection independently verifies each PERMANOVA term and residual sum of squares.

These analyses support tissue ecological differences only to the extent shown by the estimated contrasts. HP/SOM contrasts are observational and exploratory. They do not establish sinusitis replication, disease specificity, causality, shared mechanism, future progression or clinical prediction.
