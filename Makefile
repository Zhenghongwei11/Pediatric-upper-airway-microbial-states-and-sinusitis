.NOTPARALLEL:
PYTHON ?= python3
.PHONY: all acquire analyze figures tables check
all: acquire analyze figures tables check
acquire:
	$(PYTHON) scripts/acquire_public_inputs.py
analyze:
	Rscript scripts/export_primary_inputs.R
	$(PYTHON) scripts/analyze_primary.py
	Rscript scripts/analyze_primary_community.R
	$(PYTHON) scripts/analyze_external_cohort.py
figures:
	$(PYTHON) scripts/generate_publication_figures.py
tables:
	$(PYTHON) scripts/main_tables.py
	$(PYTHON) scripts/build_supplementary_tables.py
check:
	$(PYTHON) scripts/check_results.py
