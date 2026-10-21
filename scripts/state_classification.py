"""Shared dominant-genus rule; abundance and threshold must use the same units."""
import math

ANAEROBES = frozenset({'Fusobacterium', 'Porphyromonas', 'Prevotella', 'Alloprevotella'})
LABELS = {'mixed': 'Mixed community', 'anaerobe_dominant': 'Fusobacterium/anaerobe-dominant',
          'other_dominant': 'Other-dominant', **{g.lower() + '_dominant': g + '-dominant'
          for g in ('Moraxella', 'Haemophilus', 'Streptococcus', 'Neisseria')}}

def unclassified(genus):
    name = str(genus).strip().casefold()
    return name in {'', 'nan', 'none', 'na'} or name.startswith(('unclassified', 'unknown', 'uncultured'))

def state_key(genus, abundance, threshold):
    if unclassified(genus) or not math.isfinite(abundance) or abundance < threshold:
        return 'mixed'
    if genus in ANAEROBES:
        return 'anaerobe_dominant'
    if genus in {'Moraxella', 'Haemophilus', 'Streptococcus', 'Neisseria'}:
        return genus.lower() + '_dominant'
    return 'other_dominant'
