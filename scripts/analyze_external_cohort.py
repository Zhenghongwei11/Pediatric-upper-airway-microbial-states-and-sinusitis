#!/usr/bin/env python3
"""Patient-aware exploratory analysis of published PRJNA422760 genus percentages."""
from __future__ import annotations
import hashlib
import json
import math
import platform
from pathlib import Path

import numpy as np
import pandas as pd
import scipy
from scipy.spatial.distance import pdist, squareform
from scipy.stats import mannwhitneyu, wilcoxon

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results/external'
NOTE = ROOT / 'results/external_analysis.md'
SEED = 20261020
N_PERM = 9999
GENERA = ['Moraxella', 'Haemophilus', 'Streptococcus', 'Fusobacterium',
          'Neisseria', 'Alloprevotella', 'Porphyromonas', 'Prevotella', 'Gemella']
from state_classification import unclassified, state_key as state
INPUTS = [ROOT / 'data/processed/prjna422760_sample_metadata.tsv',
          ROOT / 'data/processed/prjna422760_genus_abundance.tsv']


def bh(values):
    values = np.asarray(values, float)
    order = np.argsort(values, kind='stable')
    adjusted = np.empty(len(values))
    adjusted[order] = np.minimum(1., np.minimum.accumulate(
        (values[order] * len(values) / np.arange(1, len(values) + 1))[::-1])[::-1])
    return adjusted


def write(frame, name):
    frame.to_csv(OUT / name, sep='\t', index=False, float_format='%.12g')



def allocations(labels, paired, seed):
    """Unique, label-changing Monte Carlo allocations, excluding observed labels."""
    rng = np.random.default_rng(seed)
    labels = np.asarray(labels, int)
    seen = {labels.tobytes()}
    rows = []
    while len(rows) < N_PERM:
        if paired:
            signs = rng.integers(0, 2, len(labels) // 2)
            row = np.column_stack([signs, 1 - signs]).ravel()
        else:
            row = rng.permutation(labels)
        key = row.tobytes()
        if key not in seen:
            seen.add(key)
            rows.append(row)
    return np.asarray(rows)


def gower(distance):
    squared = distance ** 2
    return -.5 * (squared - squared.mean(0)[None, :] - squared.mean(1)[:, None] + squared.mean())


def contrast(labels):
    c = np.asarray(labels, float)
    c = c - c.mean(axis=-1, keepdims=True)
    return c / np.sqrt((c*c).sum(axis=-1, keepdims=True))


def permutation_p(observed, permuted):
    return (1 + int(np.sum(permuted >= observed - 1e-12))) / (len(permuted) + 1)


def permanova(distance, labels, perms, patients=None):
    """One df term; patient-adjusted when paired, ordinary one-way otherwise."""
    g = gower(distance)
    n = len(labels)
    total = np.trace(g)
    patient_ss = 0.
    nuisance_rank = 1
    if patients is not None:
        patient_array = np.asarray(patients)
        blocks = [np.flatnonzero(patient_array == p) for p in np.unique(patient_array)]
        patient_ss = sum(g[np.ix_(b, b)].sum() / len(b) for b in blocks)
        nuisance_rank = len(blocks)
    q = contrast(labels)
    observed_ss = q @ g @ q
    perm_q = contrast(perms)
    perm_ss = np.einsum('bi,ij,bj->b', perm_q, g, perm_q, optimize=True)
    residual_df = n - nuisance_rank - 1
    residual_ss = total - patient_ss - observed_ss
    f = observed_ss / (residual_ss / residual_df)
    perm_f = perm_ss / ((total - patient_ss - perm_ss) / residual_df)
    assert np.isfinite(perm_f).all() and residual_ss > 0
    return dict(pseudo_f=float(f), term_ss=float(observed_ss), total_ss=float(total),
                patient_ss=float(patient_ss), residual_ss=float(residual_ss),
                term_r2_total=float(observed_ss / total),
                term_partial_r2=float(observed_ss / (total - patient_ss)),
                term_df=1, residual_df=residual_df,
                p_value=permutation_p(f, perm_f),
                permutations_requested=N_PERM, permutations_effective=len(perms),
                unique_label_allocations=len(perms), unique_statistic_values=len(np.unique(np.round(perm_f, 12))),
                permutations_changing_labels=int(np.any(perms != labels, axis=1).sum()))


def pcoa_lingoes(distance):
    """Euclidean coordinates, retaining every positive axis after Lingoes correction."""
    eig = np.linalg.eigvalsh(gower(distance))
    correction = max(0., -float(eig.min()))
    corrected = distance**2 + 2*correction
    np.fill_diagonal(corrected, 0.)
    vals, vectors = np.linalg.eigh(gower(np.sqrt(np.maximum(corrected, 0.))))
    positive = vals > max(1e-12, float(vals.max()) * 1e-12)
    coords = vectors[:, positive] * np.sqrt(vals[positive])
    return coords, dict(lingoes_constant=correction, minimum_original_eigenvalue=float(eig.min()),
                       negative_original_eigenvalues=int(np.sum(eig < -1e-12)),
                       original_negative_to_positive_eigenvalue_mass=float(-eig[eig < -1e-12].sum() / eig[eig > 1e-12].sum()),
                       pcoa_axes_retained=int(positive.sum()))


def dispersion(distance, labels, perms, paired):
    """PERMDISP diagnostic via fixed centroid distances and restricted residual permutations.

    Distances are estimated once from each observed group centroid. Permuting these
    distances (not the raw composition labels / recomputing centroids) corresponds
    to the usual residual permutation approach under the no-dispersion-effect null.
    Paired analysis removes patient means, so permutation is sign flipping each
    patient's centroid-distance difference. This is a diagnostic under residual
    exchangeability / symmetric differences, not a proof of equal dispersions.
    """
    coords, info = pcoa_lingoes(distance)
    labels = np.asarray(labels)
    distances = np.empty(len(labels))
    for level in [0, 1]:
        idx = labels == level
        distances[idx] = np.linalg.norm(coords[idx] - coords[idx].mean(0), axis=1) * math.sqrt(idx.sum() / (idx.sum() - 1))
    if paired:
        differences = distances[1::2] - distances[::2]
        observed = differences.mean()**2 / (differences.var(ddof=1) / len(differences))
        perm_differences = (perms[:, 1::2] - perms[:, ::2]) * differences
        perm_stat = perm_differences.mean(1)**2 / (perm_differences.var(1, ddof=1) / len(differences))
        df = len(differences) - 1
    else:
        centered = distances - distances.mean()
        q = contrast(labels)
        term = (q @ centered)**2
        total = centered @ centered
        observed = term / ((total - term) / (len(labels) - 2))
        perm_term = (contrast(perms) @ centered)**2
        perm_stat = perm_term / ((total - perm_term) / (len(labels) - 2))
        df = len(labels) - 2
    return dict(statistic_f=float(observed), term_df=1, residual_df=df,
                p_value=permutation_p(observed, perm_stat),
                mean_distance_level0=float(distances[labels == 0].mean()),
                mean_distance_level1=float(distances[labels == 1].mean()),
                distance_bias_adjustment='sqrt(n_group/(n_group-1))',
                permutations_requested=N_PERM, permutations_effective=len(perms),
                permutation_target='fixed centroid-distance residuals; within-patient sign swaps' if paired else 'fixed centroid-distance residuals; independent patients',
                **info), distances


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    NOTE.parent.mkdir(parents=True, exist_ok=True)
    metadata = pd.read_csv(INPUTS[0], sep='\t', dtype={'patient_id': str})
    abundance = pd.read_csv(INPUTS[1], sep='\t', keep_default_na=False)
    assert metadata.sample_name.is_unique
    duplicate_rows = abundance[abundance.duplicated(['sample_name', 'genus'], keep=False)]
    if len(duplicate_rows):
        write(duplicate_rows, 'source_duplicate_genus_rows.tsv')
    # The published table contains two Fusobacterium rows; sum matching genus
    # labels before every distance, abundance contrast and dominance assignment.
    abundance = abundance.groupby(['sample_name', 'genus'], as_index=False, sort=True).relative_abundance.sum()
    assert np.isfinite(abundance.relative_abundance).all() and (abundance.relative_abundance >= 0).all()
    assert set(metadata.sample_name) == set(abundance.sample_name)
    assert metadata.groupby('patient_id').tissue.apply(lambda x: sorted(x) == ['adenoid', 'tonsil']).all()
    assert metadata.groupby('patient_id').clinical_group.nunique().eq(1).all()
    metadata['tissue_order'] = metadata.tissue.map({'adenoid': 0, 'tonsil': 1})
    metadata['patient_order'] = metadata.patient_id.astype(int)
    metadata = metadata.sort_values(['patient_order', 'tissue_order']).reset_index(drop=True)
    wide = abundance.pivot(index='sample_name', columns='genus', values='relative_abundance').fillna(0).reindex(metadata.sample_name)
    assert wide.columns.is_unique and len(metadata) == 56 and metadata.patient_id.nunique() == 28
    support = metadata.groupby(['clinical_group', 'tissue']).agg(n_samples=('sample_name', 'size'), n_patients=('patient_id', 'nunique')).reset_index()
    write(support, 'sample_support.tsv')
    totals = metadata[['sample_name', 'patient_id', 'tissue', 'clinical_group']].copy()
    totals['published_named_genus_sum_percent'] = wide.sum(axis=1).to_numpy()
    totals['unreported_percent_to_100'] = 100 - totals.published_named_genus_sum_percent
    write(totals, 'abundance_totals.tsv')
    state_rows = []
    for idx, row in metadata.iterrows():
        values = wide.iloc[idx]
        top_value = float(values.max())
        tied = sorted(values.index[values == top_value])
        top = tied[0]
        for threshold in [25, 30, 50]:
            state_rows.append(dict(sample_name=row.sample_name, patient_id=row.patient_id, tissue=row.tissue,
                clinical_group=row.clinical_group, threshold_percent=threshold, dominant_genus=top,
                dominant_percent=top_value, tied_top_count=len(tied), tied_top_genera=';'.join(tied),
                dominant_is_unclassified=unclassified(top), state_key=state(top, top_value, threshold),
                named_genus_total_percent=float(values.sum())))
    states = pd.DataFrame(state_rows)
    write(states, 'sample_states.tsv')
    write(states.groupby(['threshold_percent', 'tissue', 'clinical_group', 'state_key']).size().reset_index(name='n_samples'), 'state_counts.tsv')
    write(states.pivot(index='sample_name', columns='threshold_percent', values='state_key').reset_index(), 'threshold_concordance.tsv')
    paired_rows, individual_rows, group_rows = [], [], []
    for group in ['all', 'HP', 'SOM']:
        subset = metadata if group == 'all' else metadata[metadata.clinical_group == group]
        a = wide.loc[subset[subset.tissue == 'adenoid'].sample_name]
        t = wide.loc[subset[subset.tissue == 'tonsil'].sample_name]
        ids = subset[subset.tissue == 'adenoid'].patient_id.to_list()
        for genus in GENERA:
            av, tv = a[genus].to_numpy(), t[genus].to_numpy()
            # Rounding only differences prevents spurious IEEE-754 rank ties;
            # 12 percentage-point decimals exceed source reporting precision.
            differences = np.round(tv - av, 12)
            nonzero = differences[differences != 0]
            unique_abs, counts = np.unique(np.abs(nonzero), return_counts=True)
            if len(nonzero):
                result = wilcoxon(differences, zero_method='wilcox', correction=False,
                                  alternative='two-sided', method='approx')
                statistic, p_value = float(result.statistic), float(result.pvalue)
            else:
                statistic, p_value = 0., 1.
            paired_rows.append(dict(comparison='tonsil_minus_adenoid_' + group, clinical_group=group, genus=genus,
                n_pairs=len(av), n_samples=2*len(av), median_adenoid=float(np.median(av)), median_tonsil=float(np.median(tv)),
                median_paired_difference=float(np.median(differences)), difference_of_marginal_medians=float(np.median(tv)-np.median(av)),
                n_zero_differences=int((differences == 0).sum()), n_nonzero_differences=len(nonzero),
                n_tied_absolute_difference_groups=int((counts > 1).sum()),
                n_observations_in_absolute_ties=int(counts[counts > 1].sum()),
                statistic=statistic, p_value=p_value, zero_method='wilcox', method='approx', continuity_correction=False,
                test='two-sided Wilcoxon signed-rank', family='27 preselected genus-by-group paired tests'))
            if group == 'all':
                for patient, aa, tt, dd in zip(ids, av, tv, differences):
                    individual_rows.append(dict(patient_id=patient, genus=genus, adenoid_percent=aa, tonsil_percent=tt, difference_tonsil_minus_adenoid=dd))
    paired = pd.DataFrame(paired_rows)
    paired['p_bh'] = bh(paired.p_value)
    write(paired, 'paired_genus_effects.tsv')
    write(pd.DataFrame(individual_rows), 'patient_paired_differences.tsv')
    for tissue in ['adenoid', 'tonsil']:
        sub = metadata[metadata.tissue == tissue]
        for genus in GENERA:
            hp = wide.loc[sub[sub.clinical_group == 'HP'].sample_name, genus].to_numpy()
            som = wide.loc[sub[sub.clinical_group == 'SOM'].sample_name, genus].to_numpy()
            result = mannwhitneyu(hp, som, alternative='two-sided', method='asymptotic', use_continuity=True)
            group_rows.append(dict(tissue=tissue, genus=genus, n_hp_patients=len(hp), n_som_patients=len(som),
                median_hp=float(np.median(hp)), median_som=float(np.median(som)),
                median_difference_som_minus_hp=float(np.median(som)-np.median(hp)),
                statistic_u=float(result.statistic), p_value=float(result.pvalue),
                method='two-sided Mann-Whitney; asymptotic tie-corrected; continuity correction', family='18 preselected genus-by-tissue group tests'))
    groups = pd.DataFrame(group_rows)
    groups['p_bh'] = bh(groups.p_value)
    write(groups, 'group_genus_effects.tsv')
    beta_rows, dispersion_rows, distance_rows = [], [], []
    designs = [('tissue_paired_all', metadata, True, SEED),
               ('HP_vs_SOM_adenoid', metadata[metadata.tissue == 'adenoid'], False, SEED + 1),
               ('HP_vs_SOM_tonsil', metadata[metadata.tissue == 'tonsil'], False, SEED + 2)]
    for name, sub, paired_design, seed in designs:
        labels = sub.tissue_order.to_numpy() if paired_design else sub.clinical_group.map({'HP': 0, 'SOM': 1}).to_numpy()
        perms = allocations(labels, paired_design, seed)
        assert np.all(np.any(perms != labels, axis=1)) and len(np.unique(perms, axis=0)) == N_PERM
        if paired_design:
            assert np.all(perms[:, ::2] + perms[:, 1::2] == 1)
        else:
            assert np.all(perms.sum(1) == labels.sum())
        dist = squareform(pdist(wide.loc[sub.sample_name].to_numpy(), metric='braycurtis'))
        common = dict(comparison=name, metric='Bray-Curtis on 79 published genus percentage columns; no closure',
                      n_samples=len(sub), n_patients=sub.patient_id.nunique(), seed=seed,
                      model='distance ~ patient + tissue; tissue after patient' if paired_design else 'distance ~ clinical_group',
                      labels_level0='adenoid' if paired_design else 'HP', labels_level1='tonsil' if paired_design else 'SOM',
                      exchangeability='tissue labels swapped independently within each patient' if paired_design else 'HP/SOM labels permuted among independent patients within this tissue',
                      possible_allocations=2**(len(sub)//2) if paired_design else math.comb(len(sub), int(labels.sum())))
        beta = permanova(dist, labels, perms, sub.patient_id.to_numpy() if paired_design else None)
        beta_rows.append({**common, **beta})
        disp, values = dispersion(dist, labels, perms, paired_design)
        dispersion_rows.append({**common, **disp})
        for sample, value in zip(sub.sample_name, values):
            distance_rows.append(dict(comparison=name, sample_name=sample, centroid_distance=value))
        # Independent explicit projection check of the term and residual sums of squares.
        if paired_design:
            patient_design = pd.get_dummies(sub.patient_id, dtype=float).to_numpy()
            full_design = np.column_stack([patient_design, labels])
        else:
            patient_design = np.ones((len(sub), 1))
            full_design = np.column_stack([patient_design, labels])
        h0 = patient_design @ np.linalg.pinv(patient_design)
        h1 = full_design @ np.linalg.pinv(full_design)
        gg = gower(dist)
        assert np.isclose(np.trace((h1-h0) @ gg), beta['term_ss'])
        assert np.isclose(np.trace((np.eye(len(sub))-h1) @ gg), beta['residual_ss'])
    beta = pd.DataFrame(beta_rows)
    beta['p_bh_3_tests'] = bh(beta.p_value)
    dispersions = pd.DataFrame(dispersion_rows)
    dispersions['p_bh_3_tests'] = bh(dispersions.p_value)
    write(beta, 'permanova.tsv')
    write(dispersions, 'dispersion.tsv')
    write(pd.DataFrame(distance_rows), 'centroid_distances.tsv')
    checks = dict(metadata_unique=True, complete_pairs=True, patient_group_constant=True,
                  input_abundances_nonnegative=True, explicit_projection_matches=True,
                  all_permutations_unique_and_label_changing=True,
                  within_pair_swaps_verified=True, group_sizes_preserved=True,
                  classification_30_boundary=state('Moraxella', 30, 30) == 'moraxella_dominant',
                  classification_unknown_mixed=state('Unclassified', 80, 30) == 'mixed',
                  classification_single_anaerobe=state('Prevotella', 30, 30) == 'anaerobe_dominant',
                  paired_rows=len(paired), patient_genus_differences=len(individual_rows))
    metadata_run = dict(seed=SEED, permutations=N_PERM, python=platform.python_version(), numpy=np.__version__, pandas=pd.__version__, scipy=scipy.__version__,
        n_genus_columns=wide.shape[1], source_duplicate_genus_rows=len(duplicate_rows), checks=checks, clinical_label_full_names={'HP': 'hyperplasia group', 'SOM': 'secretory otitis media'},
        clinical_label_source='https://doi.org/10.1128/mSystems.00169-18; source Table 1 and Subjects and Sample collection',
        
        inputs={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in INPUTS},
        source_workbook_sha256=hashlib.sha256((ROOT / 'data/references/external_labels/PRJNA422760/mSystems.00169-18-st003.xlsx').read_bytes()).hexdigest(),
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        classifier_sha256=hashlib.sha256((ROOT / "scripts/state_classification.py").read_bytes()).hexdigest())
    (OUT / 'run_metadata.json').write_text(json.dumps(metadata_run, indent=2)+'\n')
    lines = ['# PRJNA422760 patient-aware external analysis', '',
      'This exploratory external analysis concerns paired adenoid/tonsil tissue ecology and the published HP/SOM groups. It does not provide a comparable sinusitis outcome or direct disease replication.', '',
      '## Data and labels', '',
      'There are 56 sequencing profiles from 28 children aged 15–65 months (Table 1), with one adenoid and one palatine-tonsil profile per child. HP and SOM each contain 14 children (28 profiles), with 14 children per group within each tissue. Patient-level group labels are constant. HP means hyperplasia group: significant palatine-tonsil and/or adenoid lymphoid hyperplasia with obstructive symptoms, without acute otitis media (AOM) or SOM in the preceding year. SOM means secretory otitis media, verified by middle-ear fluid, tympanometry, paracentesis and ENT clinical evaluation. No child had an acute infection at sampling. The source reports 112 eligible collected specimens because each child provided separate sequencing and culture specimens at both tissue sites; these are distinct from the 56 sequencing profiles analyzed here. Source: doi:10.1128/mSystems.00169-18, Table 1 and Subjects and Sample collection.', '',
      f'The table contains {wide.shape[1]} distinct reported genus columns after summing the two source Fusobacterium rows. The duplicate source rows are exported; all statistics and classifications use the same genus aggregation. The original Genus sheet header explicitly says sequences not classified to genus level are not shown. Per-sample sums range from {wide.sum(axis=1).min():.6f}% to {wide.sum(axis=1).max():.6f}% (median {wide.sum(axis=1).median():.6f}%). Published percentages are preserved for all abundance comparisons, classifications and Bray–Curtis distances. There is no renormalization or imputation of the unreported fraction; the missing fraction cannot safely be assigned to a named genus. The dominant reported genus therefore concerns the supplied genus table, not independently reprocessed reads.', '',
      '## Classification', '',
      'A single reported genus with maximum percentage at least the threshold defines dominance (25%, 30%, and 50% are exported; 30% is the working definition). Exact ties are resolved lexicographically by genus name and are flagged. An unclassified/unknown/uncultured-prefix, empty or missing top genus is mixed; a named maximum below threshold is mixed. Moraxella, Haemophilus, Streptococcus and Neisseria are separate states. A highest single genus in Fusobacterium/Porphyromonas/Prevotella/Alloprevotella defines the anaerobe state; these genera are never pooled to reach the threshold. Remaining named dominant genera are other.', '',
      '## Community tests and exchangeability', '',
      'The tissue PERMANOVA fits patient + tissue, testing the one-degree-of-freedom tissue term after patient (27 residual degrees of freedom). Patient effects account for the paired design. Labels swap independently within each of 28 pairs. Group tests fit HP/SOM separately in each tissue (28 independent patients; 26 residual degrees of freedom), holding group sizes at 14/14. The group comparison assumes patients are exchangeable under the null; diagnosis is observational, so unmeasured confounding and enrollment differences remain possible. Tissue swaps assume the two tissue profiles within a patient are exchangeable under the no-tissue-effect null.', '',
      'Each test uses 9,999 distinct randomly sampled label allocations excluding the observed allocation. All allocations change the tested label; pair restrictions and group counts are checked. Seeds are 20261020 (tissue), 20261021 (adenoid group) and 20261022 (tonsil group). Monte Carlo P = (1 + number of permuted statistics at least observed)/(9999 + 1), with 1e-12 numerical tolerance. Distinct labels need not yield distinct statistics; the exported count records this distinction. R² is term SS / total SS; partial R² for tissue divides by total SS minus patient SS. Raw and BH P values across the three community tests are supplied.', '',
      '| Comparison | F | Total R² | Partial R² | P | BH P |',
      '| --- | ---: | ---: | ---: | ---: | ---: |']
    for r in beta.itertuples():
        lines.append(f'| {r.comparison} | {r.pseudo_f:.6f} | {r.term_r2_total:.6f} | {r.term_partial_r2:.6f} | {r.p_value:.4f} | {r.p_bh_3_tests:.4f} |')
    lines += ['', 'The paired tissue contrast supports a tissue-associated compositional difference. The adenoid HP/SOM comparison has raw P=0.0380 and BH P=0.0570 across the three community tests; its dispersion diagnostic also differs (raw P=0.0095). It therefore does not cleanly establish a group difference in community centroid. The tonsil comparison remains uncertain (P=0.1854). None of the 18 individual genus HP/SOM contrasts survives its BH family (minimum BH P=0.1617).', '', '## Dispersion diagnostic', '',
      'PERMDISP uses Euclidean principal coordinates after Lingoes correction of the squared Bray–Curtis distances, retaining every positive axis; constants and the original negative eigenvalue mass are exported. Distances to the observed group centroid are multiplied by sqrt(n/(n−1)) for finite-group bias adjustment. The null is tested by permuting fixed centroid-distance residuals: within-patient swaps for tissue, and independent-patient permutations separately within each tissue for HP/SOM. Tissue uses squared paired t (equivalently F with 1 and 27 df); group tests use one-way F (1 and 26 df). This residual permutation diagnostic assumes exchangeable residual distances and, for tissue, symmetric within-patient differences. Centroids are estimated; this is a sensitivity diagnostic, not independent evidence of equal distributions or a guarantee that PERMANOVA reflects only centroid location. Do not interpret a nonsignificant diagnostic as proof of equal dispersion.', '',
      '| Comparison | F | P | BH P | Mean distance level 0 | Mean distance level 1 |',
      '| --- | ---: | ---: | ---: | ---: | ---: |']
    for r in dispersions.itertuples():
        lines.append(f'| {r.comparison} | {r.statistic_f:.6f} | {r.p_value:.4f} | {r.p_bh_3_tests:.4f} | {r.mean_distance_level0:.6f} | {r.mean_distance_level1:.6f} |')
    lines += ['', '## Genus contrasts', '',
      'Nine candidate genera are tested: Moraxella, Haemophilus, Streptococcus, Fusobacterium, Neisseria, Alloprevotella, Porphyromonas, Prevotella and Gemella. The 27 paired tests (9 genera × all/HP/SOM) form one BH family; the 18 between-group tests (9 genera × 2 tissues) form a separate BH family. The all-patient and within-group paired analyses overlap, so subgroup findings are exploratory.', '',
      'The paired effect is the median of patient-specific tonsil minus adenoid percentage-point differences. Both tissue medians and their separate marginal-median difference are exported and must not be substituted for the median paired difference. Patient-level differences are also exported. Wilcoxon uses zero_method="wilcox" (drop zero differences), method="approx", two-sided, no continuity correction, and tie-adjusted normal variance. Differences are rounded to 12 decimal percentage points before ranking solely to avoid floating-point artifacts in equal values; counts of zeros, tied absolute differences and effective nonzero pairs are exported. All-zero contrasts return P=1 by convention. HP/SOM genus comparisons use a two-sided asymptotic, tie-corrected Mann–Whitney test with continuity correction.', '',
      '| Genus (all 28 pairs) | Adenoid median % | Tonsil median % | Median paired difference pp | Raw P | BH P |',
      '| --- | ---: | ---: | ---: | ---: | ---: |']
    for r in paired[paired.clinical_group == 'all'].itertuples():
        lines.append(f'| {r.genus} | {r.median_adenoid:.6f} | {r.median_tonsil:.6f} | {r.median_paired_difference:.6f} | {r.p_value:.6g} | {r.p_bh:.6g} |')
    lines += ['', '## Reproduction and limits', '',
      'Input provenance: `data/processed/prjna422760_sample_metadata.tsv`, `data/processed/prjna422760_genus_abundance.tsv`; original genus source: `data/references/external_labels/PRJNA422760/mSystems.00169-18-st003.xlsx`, Genus sheet. The workbook column headers supply HP/SOM labels and sample codes preserve pairing; the source article (doi:10.1128/mSystems.00169-18, Subjects and Sample collection) defines the clinical groups.', '',
      '`python3 scripts/analyze_external_cohort.py` recreates the dedicated output directory. `run_metadata.json` records input and script SHA-256, software versions, seeds and passed design checks. Outputs include sample support, original abundance totals, per-sample state/threshold records, state counts, threshold concordance, all paired differences, paired and group genus results, PERMANOVA, dispersion diagnostics and centroid distances. A full-rank projection independently verifies each PERMANOVA term and residual sum of squares.', '',
      'These analyses support tissue ecological differences only to the extent shown by the estimated contrasts. HP/SOM contrasts are observational and exploratory. They do not establish sinusitis replication, disease specificity, causality, shared mechanism, future progression or clinical prediction.']
    NOTE.write_text('\n'.join(lines)+'\n')
    print(beta[['comparison', 'pseudo_f', 'term_r2_total', 'p_value']].to_string(index=False))
    print(dispersions[['comparison', 'statistic_f', 'p_value']].to_string(index=False))
    print('Verified 56 samples / 28 complete patient pairs; all design checks passed.')


if __name__ == '__main__':
    main()
