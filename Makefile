PYTHON ?= python3

.PHONY: setup metadata processed external-labels primary transfer state-transfer figures reproduce clean-outputs

setup:
	mkdir -p data/raw/metadata data/processed data/references/external_labels data/references/sinusitis_microbiome docs plots/diagnostic/pdf plots/diagnostic/png plots/publication/pdf plots/publication/png results/benchmarks results/effect_sizes results/figures results/primary results/recon results/replication results/tables

metadata: setup
	$(PYTHON) scripts/acquire_metadata.py

processed: setup
	$(PYTHON) scripts/acquire_processed_artifacts.py

external-labels: metadata
	$(PYTHON) scripts/acquire_external_labels.py

primary: metadata processed
	Rscript scripts/analyze_primary_prjeb35160.R

transfer: external-labels
	$(PYTHON) scripts/analyze_prjna422760_transfer.py

state-transfer: transfer primary
	$(PYTHON) scripts/analyze_state_taxonomy_transportability.py

figures: primary state-transfer
	$(PYTHON) scripts/generate_publication_figures.py

reproduce:
	bash scripts/reproduce_one_click.sh

clean-outputs:
	rm -rf data/raw/metadata data/processed data/references/external_labels data/references/sinusitis_microbiome plots/diagnostic plots/publication results
