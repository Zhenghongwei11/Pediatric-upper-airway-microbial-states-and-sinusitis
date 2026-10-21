#!/usr/bin/env python3
"""Generate publication figures from the analysis tables; no model fitting."""
from pathlib import Path
import hashlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Patch
from matplotlib.ticker import FixedLocator, FuncFormatter, NullLocator

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'results/primary'
E = ROOT / 'results/external'
OUT = ROOT / 'plots/publication'
MAP = ROOT / 'results/figures'
for p in [OUT / 'png', OUT / 'pdf', MAP]: p.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 9, 'axes.labelsize': 9,
    'axes.titlesize': 10, 'xtick.labelsize': 8, 'ytick.labelsize': 8,
    'axes.spines.top': False, 'axes.spines.right': False, 'pdf.fonttype': 42,
    'axes.linewidth': .7, 'savefig.facecolor': 'white'})
BLUE, ORANGE, GREEN, PURPLE, GREY = '#0072B2', '#D55E00', '#009E73', '#CC79A7', '#777777'
SOURCE_MAP = []
def read(d, f): return pd.read_csv(d / f, sep='\t')
def source(fig, panel, d, filename, columns, computation):
    path = d / filename
    SOURCE_MAP.append({'figure': fig, 'panel': panel, 'source_file': str(path.relative_to(ROOT)),
        'source_sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'columns': columns,
        'calculation_or_selection': computation})
def panel(ax, letter, title):
    ax.set_title(title, loc='left', pad=12)
    ax.text(-.10, 1.075, letter, transform=ax.transAxes, fontsize=12, weight='bold', va='bottom')
def save(fig, n):
    fig.savefig(OUT / 'png' / f'Figure{n}.png', dpi=600)
    fig.savefig(OUT / 'pdf' / f'Figure{n}.pdf')
    plt.close(fig)
def forest(ax, rows, labels, colors=None, xlim=None):
    colors = colors or [BLUE] * len(rows)
    for i, (r, color) in enumerate(zip(rows, colors)):
        ax.errorbar(r['effect'], i, xerr=[[r['effect'] - r['ci_lower']], [r['ci_upper'] - r['effect']]],
                    fmt='o', color=color, markersize=4.5, capsize=3, lw=1.2)
    ax.axvline(1, color=GREY, ls='--', lw=.8, zorder=0)
    ax.set_yticks(range(len(rows)), labels)
    ax.invert_yaxis(); ax.set_xscale('log'); ax.grid(axis='x', alpha=.12)
    if xlim: ax.set_xlim(*xlim)
    ticks = [.1, .25, .5, .8, 1, 1.2, 1.5, 2, 3, 4]
    if xlim and xlim[1] > 2: ticks = [.1, .25, .5, 1, 2, 4]
    ax.xaxis.set_major_locator(FixedLocator([x for x in ticks if ax.get_xlim()[0] <= x <= ax.get_xlim()[1]]))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f'{x:g}'))
    ax.xaxis.set_minor_locator(NullLocator())
    ax.set_xlabel('Odds ratio (95% CI)')
    ax.set_ylim(len(rows)-.55, -.55)

# Figure 1: transparent profile/child flow.
flow = read(P, 'cohort_flow.tsv').set_index('stage')
support = read(E, 'sample_support.tsv')
fig, axes = plt.subplots(1, 2, figsize=(8.0, 4.2))
fig.subplots_adjust(left=.05, right=.98, top=.86, bottom=.07, wspace=.14)
def box(ax, x, y, w, h, text, fill='#EAF3F8'):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.012,rounding_size=0.02',
                             facecolor=fill, edgecolor='#526570', lw=.9))
    ax.text(x+w/2, y+h/2, text, ha='center', va='center', fontsize=9, linespacing=1.5)
def arrow(ax, a, b): ax.annotate('', xy=b, xytext=a, arrowprops={'arrowstyle':'->', 'color':'#526570', 'lw':1})
for ax in axes: ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis('off')
axes[0].set_title('A  Primary follow-up cohort', loc='left', weight='bold', pad=14)
box(axes[0], .1, .79, .8, .17, f"Released profiles\n{int(flow.loc['all_released','profiles'])} profiles · {int(flow.loc['all_released','children'])} children")
arrow(axes[0],(.5,.65),(.5,.62))
box(axes[0], .1, .43, .8, .18, 'Eligible follow-up outcome groups\n323 profiles · 45 children')
box(axes[0], .1, .04, .37, .20, 'URI group\n180 profiles\n26 children')
box(axes[0], .53, .04, .37, .20, 'Sinusitis group\n143 profiles\n19 children')
arrow(axes[0],(.5,.42),(.285,.25)); arrow(axes[0],(.5,.42),(.715,.25))
axes[0].text(.5,.70,'Excluded: 31 profiles / 13 children\nNo URI or Sinusitis group label',ha='center',va='center',fontsize=8,color='#4E5559')
axes[1].set_title('B  Independent paired anatomy cohort', loc='left', weight='bold', pad=14)
box(axes[1], .1, .79, .8, .17, 'Released sequencing profiles\n56 profiles · 28 children')
arrow(axes[1],(.5,.65),(.5,.62))
box(axes[1], .1, .43, .8, .18, 'One adenoid + one tonsil per child\n28 complete tissue pairs')
box(axes[1], .1, .04, .37, .20, 'HP group\n28 profiles\n14 children')
box(axes[1], .53, .04, .37, .20, 'SOM group\n28 profiles\n14 children')
arrow(axes[1],(.5,.42),(.285,.25)); arrow(axes[1],(.5,.42),(.715,.25))
axes[1].text(.5,.70,'HP: hyperplasia\nSOM: secretory otitis media',ha='center',va='center',fontsize=8,color='#4E5559')
save(fig, 1)
source(1,'A',P,'cohort_flow.tsv','stage;profiles;children','All released, excluded_no_group and included counts')
source(1,'A',P,'group_descriptives.tsv','group;n_profiles;n_children','URI and Sinusitis group counts')
source(1,'B',E,'sample_support.tsv','clinical_group;tissue;n_samples;n_patients','Sum two tissues per clinical group; each patient occurs in both tissues')

# Figure 2: proportions and distinct association measures.
b = read(P, 'bootstrap_summary.tsv'); models = read(P, 'adjusted_models.tsv').set_index('model')
fig, axes = plt.subplots(1, 3, figsize=(8.0, 3.5))
fig.subplots_adjust(left=.09, right=.98, top=.77, bottom=.25, wspace=.65)
ax = axes[0]; panel(ax,'A','Observed group-label\nproportions')
for i,(group,label,col) in enumerate([('other','Other profiles',GREY),('Moraxella-dominant','Moraxella\ndominant',BLUE)]):
    r=b[(b.model==group)&(b.metric=='group_profile_proportion')].iloc[0]
    ax.errorbar(i,100*r.estimate,yerr=[[100*(r.estimate-r.ci_lower)],[100*(r.ci_upper-r.estimate)]],fmt='o',color=col,capsize=4,ms=5)
    ax.text(i,100*r.ci_upper+3, ['58 / 159','85 / 164'][i],ha='center',fontsize=8)
ax.set_xticks([0,1],['Other\nprofiles','Moraxella\ndominant']);ax.set_xlim(-.55,1.55);ax.set_ylim(0,82)
ax.set_ylabel('Profiles from Sinusitis-group children (%)')
panel(axes[1],'B','Adjusted odds ratio')
r=models.loc['primary']; forest(axes[1],[r],[''],xlim=(.7,4.1));axes[1].set_yticks([])
axes[1].text(.5,.95,f"{r.effect:.2f} ({r.ci_lower:.2f}–{r.ci_upper:.2f})",transform=axes[1].transAxes,ha='center',fontsize=8)
panel(axes[2],'C','Standardized\nproportion ratio')
r=b[(b.model=='primary')&(b.metric=='standardized_proportion_ratio')].iloc[0]
axes[2].errorbar(r.estimate,0,xerr=[[r.estimate-r.ci_lower],[r.ci_upper-r.estimate]],fmt='s',color=GREEN,capsize=4,ms=5)
axes[2].axvline(1,color=GREY,ls='--',lw=.8);axes[2].set_yticks([]);axes[2].set_xlim(.7,2.1);axes[2].set_ylim(-.55,.55)
axes[2].set_xlabel('Proportion ratio (95% CI)');axes[2].text(.5,.95,f'{r.estimate:.2f} ({r.ci_lower:.2f}–{r.ci_upper:.2f})',transform=axes[2].transAxes,ha='center',fontsize=8)
fig.text(.5,.06,'323 profiles / 45 children · Exposure: Moraxella dominance ≥30%\nA: whole-child bootstrap (2,000/2,000); B: child-cluster t interval; C: bootstrap (1,915/2,000 estimable fits)',ha='center',fontsize=8)
save(fig,2)
source(2,'A',P,'bootstrap_summary.tsv','model;metric;estimate;ci_lower;ci_upper;successful','group_profile_proportion for other and Moraxella-dominant; multiply by 100')
source(2,'A',P,'threshold_sensitivity.tsv','threshold_percent;exposed_profiles;exposed_positive_profiles;unexposed_profiles;unexposed_positive_profiles','30% numerator/denominator annotations')
source(2,'B',P,'adjusted_models.tsv','model;effect;ci_lower;ci_upper','Primary season/daycare adjusted model; clustered CR1 t44 interval')
source(2,'C',P,'bootstrap_summary.tsv','model;metric;estimate;ci_lower;ci_upper;successful;requested','Primary standardized_proportion_ratio; percentile interval conditional on estimable fits')

# Figure 3: genus associations and descriptive profile abundances.
g=read(P,'genus_models.tsv');md=pd.read_csv(ROOT/'data/processed/prjeb35160_sample_metadata.tsv',sep='\t'); abund=read(P,'genus_relative_abundance.tsv')
a=md[['matrix_sample_id','outcome_group']].merge(abund,on='matrix_sample_id');a=a[a.outcome_group.isin(['URI','Sinusitis'])]
fig,axes=plt.subplots(1,2,figsize=(8,4.3));fig.subplots_adjust(left=.21,right=.98,top=.85,bottom=.27,wspace=.65)
panel(axes[0],'A','Adjusted genus associations')
forest(axes[0],[r for _,r in g.iterrows()],g.genus.tolist(),xlim=(.7,1.5))
axes[0].set_xlabel('Odds ratio per 10 percentage points\n(95% child-cluster CI)')
for i,r in g.iterrows(): axes[0].text(1.48,i,f'q={r.fdr:.3f}',ha='right',va='center',fontsize=7)
panel(axes[1],'B','Relative-abundance distributions')
for j,(group,col,mark,offset) in enumerate([('URI',BLUE,'o',-.12),('Sinusitis',ORANGE,'s',.12)]):
 for i,genus in enumerate(g.genus):
  q=np.quantile(a.loc[a.outcome_group==group,genus].to_numpy()*100,[.25,.5,.75])
  axes[1].errorbar(q[1],i+offset,xerr=[[q[1]-q[0]],[q[2]-q[1]]],fmt=mark,color=col,ms=4,lw=1.2,capsize=2,label=group if i==0 else None)
axes[1].set_yticks(range(6),['']*6);axes[1].set_ylim(5.55,-.55);axes[1].set_xscale('symlog',linthresh=.1);axes[1].set_xlim(-.02,105)
axes[1].set_xticks([0,.1,1,10,100],['0','0.1','1','10','100']);axes[1].set_xlabel('Relative abundance (%)\nProfile median and interquartile range')
axes[1].legend(frameon=False,fontsize=8,loc='center right',bbox_to_anchor=(1,.70))
fig.text(.5,.045,'323 profiles / 45 children · Each genus fitted separately with season and daycare\nq: Benjamini–Hochberg adjustment across six models; descriptive profiles are repeated within children',ha='center',fontsize=8)
save(fig,3)
source(3,'A',P,'genus_models.tsv','genus;effect;ci_lower;ci_upper;fdr','Six per-10-percentage-point models; BH family of six')
source(3,'B',P,'genus_relative_abundance.tsv','matrix_sample_id;Moraxella;Haemophilus;Streptococcus;Staphylococcus;Corynebacterium;Alloiococcus','Join sample metadata by matrix_sample_id; URI/Sinusitis profile quantiles [25,50,75], multiply by 100')
source(3,'B',ROOT/'data/processed','prjeb35160_sample_metadata.tsv','matrix_sample_id;outcome_group','Restrict to URI/Sinusitis follow-up outcome groups')

# Figure 4: sensitivity intervals, influence ranges and raw child burden.
t=read(P,'threshold_sensitivity.tsv');earliest=read(P,'earliest_profile_model.tsv').iloc[0];burden=read(P,'child_burden.tsv');loo=read(P,'leave_one_child_out_summary.tsv').iloc[0]
fig,axes=plt.subplots(2,2,figsize=(8.2,6.3));fig.subplots_adjust(left=.22,right=.98,top=.92,bottom=.22,wspace=.58,hspace=1.0)
ax=axes[0,0];panel(ax,'A','Dominance thresholds')
forest(ax,[r for _,r in t.iterrows()],['25%','30%','50%'],xlim=(.7,4.4))
for i,r in t.iterrows(): ax.text(4.25,i,f'q={r.fdr:.3f}',ha='right',va='center',fontsize=7)

ax=axes[0,1];panel(ax,'B','Weighting and profile selection')
forest(ax,[models.loc['primary'],models.loc['equal_child_weight'],earliest],['All profiles','Equal child weight','Earliest eligible\nprofile / child'],[BLUE,GREEN,ORANGE],xlim=(.075,5))
ax=axes[1,0];panel(ax,'C','Uncertainty and influence')
r=models.loc['primary'];br=b[(b.model=='primary')&(b.metric=='odds_ratio')].iloc[0]
for y,est,lo,hi,col,mark in [(0,r.effect,r.ci_lower,r.ci_upper,BLUE,'o'),(1,br.estimate,br.ci_lower,br.ci_upper,GREEN,'s'),(2,r.effect,loo.estimate_min,loo.estimate_max,GREY,'D')]:
 ax.errorbar(est,y,xerr=[[est-lo],[hi-est]],fmt=mark,color=col,capsize=3,ms=4.5,lw=1.2)
ax.axvline(1,color=GREY,ls='--',lw=.8);ax.set_xscale('log');ax.set_xlim(.7,4.4);ax.set_ylim(2.55,-.55)
ax.set_yticks(range(3),['Cluster 95% CI','Bootstrap 95% CI','Leave-one-child-out\npoint-estimate range']);ax.set_xlabel('Odds ratio')
ax.xaxis.set_major_locator(FixedLocator([1,2,4]));ax.xaxis.set_major_formatter(FuncFormatter(lambda x,_: f'{x:g}'));ax.xaxis.set_minor_locator(NullLocator())

ax=axes[1,1];panel(ax,'D','Moraxella burden by child')
rng=np.random.default_rng(20261020)
for i,(group,col,label) in enumerate([(0,BLUE,'URI'),(1,ORANGE,'Sinusitis')]):
 vals=burden.loc[burden.sinusitis_binary==group,'moraxella_fraction'].to_numpy()*100
 ax.scatter(i+rng.uniform(-.15,.15,len(vals)),vals,s=18,facecolor='none',edgecolor=col,lw=.8)
 ax.plot([i-.22,i+.22],[np.median(vals)]*2,color=col,lw=2)
ax.set_xticks([0,1],['URI\n26 children','Sinusitis\n19 children']);ax.set_xlim(-.5,1.5);ax.set_ylim(-4,104);ax.set_ylabel('Moraxella-dominant profiles\nper child (%)')
fig.text(.52,.025,'A: 25% and 30% classifications are identical; q adjusts three threshold tests.\nA–B: child-cluster 95% CIs; earliest eligible profile is not necessarily before illness.\nC: bootstrap 1,915/2,000 estimable draws; influence range is not a CI. D: bars mark group medians.',ha='center',fontsize=8)
save(fig,4)
source(4,'A',P,'threshold_sensitivity.tsv','threshold_percent;effect;ci_lower;ci_upper;fdr','Three thresholds with BH across three sensitivity tests')
source(4,'B',P,'adjusted_models.tsv','model;effect;ci_lower;ci_upper','Primary and equal_child_weight rows')
source(4,'B',P,'earliest_profile_model.tsv','effect;ci_lower;ci_upper','One earliest eligible profile per child, not necessarily before illness')
source(4,'C',P,'adjusted_models.tsv','model;effect;ci_lower;ci_upper','Primary clustered analytical interval')
source(4,'C',P,'bootstrap_summary.tsv','model;metric;estimate;ci_lower;ci_upper;successful;requested','Primary OR percentile 95% CI conditional on estimability')
source(4,'C',P,'leave_one_child_out_summary.tsv','estimate_min;estimate_max;n_fits','45 omitted-child point estimates; min/max range, not CI')
source(4,'D',P,'child_burden.tsv','sinusitis_binary;moraxella_fraction','Each child once; fraction times100; deterministic jitter; horizontal sample median')

# Figure 5: anatomy context and actual paired differences.
states=read(P,'state_assignments.tsv');ext=read(E,'sample_states.tsv');ext=ext[ext.threshold_percent==30]
state_keys=['moraxella_dominant','haemophilus_dominant','streptococcus_dominant','anaerobe_dominant','neisseria_dominant','other_dominant','mixed']
state_labels=['Moraxella','Haemophilus','Streptococcus','Anaerobe','Neisseria','Other genus','Mixed']
colors=[BLUE,ORANGE,'#E69F00',GREEN,PURPLE,'#56B4E9','#C8C8C8']
hatches=['','//','..','\\\\','xx','++','']
lookup={'Moraxella-dominant':'moraxella_dominant','Haemophilus-dominant':'haemophilus_dominant','Streptococcus-dominant':'streptococcus_dominant','Fusobacterium/anaerobe-dominant':'anaerobe_dominant','Neisseria-dominant':'neisseria_dominant','Other-dominant':'other_dominant','Mixed community':'mixed'}
states['key']=states.state_label.map(lookup);assert states.key.notna().all()
fig=plt.figure(figsize=(8.1,6.4));gs=fig.add_gridspec(2,2,height_ratios=[1.1,1],left=.12,right=.98,top=.91,bottom=.12,hspace=.85,wspace=.42)
ax=fig.add_subplot(gs[0,:]);panel(ax,'A','Dominant community states (30% threshold)')
sets=[states[states.outcome_group=='URI'].key,states[states.outcome_group=='Sinusitis'].key]
for group,tissue in [('HP','adenoid'),('HP','tonsil'),('SOM','adenoid'),('SOM','tonsil')]: sets.append(ext[(ext.clinical_group==group)&(ext.tissue==tissue)].state_key)
labels=['URI\n(n=180)','Sinusitis\n(n=143)','HP adenoid\n(n=14)','HP tonsil\n(n=14)','SOM adenoid\n(n=14)','SOM tonsil\n(n=14)']
bottom=np.zeros(6)
for key,label,col,hatch in zip(state_keys,state_labels,colors,hatches):
 vals=np.array([(s==key).mean()*100 for s in sets]);ax.bar(range(6),vals,bottom=bottom,color=col,edgecolor='white',lw=.5,label=label,hatch=hatch);bottom+=vals
assert np.allclose(bottom,100)
ax.axvline(1.5,color='#555555',lw=.8,ls=':');ax.set_xticks(range(6),labels);ax.set_ylim(0,100);ax.set_ylabel('Profiles (%)')
ax.legend(handles=[Patch(facecolor=c,hatch=h,edgecolor='white',label=l) for c,h,l in zip(colors,hatches,state_labels)],loc='upper center',bbox_to_anchor=(.5,-.29),ncol=4,frameon=False,fontsize=7.5,handlelength=1.5,columnspacing=1.3)
diffs=read(E,'patient_paired_differences.tsv');eff=read(E,'paired_genus_effects.tsv');patient_groups=ext[['patient_id','clinical_group']].drop_duplicates()
for j,genus in enumerate(['Moraxella','Haemophilus']):
 ax=fig.add_subplot(gs[1,j]);panel(ax,['B','C'][j],f'Paired {genus} abundance')
 data=diffs[diffs.genus==genus].merge(patient_groups,on='patient_id');y=data.difference_tonsil_minus_adenoid.to_numpy()
 rng=np.random.default_rng(20261020+j)
 for group,col,mark in [('HP',BLUE,'o'),('SOM',ORANGE,'s')]:
  yy=data.loc[data.clinical_group==group,'difference_tonsil_minus_adenoid'].to_numpy();ax.scatter(rng.uniform(-.13,.13,len(yy)),yy,marker=mark,facecolor='none',edgecolor=col,s=24,lw=.9,label=group)
 r=eff[(eff.genus==genus)&(eff.clinical_group=='all')].iloc[0];assert np.isclose(np.median(y),r.median_paired_difference)
 ax.plot([-.24,.24],[r.median_paired_difference]*2,color='black',lw=2)
 ax.axhline(0,color=GREY,ls='--',lw=.8);ax.set_xlim(-.5,.5);ax.set_xticks([]);ax.set_ylabel('Tonsil − adenoid\n(percentage points)')
 ax.text(.98,.60,f'Median {r.median_paired_difference:.2f} pp\nBH q={r.p_bh:.4f}',transform=ax.transAxes,ha='right',va='top',fontsize=8)
 if j==0: ax.legend(loc='lower right',frameon=False,fontsize=8)
fig.text(.5,.025,'A: descriptive profile proportions across separate cohorts. B–C: 28 paired children (14 HP, 14 SOM);\npoints show individual differences; black line shows paired median; q adjusts 27 paired genus-by-group tests.',ha='center',fontsize=8)
save(fig,5)
source(5,'A',P,'state_assignments.tsv','outcome_group;state_label','State count divided by all profiles in each primary group; 30% dominance classification')
source(5,'A',E,'sample_states.tsv','threshold_percent;clinical_group;tissue;state_key','Select30%; state count divided by14profiles per tissue/group; preserve published percentages')
source(5,'B,C',E,'patient_paired_differences.tsv','patient_id;genus;difference_tonsil_minus_adenoid','Moraxella/Haemophilus: plot28 patient differences, true median difference (not difference of medians)')
source(5,'B,C',E,'sample_states.tsv','patient_id;clinical_group','One unique clinical group per patient; marker/categorical color')
source(5,'B,C',E,'paired_genus_effects.tsv','clinical_group;genus;median_paired_difference;p_bh','All28patients median and BH across27paired genus-by-group tests; no uncertainty interval implied')
source_map = pd.DataFrame(SOURCE_MAP)
source_map.to_csv(MAP/'source_map.tsv',sep='\t',index=False)
provenance_rows = []
for (figure, panel_name), group in source_map.groupby(['figure', 'panel'], sort=True):
    anchors = sorted(group.source_file.unique())
    provenance_rows.append({
        'figure_id': f'Figure{figure}',
        'panel': panel_name,
        'generating_script': 'scripts/generate_publication_figures.py',
        'anchor_table': ';'.join(anchors),
        'status': 'generated_from_analysis_tables',
    })
pd.DataFrame(provenance_rows).to_csv(ROOT/'docs/FIGURE_PROVENANCE.tsv',sep='\t',index=False)
print('Rendered 5 figures as 600-dpi PNG and vector PDF; wrote hashed panel source map.')
