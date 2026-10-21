#!/usr/bin/env python3
"""Independent numerical checks of fitted models and resampling outputs."""
from pathlib import Path
import hashlib, json, sys
import numpy as np
import pandas as pd
import scipy.stats as st
import statsmodels.api as sm
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.sandwich_covariance import cov_cluster
from state_classification import state_key, LABELS
R=Path(__file__).resolve().parents[1]; P=R/'results/primary'; E=R/'results/external'
checks=[]
def check(name,condition,detail=''):
    checks.append(dict(check=name,status='PASS' if bool(condition) else 'FAIL',detail=str(detail)))
def read(p):return pd.read_csv(p,sep='\t')
def close(a,b):return np.allclose(a,b,rtol=1e-8,atol=1e-10,equal_nan=True)
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
meta=read(R/'data/processed/prjeb35160_sample_metadata.tsv')
f=read(P/'profile_flow.tsv'); s=read(P/'state_assignments.tsv'); child=read(P/'child_burden.tsv'); m=read(P/'model_membership.tsv')
check('roundtrip_metadata',len(meta)==354 and meta.sample_id.is_unique and meta.child_id.nunique()==58)
check('endpoint_flow',len(s)==323 and s.child_id.nunique()==45 and s.outcome_group.eq('Sinusitis').sum()==143)
check('group_constant_per_child',s.groupby('child_id').outcome_group.nunique().eq(1).all())
check('excluded_children_profiles',len(f[~f.included])==31 and f[~f.included].child_id.nunique()==13 and not set(f[~f.included].child_id)&set(s.child_id))
check('threshold25_30_identical',s.moraxella_25.equals(s.moraxella_30))
check('primary_counts',s.moraxella_30.sum()==164 and s.loc[s.moraxella_30.eq(1),'outcome_group'].eq('Sinusitis').sum()==85)
check('burden_denominator',close(child.set_index('child_id').moraxella_fraction.sort_index(),s.groupby('child_id').moraxella_30.mean().sort_index()) and child.n_profiles.sum()==323)
# Rebuild the model independently, without importing the estimator under audit.
d=meta.merge(s[['sample_id','moraxella_30']],on='sample_id',validate='one_to_one').sort_values('sample_id').reset_index(drop=True)
x=pd.DataFrame({'Intercept':1.,'Moraxella':d.moraxella_30.astype(float)})
for season in ['Spring','Summer','Winter']:x[season]=d.season.eq(season).astype(float)
x['daycare']=d.daycare.eq('Yes').astype(float)
y=d.sinusitis_binary.astype(int); models=read(P/'adjusted_models.tsv').set_index('model')
for key,equal in [('primary',False),('equal_child_weight',True)]:
    w=(1/d.groupby('child_id').child_id.transform('size')).to_numpy() if equal else np.ones(len(d))
    r=sm.GLM(y,x,family=sm.families.Binomial(),freq_weights=w).fit()
    # Library sandwich gives an independent implementation of weighted-score CR1.
    v=cov_cluster(r,d.child_id,use_correction=True);se=np.sqrt(v[1,1]);beta=r.params.iloc[1]
    expected=np.exp([beta,beta-st.t.ppf(.975,44)*se,beta+st.t.ppf(.975,44)*se])
    actual=models.loc[key,['effect','ci_lower','ci_upper']].astype(float)
    check(key+'_independent_CR1',close(actual,expected),f'max error {max(abs(actual-expected)):.3g}')
    check(key+'_independent_t_P',close(models.loc[key,'pvalue'],2*st.t.sf(abs(beta/se),44)))
for file in ['adjusted_models.tsv','genus_models.tsv','threshold_sensitivity.tsv','no_tobacco_model.tsv','earliest_profile_model.tsv','child_burden_model.tsv','leave_one_child_out.tsv']:
    for _,r in read(P/file).iterrows():
        a=m[m.model.eq(r.model)]
        check('membership_'+r.model,len(a)==(r.n_profiles if pd.notna(r.n_profiles) else r.n_children) and a.child_id.nunique()==r.n_children)
        check('estimability_'+r.model,r['rank']==r.n_parameters and r.converged and r.ci_lower<r.effect<r.ci_upper and r.covariance_min_eigenvalue>=-1e-10)
for file in ['genus_models.tsv','threshold_sensitivity.tsv']:
    z=read(P/file);check('BH_'+file,close(z.fdr,multipletests(z.pvalue,method='fdr_bh')[1]))
b=read(P/'bootstrap_draws.tsv');c=read(P/'bootstrap_crude_draws.tsv');bs=read(P/'bootstrap_summary.tsv')
check('bootstrap_complete_requested',len(b)==4000 and len(c)==2000 and c.iteration.nunique()==2000)
for _,r in bs.iterrows():
    if r.model in ['primary','with_viral_count']:
        a=b[b.model.eq(r.model)&b.status.eq('success')];v=a[r.metric]
    else:
        column={'profile_proportion_ratio':'unadjusted_proportion_ratio','group_profile_proportion':('raw_exposed_proportion' if r.model=='Moraxella-dominant' else 'raw_unexposed_proportion')}[r.metric];v=c[column]
    check('bootstrap_summary_'+r.model+'_'+r.metric,len(v)==r.successful and r.successful+r.failed==r.requested and close(v.quantile([.025,.975]),[r.ci_lower,r.ci_upper]))
lo=read(P/'leave_one_child_out.tsv');summary=read(P/'leave_one_child_out_summary.tsv').iloc[0]
check('LOO_influence_range',len(lo)==45 and lo.omitted_child.nunique()==45 and close([lo.effect.min(),lo.effect.max()],[summary.estimate_min,summary.estimate_max]))
community=read(P/'community_tests.tsv');mean=read(P/'child_mean_otu_composition.tsv')
check('community_independent_units',community.n_children.eq(45).all() and community.exchangeability_unit.eq('independent_child').all() and len(mean)==45)
# Cross-cohort classifier checks at boundaries, unknowns and single anaerobic genera.
for genus in ['Moraxella','Haemophilus','Streptococcus','Neisseria','Prevotella','Fusobacterium','Alloprevotella','Porphyromonas','Gemella','Unclassified','unknown','uncultured','',None]:
    for fraction in [.299999,.30,.300001,.50,np.nan]:
        check('classifier_'+str(genus)+'_'+str(fraction),state_key(genus,fraction,.30)==state_key(genus,fraction*100,30))
check('primary_state_rule',all(LABELS[state_key(r.recomputed_genus,r.recomputed_fraction,.30)]==r.state_label for r in s.itertuples()))
ext=read(E/'sample_states.tsv');q=ext[ext.threshold_percent.eq(30)]
check('external_pairs',len(q)==56 and q.patient_id.nunique()==28 and q.groupby('patient_id').tissue.nunique().eq(2).all() and q.groupby('patient_id').clinical_group.nunique().eq(1).all())
check('external_state_rule',all(state_key(r.dominant_genus,r.dominant_percent,r.threshold_percent)==r.state_key for r in ext.itertuples()))
pair=read(E/'paired_genus_effects.tsv');diff=read(E/'patient_paired_differences.tsv')
patient_group=q.drop_duplicates('patient_id').set_index('patient_id').clinical_group
for _,r in pair.iterrows():
    a=diff[diff.genus.eq(r.genus)]
    if r.clinical_group!='all':a=a[a.patient_id.map(patient_group).eq(r.clinical_group)]
    v=a.difference_tonsil_minus_adenoid.to_numpy()
    test=st.wilcoxon(v,zero_method='wilcox',method='approx',correction=False)
    check('paired_'+r.clinical_group+'_'+r.genus,len(a)==r.n_pairs and close(np.median(v),r.median_paired_difference) and close(test.pvalue,r.p_value) and sum(v==0)==r.n_zero_differences)
check('paired_BH27',close(pair.p_bh,multipletests(pair.p_value,method='fdr_bh')[1]))
for file in ['permanova.tsv','dispersion.tsv']:
    z=read(E/file);check('external_BH_'+file,close(z.p_bh_3_tests,multipletests(z.p_value,method='fdr_bh')[1]))
z=read(E/'permanova.tsv')
check('external_permutations_effective',z.permutations_effective.eq(9999).all() and z.unique_label_allocations.eq(9999).all() and z.permutations_changing_labels.eq(9999).all())
for file in [P/'provenance.json',E/'run_metadata.json']:
    a=json.loads(file.read_text());hs=a.get('input_sha256',a.get('inputs',{}))
    for p,h in hs.items():check('hash_'+p,digest(R/p)==h)
out=R/'results/validation';out.mkdir(exist_ok=True,parents=True)
pd.DataFrame(checks).to_csv(out/'numerical_checks.tsv',sep='\t',index=False)
failed=[x for x in checks if x['status']=='FAIL']
report=dict(checks=len(checks),passed=len(checks)-len(failed),failed=len(failed),failures=failed)
(out/'numerical_checks.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2));sys.exit(bool(failed))
