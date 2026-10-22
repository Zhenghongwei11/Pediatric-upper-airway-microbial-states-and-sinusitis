# Supplementary Tables

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

| Variable | Profiles (n) | Missing profiles (n) | Coding / values |
| --- | --- | --- | --- |
| sinusitis_binary | 323 | 0 | Binary outcome: URI / sinusitis (0/1) |
| moraxella_30 | 323 | 0 | Binary exposure: below / at least 30% (0/1) |
| child_id | 323 | 0 | De-identified public child IDs; memberships are listed in S4 and S7 |
| season | 323 | 0 | Fall; Spring; Summer; Winter |
| daycare | 323 | 0 | No; Yes |
| tobacco_exposure | 323 | 0 | No; Yes |
| virus_count | 323 | 0 | 0; 1; 2; 4 |
| age_init | 323 | 0 | 4; 5; 6 years |
| shannon | 323 | 0 | Continuous Shannon diversity index |
| AB_Taken | 323 | 0 | Binary antibiotic-taken field (0/1) |

## S2. Dataset landscape and selection flow

The table summarizes 11 candidate datasets considered in a targeted feasibility screen of public pediatric airway and ENT cohorts. Study-size descriptions are drawn from the dataset records, and primary endpoint flow is shown separately from the candidate landscape.

| Candidate | Study role | Reported study size | Selection status and rationale | Additional information |
| --- | --- | --- | --- | --- |
| PRJEB35160 | Primary endpoint cohort | 354 processed profiles / 58 children; 462 ENA runs | Selected: primary endpoint cohort — Provides pediatric URI and acute sinusitis outcomes, child identifiers, selected covariates, and public processed data. | Longitudinal pediatric URI and acute sinusitis outcomes; companion analysis artifacts are available. |
| PRJNA554533 | Candidate cohort requiring verification | 75 runs | Not analyzed: clinical labels unverified — Public records do not currently verify sample-level assignment to adenoid hypertrophy, allergic rhinitis, or control groups. | The study reports nasal microbiota in children with adenoid hypertrophy or allergic rhinitis; public records do not yet verify sample-level group labels. |
| PRJNA422760 | Paired anatomical context | 56 runs | Summarized descriptively — Paired adenoid and tonsil samples with patient and clinical-group labels support descriptive state summaries. | The source article provides supplementary taxonomy and clinical-group data for paired adenoid and tonsil samples. |
| PRJEB88727 | Potential secondary ENT cohort | 174 runs | Verification pending — Clinical labels and sampling timepoints require confirmation from publication materials before analysis. | The OME cohort includes probiotic context; clinical labels and sampling timepoints require confirmation from publication materials. |
| PRJNA275918 | Contextual comparator cohort | 3035 runs / 234 infants | Context only — The infant age range and study endpoint differ from the target pediatric clinical question. | Infant nasopharyngeal profiles provide ecological context; age and endpoint differ from the primary clinical question. |
| PRJNA1413967 | Contextual comparator cohort | 126 runs | Context only — Asthma and healthy-control throat-swab sampling does not match the ENT study setting. | Upper-airway throat swabs compare asthma and healthy-control groups. |
| PRJNA1049442 | Contextual comparator cohort | 152 runs | Context only — Shotgun sequencing and HIV status differ from the 16S-based ENT cohorts. | Upper-respiratory shotgun data from children with and without HIV infection differ in assay modality and host condition. |
| PRJEB72800 | Candidate cohort requiring verification | Sample count not yet verified | Availability unresolved — The initial public ENA query has not yet yielded verifiable sample records; dataset availability remains unresolved. | A publication is available; the initial public ENA query has not yet yielded verifiable run records. |
| PRJNA861845 | Candidate cohort requiring verification | Sample count not yet verified | Accession status unresolved — The initial public SRA RunInfo query has not yet yielded verifiable sample records; accession status remains unresolved. | The publication reports an SRA accession; the initial public RunInfo query has not yet yielded verifiable run records. |
| PRJNA1441615 | Exploratory context cohort | 35 runs | Context only — The small tonsil cohort represents a distinct population of children with Down syndrome and obstructive sleep apnea. | Small tonsil cohort from children with Down syndrome and obstructive sleep apnea. |
| PRJNA615768 | Exploratory context cohort | 58 runs | Not selected — The tonsil and saliva study has assay and metadata descriptions that require clarification before primary analysis. | Tonsil and saliva data have assay and metadata descriptions that require clarification. |

| Screening stage | Datasets (n) | Participants / children (n) | Profiles / runs (n) | Screening outcome | Basis for selection |
| --- | --- | --- | --- | --- | --- |
| Public pediatric airway or ENT datasets screened | 11 | — | — | Screened | Candidate cohorts were assessed for pediatric relevance, airway or ENT sampling, public records, and usable clinical labels. |
| Primary endpoint cohort: all released | 1 | 58 | 354 | Released | Counts from the finalized primary endpoint cohort flow. |
| Primary endpoint cohort: eligible profiles included | 1 | 45 | 323 | Analyzed | URI and sinusitis profiles with eligible outcome labels. |
| Primary endpoint profiles excluded for no eligible group | 1 | 13 | 31 | Excluded | Released children and profiles without an eligible endpoint group. |
| Paired ENT cohort summarized descriptively | 1 | 28 | 56 | Descriptive summary | Public records and article supplements provide paired adenoid and tonsil labels and HP/SOM group assignment for descriptive summaries. |
| Pediatric ENT cohort with unverified group labels | 1 | — | 75 | Not analyzed | Public SRA, BioSample, and article materials do not currently verify sample-level assignments to adenoid hypertrophy, allergic rhinitis, or control groups. |
| Other candidates not selected for the primary endpoint analysis | 8 | — | — | Not selected for primary analysis | Age range, endpoint, sampling site, assay modality, or clinical labels differ from the primary clinical question. |

## S3. Threshold counts and adjusted associations

Each row uses the 323-profile, 45-child endpoint set. Exposed and unexposed child counts can overlap because children may contribute profiles to both exposure categories.

| Threshold | Exposed profiles / sinusitis profiles | Unexposed profiles / sinusitis profiles | Adjusted OR (95% CI) | Raw P | BH FDR |
| --- | --- | --- | --- | --- | --- |
| 25% | 164 / 85 | 159 / 58 | 1.802 (1.021–3.182) | 0.04254 | 0.0638 |
| 30% | 164 / 85 | 159 / 58 | 1.802 (1.021–3.182) | 0.04254 | 0.0638 |
| 50% | 149 / 77 | 174 / 66 | 1.744 (0.9532–3.192) | 0.07021 | 0.07021 |

## S4. Model summaries and explicit membership

The profile-level models use child-cluster robust inference where specified in the workbook. Sensitivity models remain labeled as such; genus models belong to a six-model focused family.

| Model family | Model | Exposure | OR (95% CI) | Raw P | BH FDR | Profiles | Children |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Primary/sensitivity | primary | moraxella_30 | 1.802 (1.021–3.182) | 0.04254 | NA | 323 | 45 |
| Primary/sensitivity | with_viral_count | moraxella_30 | 1.802 (1.02–3.185) | 0.04292 | NA | 323 | 45 |
| Primary/sensitivity | unadjusted | moraxella_30 | 1.874 (1.04–3.376) | 0.03719 | NA | 323 | 45 |
| Primary/sensitivity | equal_child_weight | moraxella_30 | 1.818 (0.9201–3.593) | 0.08382 | NA | 323 | 45 |
| Primary/sensitivity | cluster_I | cluster_i | 1.233 (0.6846–2.219) | 0.4773 | NA | 323 | 45 |
| Primary/sensitivity | Shannon | shannon | 1.085 (0.6639–1.772) | 0.7402 | NA | 323 | 45 |
| Tobacco-restricted | no_tobacco_exposure_restriction | moraxella_30 | 1.878 (1.042–3.387) | 0.03665 | NA | 311 | 44 |

Focused genus models:

| Genus | OR per 10-point increase (95% CI) | Raw P | BH FDR | Median fraction, URI | Median fraction, sinusitis |
| --- | --- | --- | --- | --- | --- |
| Moraxella | 1.07 (0.9821–1.166) | 0.1188 | 0.3565 | 0.3162 | 0.5743 |
| Haemophilus | 0.9132 (0.8171–1.021) | 0.1068 | 0.3565 | 0.0005041 | 0.000451 |
| Streptococcus | 1.008 (0.8514–1.193) | 0.9268 | 0.9324 | 9.286e-05 | 0.0001592 |
| Staphylococcus | 0.9433 (0.7647–1.164) | 0.578 | 0.8761 | 0 | 0 |
| Corynebacterium | 1.006 (0.8796–1.15) | 0.9324 | 0.9324 | 0.033 | 0.02165 |
| Alloiococcus | 0.9564 (0.8126–1.126) | 0.5841 | 0.8761 | 0.0908 | 0.0645 |

Primary child-cluster bootstrap odds ratio: 1.802 (percentile 95% interval 1.033–3.27; 1915 successful / 2000 requested resamples). Leave-one-child-out primary odds ratios ranged from 1.627 to 2.035 across 45 fits; this is an influence range, not a confidence interval. The companion `S4_Membership` worksheet contains all 19,458 model/sample/child/outcome membership records from `model_membership.tsv`.

## S5. Paired genus effects, zeros, and tied ranks

All 27 preselected paired tests are shown. The signed difference is tonsil minus adenoid in percentage points; the source Wilcoxon zero method is `wilcox`, with continuity correction off. The companion worksheet retains patient-level paired values.

| Comparison | Group | Genus | Pairs | Median paired difference (pp) | Zero differences | Tied-rank groups / observations | Raw P | BH FDR |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| tonsil_minus_adenoid_all | all | Moraxella | 28 | -1.304 | 2 | 0 / 0 | 1.873e-05 | 0.0005056 |
| tonsil_minus_adenoid_all | all | Haemophilus | 28 | -4.249 | 0 | 0 / 0 | 0.0001718 | 0.002319 |
| tonsil_minus_adenoid_all | all | Streptococcus | 28 | 4.316 | 0 | 0 / 0 | 0.02719 | 0.06673 |
| tonsil_minus_adenoid_all | all | Fusobacterium | 28 | 2.327 | 0 | 0 / 0 | 0.5387 | 0.6198 |
| tonsil_minus_adenoid_all | all | Neisseria | 28 | -0.2963 | 0 | 0 / 0 | 0.2549 | 0.3622 |
| tonsil_minus_adenoid_all | all | Alloprevotella | 28 | -0.1104 | 0 | 0 / 0 | 0.4388 | 0.5385 |
| tonsil_minus_adenoid_all | all | Porphyromonas | 28 | 2.165 | 0 | 0 / 0 | 0.02417 | 0.06527 |
| tonsil_minus_adenoid_all | all | Prevotella | 28 | 2.013 | 0 | 0 / 0 | 0.02278 | 0.06527 |
| tonsil_minus_adenoid_all | all | Gemella | 28 | 1.225 | 0 | 0 / 0 | 0.1514 | 0.2405 |
| tonsil_minus_adenoid_HP | HP | Moraxella | 14 | -1.748 | 1 | 0 / 0 | 0.002366 | 0.01065 |
| tonsil_minus_adenoid_HP | HP | Haemophilus | 14 | -2.563 | 0 | 0 / 0 | 0.03546 | 0.07366 |
| tonsil_minus_adenoid_HP | HP | Streptococcus | 14 | 2.7 | 0 | 0 / 0 | 0.1981 | 0.2972 |
| tonsil_minus_adenoid_HP | HP | Fusobacterium | 14 | -0.1298 | 0 | 0 / 0 | 0.4326 | 0.5385 |
| tonsil_minus_adenoid_HP | HP | Neisseria | 14 | 0.5907 | 0 | 0 / 0 | 0.05553 | 0.1071 |
| tonsil_minus_adenoid_HP | HP | Alloprevotella | 14 | 0.1213 | 0 | 0 / 0 | 0.925 | 0.9606 |
| tonsil_minus_adenoid_HP | HP | Porphyromonas | 14 | 5.675 | 0 | 0 / 0 | 0.01565 | 0.05283 |
| tonsil_minus_adenoid_HP | HP | Prevotella | 14 | 0.3605 | 0 | 0 / 0 | 0.975 | 0.975 |
| tonsil_minus_adenoid_HP | HP | Gemella | 14 | 4.645 | 0 | 0 / 0 | 0.03546 | 0.07366 |
| tonsil_minus_adenoid_SOM | SOM | Moraxella | 14 | -1.194 | 1 | 0 / 0 | 0.002366 | 0.01065 |
| tonsil_minus_adenoid_SOM | SOM | Haemophilus | 14 | -4.63 | 0 | 0 / 0 | 0.0009815 | 0.008834 |
| tonsil_minus_adenoid_SOM | SOM | Streptococcus | 14 | 5.987 | 0 | 0 / 0 | 0.07359 | 0.1325 |
| tonsil_minus_adenoid_SOM | SOM | Fusobacterium | 14 | 3.785 | 0 | 0 / 0 | 0.0962 | 0.1623 |
| tonsil_minus_adenoid_SOM | SOM | Neisseria | 14 | -4.154 | 0 | 0 / 0 | 0.004286 | 0.01653 |
| tonsil_minus_adenoid_SOM | SOM | Alloprevotella | 14 | -0.7651 | 0 | 0 / 0 | 0.3305 | 0.4462 |
| tonsil_minus_adenoid_SOM | SOM | Porphyromonas | 14 | -0.07092 | 0 | 0 / 0 | 0.8753 | 0.9453 |
| tonsil_minus_adenoid_SOM | SOM | Prevotella | 14 | 3.896 | 0 | 0 / 0 | 0.001887 | 0.01065 |
| tonsil_minus_adenoid_SOM | SOM | Gemella | 14 | -0.9696 | 0 | 0 / 0 | 0.5509 | 0.6198 |

## S6. Community tests and diagnostics

Primary-child and external-patient analyses are presented independently. Comparison codes are expanded into descriptive English, while numeric results retain their source values. The primary PERMANOVA uses 45 child-mean compositions; the external cohort has 28 paired patients and 56 samples. PERMANOVA and dispersion tests are both shown.

| Test | Comparison | Independent units | R² | F statistic | Raw P | BH FDR | Permutations |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Primary PERMANOVA (mean child composition) | Follow-up outcome group | 45 children; 323 profiles | 0.03179 | 1.412 | 0.2187 | Not reported | 9999 |
| Primary PERMDISP (mean child composition) | Follow-up outcome group | 45 children; 323 profiles | NA | 10.03 | 0.0022 | Not reported | 9999 |
| External PERMANOVA | Adenoid vs tonsil (paired) | 28 patients; 56 samples | 0.06331 | 6.507 | 0.0001 | 0.0003 | 9999 |
| External PERMANOVA | Hyperplasia vs secretory otitis media (adenoid) | 28 patients; 28 samples | 0.07816 | 2.204 | 0.038 | 0.057 | 9999 |
| External PERMANOVA | Hyperplasia vs secretory otitis media (tonsil) | 28 patients; 28 samples | 0.05237 | 1.437 | 0.1854 | 0.1854 | 9999 |
| External dispersion | Adenoid vs tonsil (paired) | 28 patients; 56 samples | — | 4.037 | 0.0528 | 0.0792 | 9999 |
| External dispersion | Hyperplasia vs secretory otitis media (adenoid) | 28 patients; 28 samples | — | 7.591 | 0.0095 | 0.0285 | 9999 |
| External dispersion | Hyperplasia vs secretory otitis media (tonsil) | 28 patients; 28 samples | — | 0.0001729 | 0.9894 | 0.9894 | 9999 |

| Primary dispersion diagnostic | Value |
| --- | --- |
| Mean distance to median: sinusitis | 0.5117 |
| Mean distance to median: URI | 0.5828 |
| Positive PCoA eigenvalues | 43 |
| Negative PCoA eigenvalues after Lingoes correction | 0 |

## S7. Child-level burden and earliest-profile analyses

Group descriptions summarize child-level burden. The earliest-profile model uses one first eligible profile per analyzed child.

| Group | Profiles | Children | Median profiles / child | Median Moraxella burden | Baseline age range |
| --- | --- | --- | --- | --- | --- |
| URI | 180 | 26 | 5.5 | 0.455 | 4–6 years |
| Sinusitis | 143 | 19 | 7 | 0.571 | 4–6 years |

| Cohort stage | Profiles | Children |
| --- | --- | --- |
| all_released | 354 | 58 |
| excluded_no_group | 31 | 13 |
| included | 323 | 45 |

| Analysis | OR (95% CI) | Raw P | Profiles | Children |
| --- | --- | --- | --- | --- |
| Child-level burden model | 1.587 (0.8997–2.799) | 0.1082 | NA | 45 |
| Earliest eligible profile per child | 0.4939 (0.09734–2.506) | 0.3862 | 45 | 45 |

## Source index

All result values are copied from the listed files; the builder does not refit models or calculate new estimates. Explanatory labels consolidate existing source annotations and decision records. Identifiers appear only when already present in de-identified public-study result files. Blank source fields remain blank in the workbook; literal `NA` values are preserved where reported.

| Table | Source path | Source rows | Use |
|---|---|---:|---|
| S1 | `results/primary/covariate_coding_missingness.tsv` | 10 | Coding and missing-profile counts |
| S2 | `docs/DATASET_LANDSCAPE.tsv` | 11 | Candidate dataset descriptors and access links |
| S2 | `docs/DATASET_SUITABILITY_DECISION.md` | 11 decisions | Disposition and rationale for each candidate |
| S2 | `docs/DATASET_SCREEN_FLOW.tsv` | 4 of 5 records | Dataset screen and non-primary cohort flow; primary endpoint counts are sourced separately |
| S2 | `results/primary/cohort_flow.tsv` | 3 | Finalized primary release, exclusion, and analysis flow |
| S3 | `results/primary/threshold_sensitivity.tsv` | 3 | Primary 25%, 30%, and 50% threshold counts and models |
| S3 | `results/primary/threshold_agreement.tsv` | 1 | Primary 25% versus 30% classification agreement |
| S3 | `results/external/state_counts.tsv` | 47 | External state-count distribution |
| S3 | `results/external/threshold_concordance.tsv` | 56 | Per-sample external state labels at 25%, 30%, and 50% |
| S4 | `results/primary/adjusted_models.tsv` | 6 | profile-level association/sensitivity |
| S4 | `results/primary/genus_models.tsv` | 6 | focused genus abundance |
| S4 | `results/primary/no_tobacco_model.tsv` | 1 | tobacco-restricted sensitivity |
| S4 | `results/primary/bootstrap_summary.tsv` | 11 | Point estimates, bootstrap intervals, successful and failed resamples |
| S4 | `results/primary/leave_one_child_out.tsv` | 45 | Exact model fit by omitted child |
| S4 | `results/primary/leave_one_child_out_summary.tsv` | 1 | Influence range summary |
| S4 | `results/primary/model_membership.tsv` | 19458 | Sample, child, and outcome membership for all fitted models |
| S5 | `results/external/paired_genus_effects.tsv` | 27 | All preselected paired genus-by-group tests |
| S5 | `results/external/patient_paired_differences.tsv` | 252 | Patient-level genus values used by paired comparisons |
| S6 | `results/primary/community_tests.tsv` | 2 | Primary child-level PERMANOVA and PERMDISP |
| S6 | `results/primary/community_diagnostics.txt` | text report | Primary distance-to-median and eigenvalue diagnostics |
| S6 | `results/external/permanova.tsv` | 3 | External-cohort Bray–Curtis PERMANOVA results |
| S6 | `results/external/dispersion.tsv` | 3 | External-cohort dispersion diagnostics |
| S6 | `results/external/centroid_distances.tsv` | 112 | Per-sample distance to group centroid |
| S7 | `results/primary/child_burden.tsv` | 45 | Child-level burden and covariates |
| S7 | `results/primary/child_burden_model.tsv` | 1 | Child burden per 25 percentage-point increase |
| S7 | `results/primary/earliest_profile_model.tsv` | 1 | Earliest eligible profile per child |
| S7 | `results/primary/cohort_flow.tsv` | 3 | Original endpoint cohort profile and child flow |
| S7 | `results/primary/child_flow.tsv` | 58 | Child-level released-to-analysis flow |

Workbook construction: `scripts/build_supplementary_tables.py`.
