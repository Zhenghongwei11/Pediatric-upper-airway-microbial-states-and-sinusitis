# Dataset selection

The repository-based candidate screen considered 11 public pediatric airway or ENT datasets. It was a feasibility screen, not an exhaustive systematic search. Candidate accessions and source-reported sizes are retained in `DATASET_LANDSCAPE.tsv`; the analysis denominators are generated independently from the released primary object and surgical supplement.

PRJEB35160 supplies the source-defined child URI/Sinusitis follow-up groups, repeated profiles, child identifiers and covariates. The released 354 profiles from 58 children yield 323 profiles from 45 children with either binary group. This endpoint is a child-level group label repeated across visits, not a profile-specific acute episode or prospective progression outcome.

PRJNA422760 supplies paired adenoid/tonsil sequencing profiles for 28 surgical patients and published HP/SOM column labels. Its role is anatomical description with patient-aware inference. The clinical endpoint is not comparable to the primary URI/Sinusitis follow-up group, so it is not an external validation of a sinusitis association.

| Dataset | Disposition | Rationale |
| --- | --- | --- |
| PRJEB35160 | Analyzed: primary cohort | Public source object, child IDs, follow-up-group label and covariates. |
| PRJNA422760 | Analyzed: anatomical cohort | Published genus percentages, complete tissue pairs and HP/SOM labels. |
| PRJNA554533 | Not analyzed | No verifiable public sample-to-AH/AR/control mapping was recovered in the screen. |
| PRJEB88727 | Not analyzed | Relevant OME setting, but clinical labels and timepoints were insufficiently mapped. |
| PRJNA275918 | Background | Infant cohort with a different age range and endpoint. |
| PRJNA1413967 | Background | Asthma/control throat samples, with a different clinical endpoint. |
| PRJNA1049442 | Not analyzed | Shotgun assay and HIV context differ from the two 16S cohorts. |
| PRJEB72800 | Unresolved at screening | The recorded ENA request returned no run rows; this is not a claim that data are unavailable now. |
| PRJNA861845 | Unresolved at screening | The recorded accession request did not resolve; no present-day availability claim is made. |
| PRJNA1441615 | Not analyzed | Small Down syndrome/OSA tonsil population with a distinct clinical context. |
| PRJNA615768 | Not analyzed | Tonsil/saliva comparison with unresolved assay and metadata mapping. |

The screen is a historical selection record. No additional cohort is automatically included when a download becomes available. Different assays, patient populations and endpoint definitions require a separate scientific question and justified analysis.
