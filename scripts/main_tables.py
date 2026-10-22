#!/usr/bin/env python3
"""Generate main Tables 1–3 from the participant summaries and fitted models."""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'results/primary'
E = ROOT / 'results/external'
OUT = ROOT / 'results/tables'
PRIMARY_METADATA = ROOT / 'data/processed/prjeb35160_sample_metadata.tsv'


def read(folder, name):
    return pd.read_csv(folder / name, sep='\t')


def child_demographics(primary_groups):
    """Summarize released sex and initial age once per primary-analysis child."""
    members = read(P, 'model_membership.tsv')
    members = members.loc[members.model.eq('primary'), ['sample_id', 'child_id', 'group']].copy()
    if members.empty or members.sample_id.duplicated().any():
        raise ValueError('Primary model membership is empty or has duplicate sample IDs')
    metadata = pd.read_csv(
        PRIMARY_METADATA, sep='\t', dtype={'sample_id': str, 'child_id': str}
    )[['sample_id', 'child_id', 'outcome_group', 'Gender', 'age_init']]
    members['sample_id'] = members.sample_id.astype(str)
    members['child_id'] = members.child_id.astype(str)
    joined = members.merge(
        metadata, on=['sample_id', 'child_id'], how='left', validate='one_to_one'
    )
    if joined[['outcome_group', 'Gender', 'age_init']].isna().any().any():
        raise ValueError('Primary membership has unmatched or incomplete demographic metadata')
    if not joined.group.eq(joined.outcome_group).all():
        raise ValueError('Primary membership group disagrees with the processed metadata')
    for column in ['group', 'Gender', 'age_init']:
        if joined.groupby('child_id')[column].nunique(dropna=False).gt(1).any():
            raise ValueError(f'{column} varies within a child in primary membership')
    if joined.child_id.nunique() != 45:
        raise ValueError(f'Expected 45 primary-analysis children; found {joined.child_id.nunique()}')
    if not joined.Gender.isin(['Female', 'Male']).all():
        raise ValueError('Unexpected or missing sex coding in primary membership')
    joined['age_init'] = pd.to_numeric(joined.age_init, errors='raise')
    children = joined.drop_duplicates('child_id').copy()
    observed = children.groupby('group').child_id.nunique()
    expected = primary_groups.n_children.astype(int)
    if not observed.reindex(expected.index).eq(expected).all():
        raise ValueError('Demographic child counts disagree with primary group descriptives')
    if set(observed.index) != {'URI', 'Sinusitis'}:
        raise ValueError('Unexpected group in primary demographic membership')
    summaries = {}
    for group, data in children.groupby('group'):
        n = len(data)
        sex_cells = []
        for sex in ['Female', 'Male']:
            count = int(data.Gender.eq(sex).sum())
            sex_cells.append(f'{sex} {count} ({count / n * 100:.1f}%)')
        age = data.age_init
        summaries[group] = {
            'sex': '; '.join(sex_cells),
            'age': f'{age.median():g} ({age.quantile(.25):g}–{age.quantile(.75):g})',
        }
    return summaries


def emit(number, frame, note):
    frame.to_csv(OUT / f'Table{number}.tsv', sep='\t', index=False)
    def escape(value):
        return str(value).replace('|', '\\|').replace('\n', ' ')
    lines = ['| ' + ' | '.join(map(escape, frame.columns)) + ' |',
             '| ' + ' | '.join(['---'] * len(frame.columns)) + ' |']
    lines.extend('| ' + ' | '.join(map(escape, row)) + ' |' for row in frame.itertuples(index=False, name=None))
    (OUT / f'Table{number}.md').write_text('\n'.join(lines) + '\n\n' + note + '\n')
    return frame


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    groups = read(P, 'group_descriptives.tsv').set_index('group')
    support = read(E, 'sample_support.tsv')
    n_patients = int(support[support.tissue == 'adenoid'].n_patients.sum())
    n_profiles = int(support.n_samples.sum())
    hp = int(support.query("tissue == 'adenoid' and clinical_group == 'HP'").n_patients.iloc[0])
    som = int(support.query("tissue == 'adenoid' and clinical_group == 'SOM'").n_patients.iloc[0])
    demographics = child_demographics(groups)
    rows = []
    def add(label, field, external, formatter=lambda x: str(int(x))):
        rows.append([label, formatter(groups.loc['URI', field]), formatter(groups.loc['Sinusitis', field]), external])
    add('Children', 'n_children', f'{n_patients}; {hp} HP and {som} SOM')
    rows.append([
        'Sex, children, n (%)', demographics['URI']['sex'], demographics['Sinusitis']['sex'],
        'Not available in released input table'
    ])
    add('Eligible sequencing profiles', 'n_profiles', f'{n_profiles}; one adenoid and one tonsil per child')
    rows.append(['Profiles per child, median (range)', *[f"{g.profiles_per_child_median:g} ({int(g.profiles_per_child_min)}–{int(g.profiles_per_child_max)})" for _,g in groups.loc[['URI','Sinusitis']].iterrows()], '2 (2–2)'])
    rows.append([
        'Initial age, median (IQR), years', demographics['URI']['age'], demographics['Sinusitis']['age'],
        'Not available in released input table'
    ])
    rows.append(['Released initial age / observed age', *[f"Initial integer field {int(g.baseline_age_min)}–{int(g.baseline_age_max)} years" for _,g in groups.loc[['URI','Sinusitis']].iterrows()], 'Observed age 15–65 months (source Table 1)'])
    for label,field in [('Baseline daycare, children','daycare_yes_children'),('Household tobacco exposure, children','tobacco_yes_children')]:
        rows.append([label,*[f'{int(g[field])}/{int(g.n_children)}' for _,g in groups.loc[['URI','Sinusitis']].iterrows()],'Not used in anatomical analyses'])
    add('Moraxella-dominant profile fraction per child, median','burden_median','Described by tissue',lambda x:f'{x:.3f}')
    table1 = emit(1,pd.DataFrame(rows,columns=['Characteristic','PRJEB35160: URI group','PRJEB35160: Sinusitis group','PRJNA422760: anatomical cohort']),
        'The primary source dataset contains 354 profiles/58 children; 31 profiles/13 children without the binary outcome were excluded. Baseline age is distinct from enrollment eligibility (48–96 months) and exact age at sampling. The external age range is reported in Table 1 of doi:10.1128/mSystems.00169-18; external sex and individual-age summaries are not available in the released input table and are not inferred. HP, hyperplasia; IQR, interquartile range; SOM, secretory otitis media; URI, upper respiratory infection.')
    models=read(P,'adjusted_models.tsv').set_index('model')
    selections=[('Unadjusted Moraxella dominance',models.loc['unadjusted']),
                ('Primary: season and daycare adjustment',models.loc['primary']),
                ('Primary plus simultaneous viral count',models.loc['with_viral_count']),
                ('Equal-child weighting, adjusted',models.loc['equal_child_weight']),
                ('Earliest eligible profile per child, adjusted',read(P,'earliest_profile_model.tsv').iloc[0]),
                ('No recorded tobacco exposure, adjusted',read(P,'no_tobacco_model.tsv').iloc[0]),
                ('Child burden per 25 percentage points, unadjusted',read(P,'child_burden_model.tsv').iloc[0])]
    rows=[]
    for label,m in selections:
        count=(f'{int(m.n_children)} child summaries / {int(m.n_children)}' if pd.isna(m.n_profiles) else f'{int(m.n_profiles)} / {int(m.n_children)}')
        rows.append([label,count,f'{m.effect:.2f} ({m.ci_lower:.2f}–{m.ci_upper:.2f})',f'{m.pvalue:.3f}'.removeprefix('0')])
    table2=emit(2,pd.DataFrame(rows,columns=['Analysis','Profiles / children','OR (95% CI)','Raw P']),
        'Moraxella dominance requires the most abundant genus to be Moraxella at ≥30%. Profile-model intervals use CR1 child-cluster covariance and t inference with G−1 degrees of freedom; the independent child-burden model uses t inference with 44 degrees of freedom. Apart from the focal primary model, rows are exploratory sensitivity analyses with raw P values and no separate confirmatory claim. OR, odds ratio; CI, confidence interval; G, number of children.')
    effects=read(E,'paired_genus_effects.tsv').query("clinical_group == 'all'")
    order=['Moraxella','Haemophilus','Streptococcus','Fusobacterium','Neisseria','Alloprevotella','Porphyromonas','Prevotella','Gemella']
    effects=effects.set_index('genus').loc[order].reset_index()
    # Numeric TSV retains full output precision; the companion Markdown formats display values.
    table3=effects[['genus','median_adenoid','median_tonsil','median_paired_difference','n_zero_differences','p_value','p_bh']].copy()
    table3.columns=['Genus','Adenoid median, %','Tonsil median, %','Median paired tonsil–adenoid difference, percentage points','Zero differences','Raw P','BH P']
    note='The effect is the median of within-patient differences, not the difference between tissue medians. Two-sided Wilcoxon signed ranks omit zero differences, use tie-adjusted normal approximation, and apply no continuity correction. BH correction covers all 27 genus-by-group paired tests (nine genera in all, HP and SOM patients).'
    emit(3,table3,note)
    with pd.ExcelWriter(OUT/'Main_Tables.xlsx',engine='openpyxl') as writer:
        for n,frame in [(1,table1),(2,table2),(3,table3)]:
            frame.to_excel(writer,sheet_name=f'Table{n}',index=False)
    print('Generated Tables 1–3 and Main_Tables.xlsx')


if __name__=='__main__':
    main()
