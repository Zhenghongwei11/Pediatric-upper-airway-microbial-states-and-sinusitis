#!/usr/bin/env python3
"""Reproducible descriptive associations with child-cluster uncertainty."""
from __future__ import annotations
import hashlib, json, platform, warnings
from pathlib import Path
import numpy as np
import pandas as pd
import scipy
from scipy.special import expit
from scipy.stats import t
import statsmodels
import statsmodels.api as sm
from statsmodels.stats.multitest import multipletests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results/primary'
SEED = 20261020
BOOTSTRAPS = 2000
from state_classification import LABELS, state_key
FOCUS = ['Moraxella','Haemophilus','Streptococcus','Staphylococcus','Corynebacterium','Alloiococcus']
MEMBERS = []

def save(df, name):
    pd.DataFrame(df).to_csv(OUT/name, sep='\t', index=False, na_rep='NA')

def state(genus, fraction, threshold=.30):
    return LABELS[state_key(genus, fraction, threshold)]

def design(df, exposure, virus=False):
    x = pd.DataFrame({'Intercept':np.ones(len(df)), exposure:df[exposure].astype(float)},index=df.index)
    for season in ['Spring','Summer','Winter']:
        x['season_'+season] = df.season.eq(season).astype(float)
    x['daycare_Yes'] = df.daycare.eq('Yes').astype(float)
    if virus: x['virus_count'] = df.virus_count.astype(float)
    return x

def fit(df, exposure, label, virus=False, equal_child=False, covariates=True, clustered=True):
    required=['sinusitis_binary',exposure,'child_id']
    if covariates: required += ['season','daycare','tobacco_exposure']+(['virus_count'] if virus else [])
    d=df.dropna(subset=required).copy()
    x=design(d,exposure,virus) if covariates else sm.add_constant(d[[exposure]].astype(float),has_constant='add')
    y=d.sinusitis_binary.astype(int)
    weights=1/d.groupby('child_id').child_id.transform('size') if equal_child else None
    kwargs={'freq_weights':weights} if weights is not None else {}
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        model=sm.GLM(y,x,family=sm.families.Binomial(),**kwargs)
        res=model.fit()
        if clustered:
            w=np.ones(len(d)) if weights is None else np.asarray(weights)
            xx=np.asarray(x); mu=np.asarray(res.fittedvalues)
            bread=np.linalg.inv(xx.T@((w*mu*(1-mu))[:,None]*xx))
            score=xx*(w*(np.asarray(y)-mu))[:,None]
            scores=pd.DataFrame(score).groupby(d.child_id.to_numpy(),sort=False).sum().to_numpy()
            g=d.child_id.nunique(); n,k=xx.shape
            covariance=(g/(g-1))*((n-1)/(n-k))*bread@(scores.T@scores)@bread
            dfree=g-1
        else:
            covariance=np.asarray(res.cov_params()); dfree=len(d)-1
    beta=float(res.params[exposure]); se=float(np.sqrt(covariance[1,1])); crit=t.ppf(.975,dfree)
    low,high=beta-crit*se,beta+crit*se
    p=2*t.sf(abs(beta/se),dfree)
    for _,r in d.iterrows():MEMBERS.append({'model':label,'sample_id':r.get('sample_id',r.child_id),'child_id':r.child_id,'group':r.get('outcome_group','Sinusitis' if r.sinusitis_binary else 'URI')})
    row={'model':label,'exposure':exposure,'covariates':';'.join(x.columns[2:]),'effect_type':'odds_ratio','effect':np.exp(beta),'ci_lower':np.exp(low),'ci_upper':np.exp(high),'pvalue':p,'n_profiles':len(d) if clustered else np.nan,'n_children':d.child_id.nunique(),'positive_profiles':int(y.sum()) if clustered else np.nan,'positive_children':d.loc[y.eq(1),'child_id'].nunique(),'reference_df':dfree,'covariance':'child_cluster_CR1' if clustered else 'model_based_child_independent','weighting':'equal_child' if equal_child else 'equal_observation','rank':int(np.linalg.matrix_rank(x)),'n_parameters':x.shape[1],'condition_number':float(np.linalg.cond(x)),'converged':bool(res.converged),'fitted_min':float(res.fittedvalues.min()),'fitted_max':float(res.fittedvalues.max()),'covariance_min_eigenvalue':float(np.linalg.eigvalsh(covariance).min()),'max_abs_coefficient':float(np.abs(res.params).max()),'warnings':' | '.join(sorted(set(str(w.message) for w in caught)))}
    return row,res,d,x

def bh(rows, family):
    vals=[r['pvalue'] for r in rows]
    for r,q in zip(rows,multipletests(vals,method='fdr_bh')[1]):r.update(fdr=float(q),multiplicity_family=family)
    return rows

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    full=pd.read_csv(ROOT/'data/processed/prjeb35160_sample_metadata.tsv',sep='\t',dtype={'child_id':str,'sample_id':str})
    genus=pd.read_csv(OUT/'genus_relative_abundance.tsv',sep='\t').set_index('matrix_sample_id')
    names=sorted(genus.columns)
    a=genus[names].to_numpy(); max_idx=np.argmax(a,axis=1)
    max_name=np.array(names)[max_idx]; frac=a[np.arange(len(a)),max_idx]
    assignments=pd.DataFrame({'matrix_sample_id':genus.index,'recomputed_genus':max_name,'recomputed_fraction':frac,'tie':np.sum(np.isclose(a,frac[:,None],rtol=0,atol=1e-14),axis=1)>1})
    full=full.merge(assignments,on='matrix_sample_id',validate='one_to_one')
    full['source_genus_agreement']=full.dominant_genus.eq(full.recomputed_genus)
    full['source_fraction_difference']=full.dominant_genus_fraction-full.recomputed_fraction
    # Source labels retain their released definition; do not reinterpret as visit diagnoses.
    full['included']=full.outcome_group.isin(['URI','Sinusitis']) & full.child_id.notna()
    full['exclusion_reason']=np.where(full.included,'included','no_URI_or_Sinusitis_followup_group')
    save(full[['sample_id','child_id','outcome_group','StudySubGroup','healthy_vs_sick','Visit.Type_Lab','Surv_Sick_Recov','Sinusitis_Samp','Date','included','exclusion_reason']], 'profile_flow.tsv')
    df=full.loc[full.included].copy().reset_index(drop=True)
    assert len(full)==354 and full.child_id.nunique()==58
    assert len(df)==323 and df.child_id.nunique()==45
    assert df.groupby('child_id').sinusitis_binary.nunique().eq(1).all()
    assert np.allclose(genus.sum(axis=1),1,atol=1e-10)
    assert df.source_genus_agreement.all(), 'Source genus and recomputed maximum differ; review before fitting'
    df=pd.concat([df,genus.loc[df.matrix_sample_id,names].reset_index(drop=True)],axis=1).copy()
    for threshold in [25,30,50]:
        df[f'moraxella_{threshold}']=(df.recomputed_genus.eq('Moraxella') & df.recomputed_fraction.ge(threshold/100)).astype(int)
    df['state_label']=[state(g,f) for g,f in zip(df.recomputed_genus,df.recomputed_fraction)]
    save(df[['sample_id','child_id','outcome_group','dominant_genus','dominant_genus_fraction','recomputed_genus','recomputed_fraction','source_genus_agreement','source_fraction_difference','tie','state_label','moraxella_25','moraxella_30','moraxella_50']], 'state_assignments.tsv')
    save(full.loc[~full.source_genus_agreement | full.source_fraction_difference.abs().gt(1e-8),['sample_id','dominant_genus','recomputed_genus','dominant_genus_fraction','recomputed_fraction']], 'source_dominance_differences.tsv')
    save([{'stage':'all_released','profiles':len(full),'children':full.child_id.nunique()},{'stage':'excluded_no_group','profiles':len(full)-len(df),'children':full.loc[~full.included,'child_id'].nunique()},{'stage':'included','profiles':len(df),'children':df.child_id.nunique()}], 'cohort_flow.tsv')
    flow=full.groupby('child_id',dropna=False).agg(total_profiles=('sample_id','size'),included_profiles=('included','sum'),source_subgroups=('StudySubGroup',lambda s:';'.join(sorted(set(s.dropna().astype(str)))))).reset_index()
    save(flow,'child_flow.tsv')
    save(df.groupby(['outcome_group','Visit.Type_Lab'],dropna=False).agg(n_profiles=('sample_id','size'),n_children=('child_id','nunique')).reset_index(),'visits_by_group.tsv')
    missing=[]
    for col in ['sinusitis_binary','moraxella_30','child_id','season','daycare','tobacco_exposure','virus_count','age_init','shannon','AB_Taken']:
        missing.append({'variable':col,'n_profiles':len(df),'missing_profiles':int(df[col].isna().sum()),'observed_values':';'.join(map(str,sorted(df[col].dropna().unique(),key=str)))})
    save(missing,'covariate_coding_missingness.tsv')
    models=[]
    for label,exp,virus,eq,cov in [('primary','moraxella_30',False,False,True),('with_viral_count','moraxella_30',True,False,True),('unadjusted','moraxella_30',False,False,False),('equal_child_weight','moraxella_30',False,True,True),('cluster_I','cluster_i',False,False,True),('Shannon','shannon',False,False,True)]:
        row,res,d,x=fit(df,exp,label,virus,eq,cov)
        row.update(fdr=np.nan,multiplicity_family='single_primary_hypothesis' if label=='primary' else 'exploratory_sensitivity_no_separate_confirmatory_claim')
        models.append(row)
    save(models,'adjusted_models.tsv')
    tx=design(df,'moraxella_30');tx['tobacco_Yes']=df.tobacco_exposure.eq('Yes').astype(float)
    tr=sm.GLM(df.sinusitis_binary,tx,family=sm.families.Binomial()).fit()
    save([{'diagnosis':'quasi_complete_separation_tobacco','exposed_children':df.loc[df.tobacco_exposure.eq('Yes'),'child_id'].nunique(),'exposed_profiles':int(df.tobacco_exposure.eq('Yes').sum()),'positive_exposed_profiles':int(df.loc[df.tobacco_exposure.eq('Yes'),'sinusitis_binary'].sum()),'tobacco_coefficient':tr.params['tobacco_Yes'],'interpretation':'no_finite_MLE_for_tobacco_not_reported_as_adjusted_inference'}],'separation_diagnostics.tsv')
    restricted,_,_,_=fit(df[df.tobacco_exposure.eq('No')],'moraxella_30','no_tobacco_exposure_restriction')
    save([restricted],'no_tobacco_model.tsv')
    thresholds=[]
    for cutoff in [25,30,50]:
        row,_,d,_=fit(df,f'moraxella_{cutoff}',f'threshold_{cutoff}')
        row['threshold_percent']=cutoff
        for val,label in [(1,'exposed'),(0,'unexposed')]:
            sub=d[d[f'moraxella_{cutoff}']==val]
            row[label+'_profiles']=len(sub);row[label+'_positive_profiles']=int(sub.sinusitis_binary.sum());row[label+'_children']=sub.child_id.nunique()
        thresholds.append(row)
    save(bh(thresholds,'three_threshold_sensitivity_tests'),'threshold_sensitivity.tsv')
    save([{'comparison':'25_vs_30','identical':bool(df.moraxella_25.eq(df.moraxella_30).all()),'changed_profiles':int(df.moraxella_25.ne(df.moraxella_30).sum()),'minimum_Moraxella_fraction':df.loc[df.recomputed_genus.eq('Moraxella'),'recomputed_fraction'].min()}],'threshold_agreement.tsv')
    genera=[]
    for g in FOCUS:
        d=df.copy();d['abundance_10pct']=d[g]/.10
        row,_,_,_=fit(d,'abundance_10pct','genus_'+g)
        row['genus']=g
        for group in ['URI','Sinusitis']:
            row['median_fraction_'+group]=float(d.loc[d.outcome_group.eq(group),g].median())
        genera.append(row)
    save(bh(genera,'six_focused_genus_models'),'genus_models.tsv')
    child=df.groupby('child_id').agg(sinusitis_binary=('sinusitis_binary','first'),n_profiles=('sample_id','size'),moraxella_fraction=('moraxella_30','mean'),mean_shannon=('shannon','mean'),age_init=('age_init','first'),daycare=('daycare','first'),tobacco_exposure=('tobacco_exposure','first')).reset_index()
    child['burden_25pct']=child.moraxella_fraction/.25
    save(child,'child_burden.tsv')
    row,_,_,_=fit(child,'burden_25pct','child_burden_per_25pct',covariates=False,clustered=False)
    save([row],'child_burden_model.tsv')
    descriptions=[]
    for group,y in [('URI',0),('Sinusitis',1)]:
        c=child[child.sinusitis_binary==y];d=df[df.sinusitis_binary==y]
        descriptions.append({'group':group,'n_profiles':len(d),'n_children':len(c),'profiles_per_child_median':c.n_profiles.median(),'profiles_per_child_min':c.n_profiles.min(),'profiles_per_child_max':c.n_profiles.max(),'profiles_per_child_q1':c.n_profiles.quantile(.25),'profiles_per_child_q3':c.n_profiles.quantile(.75),'burden_median':c.moraxella_fraction.median(),'baseline_age_min':c.age_init.min(),'baseline_age_max':c.age_init.max(),'shannon_profile_median':d.shannon.median(),'daycare_yes_children':int(c.daycare.eq('Yes').sum()),'tobacco_yes_children':int(c.tobacco_exposure.eq('Yes').sum())})
    save(descriptions,'group_descriptives.tsv')
    earliest=df.assign(date_order=pd.to_datetime(df.Date)).sort_values(['child_id','date_order','sample_id']).groupby('child_id',sort=False).head(1)
    erow,_,_,_=fit(earliest,'moraxella_30','earliest_profile_per_child')
    save([erow],'earliest_profile_model.tsv')
    # Whole-child bootstrap of the adjusted GLMs; covariates and columns stay fixed.
    rng=np.random.default_rng(SEED);ids=sorted(df.child_id.unique());indices=[np.flatnonzero(df.child_id.eq(c)) for c in ids]
    x0=design(df,'moraxella_30',False).to_numpy();xv=design(df,'moraxella_30',True).to_numpy();y=df.sinusitis_binary.to_numpy().astype(float)
    obs=[]
    for label,x in [('primary',x0),('with_viral_count',xv)]:
        r=sm.GLM(y,x,family=sm.families.Binomial()).fit()
        a=x.copy();b=x.copy();a[:,1]=0;b[:,1]=1
        p0=expit(a@r.params).mean();p1=expit(b@r.params).mean()
        obs.append({'model':label,'odds_ratio':float(np.exp(r.params[1])),'standardized_probability_unexposed':p0,'standardized_probability_exposed':p1,'standardized_proportion_ratio':p1/p0})
    boot=[];crude=[]
    for iteration in range(BOOTSTRAPS):
        ix=np.concatenate([indices[i] for i in rng.integers(0,len(ids),len(ids))]);yb=y[ix]
        raw0=yb[x0[ix,1]==0].mean();raw1=yb[x0[ix,1]==1].mean()
        crude.append({'iteration':iteration,'raw_unexposed_proportion':raw0,'raw_exposed_proportion':raw1,'unadjusted_proportion_ratio':raw1/raw0})
        for label,x in [('primary',x0),('with_viral_count',xv)]:
            xb=x[ix]
            failure=''
            try:
                with warnings.catch_warnings(record=True) as caught:
                    warnings.simplefilter('always');r=sm.GLM(yb,xb,family=sm.families.Binomial()).fit(maxiter=100)
                if np.linalg.matrix_rank(xb)<xb.shape[1]:raise ValueError('rank_deficient_resample')
                if not r.converged:raise ValueError('not_converged')
                if not np.isfinite(r.params).all() or np.abs(r.params).max()>20:raise ValueError('nonfinite_or_nuisance_separation')
                if any('separation' in str(w.message).lower() for w in caught):raise ValueError('separation_warning')
                a=xb.copy();b=xb.copy();a[:,1]=0;b[:,1]=1
                p0=expit(a@r.params).mean();p1=expit(b@r.params).mean()
                rr=yb[xb[:,1]==1].mean()/yb[xb[:,1]==0].mean()
                if not np.isfinite(rr):raise ValueError('nonfinite_crude_ratio')
                boot.append({'iteration':iteration,'model':label,'status':'success','odds_ratio':np.exp(r.params[1]),'standardized_probability_unexposed':p0,'standardized_probability_exposed':p1,'standardized_proportion_ratio':p1/p0,'unadjusted_proportion_ratio':rr,'raw_unexposed_proportion':yb[xb[:,1]==0].mean(),'raw_exposed_proportion':yb[xb[:,1]==1].mean()})
            except Exception as e:
                failure=str(e);boot.append({'iteration':iteration,'model':label,'status':failure})
        if (iteration+1)%500==0:print('bootstrap',iteration+1,'/',BOOTSTRAPS,flush=True)
    bootdf=pd.DataFrame(boot);save(bootdf,'bootstrap_draws.tsv')
    crudedf=pd.DataFrame(crude);save(crudedf,'bootstrap_crude_draws.tsv')
    summaries=[]
    for o in obs:
        b=bootdf[(bootdf.model==o['model']) & bootdf.status.eq('success')]
        for metric in ['odds_ratio','standardized_probability_unexposed','standardized_probability_exposed','standardized_proportion_ratio']:
            low,high=b[metric].quantile([.025,.975])
            summaries.append({'model':o['model'],'metric':metric,'estimate':o[metric],'ci_lower':low,'ci_upper':high,'requested':BOOTSTRAPS,'successful':len(b),'failed':BOOTSTRAPS-len(b),'interval':'percentile','seed':SEED})
    expose=df[df.moraxella_30==1];other=df[df.moraxella_30==0]
    rr=expose.sinusitis_binary.mean()/other.sinusitis_binary.mean()
    b=crudedf[np.isfinite(crudedf.unadjusted_proportion_ratio)]
    low,high=b.unadjusted_proportion_ratio.quantile([.025,.975])
    summaries.append({'model':'unadjusted','metric':'profile_proportion_ratio','estimate':rr,'ci_lower':low,'ci_upper':high,'requested':BOOTSTRAPS,'successful':len(b),'failed':BOOTSTRAPS-len(b),'interval':'percentile_child_cluster','seed':SEED})
    for val,label in [(0,'other'),(1,'Moraxella-dominant')]:
        sel=df.moraxella_30.eq(val);point=df.loc[sel,'sinusitis_binary'].mean()
        values=b['raw_exposed_proportion' if val else 'raw_unexposed_proportion'].to_numpy()
        lo,hi=np.quantile(values,[.025,.975])
        summaries.append({'model':label,'metric':'group_profile_proportion','estimate':point,'ci_lower':lo,'ci_upper':hi,'requested':BOOTSTRAPS,'successful':len(values),'failed':BOOTSTRAPS-len(values),'interval':'percentile_child_cluster','seed':SEED})
    save(summaries,'bootstrap_summary.tsv')
    loo=[]
    for c in ids:
        row,_,_,_=fit(df[df.child_id!=c],'moraxella_30','loo_'+c)
        row['omitted_child']=c;loo.append(row)
    save(loo,'leave_one_child_out.tsv')
    save([{'estimate_min':min(r['effect'] for r in loo),'estimate_max':max(r['effect'] for r in loo),'n_fits':len(loo),'interpretation':'influence_range_not_confidence_interval'}],'leave_one_child_out_summary.tsv')
    save(MEMBERS,'model_membership.tsv')
    inputs=[ROOT/'data/references/sinusitis_microbiome/AnalysisPhyloseq.rds',ROOT/'data/processed/prjeb35160_sample_metadata.tsv',ROOT/'scripts/analyze_primary.py',ROOT/'docs/STATISTICAL_DECISION_RULES.md',ROOT/'scripts/state_classification.py']
    provenance={'seed':SEED,'bootstrap_requested':BOOTSTRAPS,'software':{'python':platform.python_version(),'numpy':np.__version__,'pandas':pd.__version__,'scipy':scipy.__version__,'statsmodels':statsmodels.__version__},'input_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},'endpoint':'source-defined_child_followup_group','interpretation':'descriptive_association_not_future_risk','prospectively_preregistered':False}
    (OUT/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    print(pd.DataFrame(models)[['model','effect','ci_lower','ci_upper','pvalue','n_children']].to_string(index=False))

if __name__=='__main__':main()
