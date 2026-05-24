#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(phyloseq)
  library(dplyr)
  library(readr)
  library(ggplot2)
  library(lme4)
  library(vegan)
})

root <- normalizePath(getwd(), mustWork = TRUE)
if (!file.exists(file.path(root, "Makefile")) || !dir.exists(file.path(root, "data"))) {
  stop("Run this script from the project root, for example: Rscript scripts/analyze_primary_prjeb35160.R")
}
permutation_count <- as.integer(Sys.getenv("PERMUTATIONS", "99"))
bootstrap_iterations <- as.integer(Sys.getenv("BOOTSTRAP_ITERATIONS", "100"))

dir_create <- function(path) {
  if (!dir.exists(path)) dir.create(path, recursive = TRUE, showWarnings = FALSE)
}

compact_message <- function(x) {
  gsub("\\s+", " ", trimws(x))
}

clean_taxon_label <- function(x) {
  x <- as.character(x)
  x <- sub("^.*g__", "", x)
  x[x == "" | is.na(x)] <- "Unclassified"
  x
}

wald_or <- function(model, term, claim_id, dataset_id, outcome, model_label) {
  coef_table <- summary(model)$coefficients
  if (!term %in% rownames(coef_table)) {
    return(NULL)
  }
  beta <- coef_table[term, "Estimate"]
  se <- coef_table[term, "Std. Error"]
  pvalue <- coef_table[term, grep("Pr\\(", colnames(coef_table), value = TRUE)[1]]
  data.frame(
    claim_id = claim_id,
    dataset_id = dataset_id,
    outcome = outcome,
    model = model_label,
    exposure = term,
    effect_type = "odds_ratio",
    effect = exp(beta),
    ci_lower = exp(beta - 1.96 * se),
    ci_upper = exp(beta + 1.96 * se),
    pvalue = pvalue,
    fdr = NA_real_,
    n = stats::nobs(model),
    analysis_status = "estimated",
    stringsAsFactors = FALSE
  )
}

safe_wald_or <- function(formula, data, term, claim_id, outcome, model_label) {
  model <- tryCatch(glm(formula, data = data, family = binomial()), error = function(e) NULL)
  if (is.null(model)) {
    return(NULL)
  }
  wald_or(model, term, claim_id, "PRJEB35160", outcome, model_label)
}

risk_ratio_row <- function(df, exposure, claim_id, label) {
  tab <- table(df[[exposure]], df$sinusitis_binary)
  levels_needed <- c("FALSE", "TRUE")
  for (level in levels_needed) {
    if (!level %in% rownames(tab)) {
      tab <- rbind(tab, setNames(c(0, 0), colnames(tab)))
      rownames(tab)[nrow(tab)] <- level
    }
  }
  tab <- tab[levels_needed, c("0", "1"), drop = FALSE]
  exposed_events <- tab["TRUE", "1"]
  exposed_total <- sum(tab["TRUE", ])
  unexposed_events <- tab["FALSE", "1"]
  unexposed_total <- sum(tab["FALSE", ])
  risk_exposed <- exposed_events / exposed_total
  risk_unexposed <- unexposed_events / unexposed_total
  rr <- risk_exposed / risk_unexposed
  se_log <- sqrt((1 / exposed_events) - (1 / exposed_total) + (1 / unexposed_events) - (1 / unexposed_total))
  pvalue <- fisher.test(tab)$p.value
  data.frame(
    claim_id = claim_id,
    dataset_id = "PRJEB35160",
    outcome = "URI-to-acute-sinusitis progression",
    model = "sample-level risk ratio",
    exposure = label,
    effect_type = "risk_ratio",
    effect = rr,
    ci_lower = exp(log(rr) - 1.96 * se_log),
    ci_upper = exp(log(rr) + 1.96 * se_log),
    pvalue = pvalue,
    fdr = NA_real_,
    n = nrow(df),
    analysis_status = "estimated",
    stringsAsFactors = FALSE
  )
}

extract_adonis_row <- function(result, term, model_label, n) {
  result_df <- as.data.frame(result)
  if (!term %in% rownames(result_df)) {
    return(NULL)
  }
  data.frame(
    dataset_id = "PRJEB35160",
    analysis = model_label,
    term = term,
    distance = "Bray-Curtis",
    df = result_df[term, "Df"],
    r2 = result_df[term, "R2"],
    statistic = result_df[term, "F"],
    pvalue = result_df[term, "Pr(>F)"],
    n = n,
    analysis_status = "estimated",
    stringsAsFactors = FALSE
  )
}

relative_abundance_matrix <- function(otu_counts) {
  totals <- colSums(otu_counts, na.rm = TRUE)
  totals[totals == 0] <- NA_real_
  rel <- sweep(otu_counts, 2, totals, "/")
  rel[is.na(rel)] <- 0
  rel
}

bootstrap_rr_by_child <- function(df, exposure, iterations = bootstrap_iterations) {
  set.seed(20260523)
  children <- unique(df$child_id)
  observed <- risk_ratio_row(df, exposure, "C1", exposure)$effect
  child_indices <- split(seq_len(nrow(df)), df$child_id)
  boot_rr <- replicate(iterations, {
    sampled_children <- sample(children, length(children), replace = TRUE)
    sampled_index <- unlist(child_indices[sampled_children], use.names = FALSE)
    sampled_exposure <- factor(df[[exposure]][sampled_index], levels = c(FALSE, TRUE))
    sampled_outcome <- factor(df$sinusitis_binary[sampled_index], levels = c(0, 1))
    tab <- table(sampled_exposure, sampled_outcome)
    exposed_risk <- tab["TRUE", "1"] / sum(tab["TRUE", ])
    unexposed_risk <- tab["FALSE", "1"] / sum(tab["FALSE", ])
    exposed_risk / unexposed_risk
  })
  boot_rr <- boot_rr[is.finite(boot_rr)]
  data.frame(
    dataset_id = "PRJEB35160",
    exposure = exposure,
    effect_type = "cluster_bootstrap_risk_ratio",
    effect = observed,
    ci_lower = unname(stats::quantile(boot_rr, 0.025, na.rm = TRUE)),
    ci_upper = unname(stats::quantile(boot_rr, 0.975, na.rm = TRUE)),
    n_bootstrap = length(boot_rr),
    n_children = length(children),
    analysis_status = "estimated",
    stringsAsFactors = FALSE
  )
}

input_rds <- file.path(root, "data", "references", "sinusitis_microbiome", "AnalysisPhyloseq.rds")
if (!file.exists(input_rds)) {
  stop("Missing AnalysisPhyloseq.rds. Run `make processed` first.")
}

dir_create(file.path(root, "data", "processed"))
dir_create(file.path(root, "results", "primary"))
dir_create(file.path(root, "results", "effect_sizes"))
dir_create(file.path(root, "results", "figures"))
dir_create(file.path(root, "plots", "publication", "pdf"))
dir_create(file.path(root, "plots", "publication", "png"))

ps <- readRDS(input_rds)
otu_for_diversity <- as(otu_table(ps), "matrix")
if (taxa_are_rows(ps)) {
  otu_for_diversity <- t(otu_for_diversity)
}
sample_df <- data.frame(sample_data(ps), check.names = FALSE) %>%
  tibble::rownames_to_column("phyloseq_sample_id") %>%
  mutate(
    sample_id = as.character(X.SampleID),
    matrix_sample_id = if_else(sample_id %in% rownames(otu_for_diversity), sample_id, phyloseq_sample_id),
    child_id = as.character(PatID),
    outcome_group = as.character(sinusitis_vs_uri),
    sinusitis_binary = case_when(
      outcome_group == "Sinusitis" ~ 1L,
      outcome_group == "URI" ~ 0L,
      TRUE ~ NA_integer_
    ),
    ecological_cluster = as.character(CanberraClusters),
    cluster_i = ecological_cluster == "I",
    dominant_genus = clean_taxon_label(dom_gen),
    moraxella_dominant = dominant_genus == "Moraxella",
    haemophilus_dominant = dominant_genus == "Haemophilus",
    dominant_genus_fraction = as.numeric(domgen_pct),
    season = as.factor(season),
    daycare = as.factor(Daycare_Initial),
    tobacco_exposure = as.factor(Tobacco.Exposure_Initial),
    virus_count = suppressWarnings(as.numeric(tot.virus.in.samp)),
    antibiotics_taken = suppressWarnings(as.numeric(AB_Taken)),
    shannon = vegan::diversity(otu_for_diversity, index = "shannon")
  )

otu_matrix <- as(otu_table(ps), "matrix")
if (!taxa_are_rows(ps)) {
  otu_matrix <- t(otu_matrix)
}
tax_df <- data.frame(tax_table(ps), check.names = FALSE) %>%
  mutate(taxon_id = rownames(.), genus_label = clean_taxon_label(genus))
rel_otu <- relative_abundance_matrix(otu_matrix)
genus_rel_otu <- rowsum(rel_otu, group = tax_df$genus_label, reorder = FALSE)
sample_genus_rel <- as.data.frame(t(genus_rel_otu), check.names = FALSE) %>%
  tibble::rownames_to_column("matrix_sample_id")

write_tsv(sample_df, file.path(root, "data", "processed", "prjeb35160_sample_metadata.tsv"))
write_tsv(tax_df, file.path(root, "data", "processed", "prjeb35160_taxonomy.tsv"))

analysis_df <- sample_df %>%
  filter(!is.na(sinusitis_binary), !is.na(cluster_i), !is.na(moraxella_dominant)) %>%
  left_join(sample_genus_rel, by = "matrix_sample_id") %>%
  mutate(
    sinusitis_binary = factor(sinusitis_binary, levels = c(0, 1)),
    cluster_i = factor(cluster_i, levels = c(FALSE, TRUE)),
    moraxella_dominant = factor(moraxella_dominant, levels = c(FALSE, TRUE))
  )

dataset_profile <- data.frame(
  dataset_id = "PRJEB35160",
  independent_children = length(unique(sample_df$child_id)),
  microbiome_profiles = nrow(sample_df),
  uri_or_sinusitis_profiles = nrow(analysis_df),
  sinusitis_profiles = sum(analysis_df$sinusitis_binary == 1),
  uri_profiles = sum(analysis_df$sinusitis_binary == 0),
  ecological_clusters = paste(sort(unique(na.omit(sample_df$ecological_cluster))), collapse = ";"),
  dominant_genera = paste(sort(unique(na.omit(sample_df$dominant_genus))), collapse = ";"),
  stringsAsFactors = FALSE
)
write_tsv(dataset_profile, file.path(root, "results", "primary", "prjeb35160_cohort_profile.tsv"))

state_summary <- analysis_df %>%
  group_by(ecological_cluster) %>%
  summarise(
    n_profiles = n(),
    n_children = n_distinct(child_id),
    sinusitis_profiles = sum(sinusitis_binary == 1),
    uri_profiles = sum(sinusitis_binary == 0),
    sinusitis_fraction = sinusitis_profiles / n_profiles,
    median_dominant_genus_fraction = median(dominant_genus_fraction, na.rm = TRUE),
    median_shannon = median(shannon, na.rm = TRUE),
    .groups = "drop"
  )
write_tsv(state_summary, file.path(root, "results", "primary", "ecological_state_outcome.tsv"))

dominant_summary <- analysis_df %>%
  group_by(dominant_genus) %>%
  summarise(
    n_profiles = n(),
    n_children = n_distinct(child_id),
    sinusitis_profiles = sum(sinusitis_binary == 1),
    uri_profiles = sum(sinusitis_binary == 0),
    sinusitis_fraction = sinusitis_profiles / n_profiles,
    median_dominant_genus_fraction = median(dominant_genus_fraction, na.rm = TRUE),
    .groups = "drop"
  ) %>%
  arrange(desc(n_profiles))
write_tsv(dominant_summary, file.path(root, "results", "primary", "dominant_genus_outcome.tsv"))

effect_rows <- list(
  risk_ratio_row(analysis_df, "cluster_i", "C1", "Cluster I ecological state"),
  risk_ratio_row(analysis_df, "moraxella_dominant", "C1", "Moraxella-dominant state")
)

glm_cluster <- glm(
  as.integer(as.character(sinusitis_binary)) ~ cluster_i + season + daycare + tobacco_exposure + virus_count,
  data = analysis_df,
  family = binomial()
)
glm_moraxella <- glm(
  as.integer(as.character(sinusitis_binary)) ~ moraxella_dominant + season + daycare + tobacco_exposure + virus_count,
  data = analysis_df,
  family = binomial()
)
effect_rows <- c(
  effect_rows,
  list(
    wald_or(glm_cluster, "cluster_iTRUE", "C1", "PRJEB35160", "URI-to-acute-sinusitis progression", "adjusted logistic regression"),
    wald_or(glm_moraxella, "moraxella_dominantTRUE", "C1", "PRJEB35160", "URI-to-acute-sinusitis progression", "adjusted logistic regression")
  )
)

mixed_status <- "estimated"
mixed_warnings <- character()
mixed_cluster <- withCallingHandlers(
  tryCatch(
    glmer(
      as.integer(as.character(sinusitis_binary)) ~ cluster_i + season + daycare + tobacco_exposure + virus_count + (1 | child_id),
      data = analysis_df,
      family = binomial(),
      control = glmerControl(optimizer = "bobyqa", optCtrl = list(maxfun = 100000))
    ),
    error = function(e) {
      mixed_status <<- paste("failed:", compact_message(conditionMessage(e)))
      NULL
    }
  ),
  warning = function(w) {
    mixed_warnings <<- c(mixed_warnings, compact_message(conditionMessage(w)))
    invokeRestart("muffleWarning")
  }
)
mixed_rows <- list()
if (!is.null(mixed_cluster)) {
  if (length(mixed_warnings) > 0) {
    mixed_status <- paste("unstable_convergence:", paste(unique(mixed_warnings), collapse = " | "))
  }
  mixed_row <- withCallingHandlers(
    wald_or(
      mixed_cluster,
      "cluster_iTRUE",
      "C1",
      "PRJEB35160",
      "URI-to-acute-sinusitis progression",
      "mixed-effects logistic regression with child intercept"
    ),
    warning = function(w) {
      mixed_warnings <<- c(mixed_warnings, compact_message(conditionMessage(w)))
      invokeRestart("muffleWarning")
    }
  )
  if (length(mixed_warnings) > 0) {
    mixed_status <- paste("unstable_convergence:", paste(unique(mixed_warnings), collapse = " | "))
  }
  if (!is.null(mixed_row)) {
    mixed_row$analysis_status <- mixed_status
    mixed_rows <- c(mixed_rows, list(mixed_row))
  }
}

claim_effects <- bind_rows(effect_rows) %>%
  mutate(
    pvalue = as.numeric(pvalue),
    fdr = p.adjust(pvalue, method = "BH"),
    effect = round(effect, 3),
    ci_lower = round(ci_lower, 3),
    ci_upper = round(ci_upper, 3),
    pvalue = signif(pvalue, 4),
    fdr = signif(fdr, 4)
  )
write_tsv(claim_effects, file.path(root, "results", "effect_sizes", "claim_effects.tsv"))
write_tsv(claim_effects, file.path(root, "results", "figures", "figure2_effects.tsv"))

if (length(mixed_rows) > 0) {
  repeated_measures <- bind_rows(mixed_rows) %>%
    mutate(
      pvalue = as.numeric(pvalue),
      fdr = p.adjust(pvalue, method = "BH"),
      effect = round(effect, 3),
      ci_lower = round(ci_lower, 3),
      ci_upper = round(ci_upper, 3),
      pvalue = signif(pvalue, 4),
      fdr = signif(fdr, 4)
    )
} else {
  repeated_measures <- data.frame(
    claim_id = "C1",
    dataset_id = "PRJEB35160",
    outcome = "URI-to-acute-sinusitis progression",
    model = "mixed-effects logistic regression with child intercept",
    exposure = "cluster_iTRUE",
    effect_type = "odds_ratio",
    effect = NA_real_,
    ci_lower = NA_real_,
    ci_upper = NA_real_,
    pvalue = NA_real_,
    fdr = NA_real_,
    n = nrow(analysis_df),
    analysis_status = mixed_status,
    stringsAsFactors = FALSE
  )
}
write_tsv(repeated_measures, file.path(root, "results", "effect_sizes", "sensitivity_repeated_measures.tsv"))

covariate_model <- glm(
  as.integer(as.character(sinusitis_binary)) ~ cluster_i + season + daycare + tobacco_exposure + virus_count + antibiotics_taken,
  data = analysis_df,
  family = binomial()
)
cov_table <- as.data.frame(summary(covariate_model)$coefficients) %>%
  tibble::rownames_to_column("term") %>%
  filter(term != "(Intercept)") %>%
  transmute(
    claim_id = "C3",
    dataset_id = "PRJEB35160",
    covariate = term,
    model = "adjusted logistic regression",
    effect_type = "odds_ratio",
    effect = round(exp(Estimate), 3),
    ci_lower = round(exp(Estimate - 1.96 * `Std. Error`), 3),
    ci_upper = round(exp(Estimate + 1.96 * `Std. Error`), 3),
    pvalue = signif(`Pr(>|z|)`, 4),
    fdr = signif(p.adjust(`Pr(>|z|)`, method = "BH"), 4),
    analysis_status = "estimated"
  )
write_tsv(cov_table, file.path(root, "results", "effect_sizes", "covariate_effects.tsv"))

alpha_summary <- analysis_df %>%
  group_by(outcome_group) %>%
  summarise(
    n_profiles = n(),
    n_children = n_distinct(child_id),
    median_shannon = median(shannon, na.rm = TRUE),
    iqr_shannon = IQR(shannon, na.rm = TRUE),
    .groups = "drop"
  )
alpha_test <- stats::wilcox.test(shannon ~ outcome_group, data = analysis_df, exact = FALSE)
alpha_model <- safe_wald_or(
  as.integer(as.character(sinusitis_binary)) ~ shannon + season + daycare + tobacco_exposure + virus_count,
  analysis_df,
  "shannon",
  "C1",
  "URI-to-acute-sinusitis progression",
  "adjusted logistic regression per Shannon unit"
)
alpha_outcome <- alpha_summary %>%
  mutate(
    dataset_id = "PRJEB35160",
    metric = "Shannon diversity",
    between_group_test = "Wilcoxon rank-sum",
    pvalue = signif(alpha_test$p.value, 4),
    fdr = signif(p.adjust(alpha_test$p.value, method = "BH"), 4),
    adjusted_odds_ratio_per_unit = if (!is.null(alpha_model)) round(alpha_model$effect, 3) else NA_real_,
    adjusted_ci_lower = if (!is.null(alpha_model)) round(alpha_model$ci_lower, 3) else NA_real_,
    adjusted_ci_upper = if (!is.null(alpha_model)) round(alpha_model$ci_upper, 3) else NA_real_,
    adjusted_pvalue = if (!is.null(alpha_model)) signif(alpha_model$pvalue, 4) else NA_real_
  ) %>%
  select(dataset_id, metric, outcome_group, n_profiles, n_children, median_shannon, iqr_shannon, between_group_test, pvalue, fdr, adjusted_odds_ratio_per_unit, adjusted_ci_lower, adjusted_ci_upper, adjusted_pvalue)
write_tsv(alpha_outcome, file.path(root, "results", "primary", "alpha_diversity_outcome.tsv"))

sample_rel_matrix <- t(rel_otu)
analysis_matrix <- sample_rel_matrix[analysis_df$matrix_sample_id, , drop = FALSE]
analysis_matrix <- analysis_matrix[, colSums(analysis_matrix) > 0, drop = FALSE]
analysis_meta <- analysis_df %>%
  transmute(
    child_id = child_id,
    clinical_endpoint = factor(outcome_group),
    moraxella_dominant = moraxella_dominant,
    ecological_cluster = factor(ecological_cluster)
  )
bray_distance <- vegan::vegdist(analysis_matrix, method = "bray")
beta_rows <- list(
  extract_adonis_row(
    vegan::adonis2(bray_distance ~ clinical_endpoint, data = analysis_meta, permutations = permutation_count, strata = analysis_meta$child_id, by = "margin"),
    "clinical_endpoint",
    "PERMANOVA by clinical endpoint, child-stratified permutations",
    nrow(analysis_meta)
  ),
  extract_adonis_row(
    vegan::adonis2(bray_distance ~ moraxella_dominant, data = analysis_meta, permutations = permutation_count, strata = analysis_meta$child_id, by = "margin"),
    "moraxella_dominant",
    "PERMANOVA by Moraxella-dominant state, child-stratified permutations",
    nrow(analysis_meta)
  ),
  extract_adonis_row(
    vegan::adonis2(bray_distance ~ ecological_cluster, data = analysis_meta, permutations = permutation_count, strata = analysis_meta$child_id, by = "margin"),
    "ecological_cluster",
    "PERMANOVA by nasopharyngeal ecological state, child-stratified permutations",
    nrow(analysis_meta)
  )
)
dispersion_endpoint <- anova(vegan::betadisper(bray_distance, analysis_meta$clinical_endpoint))
dispersion_moraxella <- anova(vegan::betadisper(bray_distance, analysis_meta$moraxella_dominant))
beta_rows <- c(
  beta_rows,
  list(
    data.frame(
      dataset_id = "PRJEB35160",
      analysis = "Dispersion check by clinical endpoint",
      term = "clinical_endpoint",
      distance = "Bray-Curtis",
      df = dispersion_endpoint$Df[1],
      r2 = NA_real_,
      statistic = dispersion_endpoint$`F value`[1],
      pvalue = dispersion_endpoint$`Pr(>F)`[1],
      n = nrow(analysis_meta),
      analysis_status = "diagnostic",
      stringsAsFactors = FALSE
    ),
    data.frame(
      dataset_id = "PRJEB35160",
      analysis = "Dispersion check by Moraxella-dominant state",
      term = "moraxella_dominant",
      distance = "Bray-Curtis",
      df = dispersion_moraxella$Df[1],
      r2 = NA_real_,
      statistic = dispersion_moraxella$`F value`[1],
      pvalue = dispersion_moraxella$`Pr(>F)`[1],
      n = nrow(analysis_meta),
      analysis_status = "diagnostic",
      stringsAsFactors = FALSE
    )
  )
)
beta_tests <- bind_rows(beta_rows) %>%
  mutate(
    r2 = round(r2, 4),
    statistic = round(statistic, 3),
    pvalue = signif(pvalue, 4),
    fdr = signif(p.adjust(pvalue, method = "BH"), 4)
  )
write_tsv(beta_tests, file.path(root, "results", "primary", "beta_diversity_tests.tsv"))

focus_genera <- intersect(
  c("Moraxella", "Haemophilus", "Streptococcus", "Staphylococcus", "Corynebacterium", "Alloiococcus"),
  colnames(analysis_df)
)
genus_rows <- lapply(focus_genera, function(genus_name) {
  genus_df <- analysis_df %>%
    mutate(abundance = as.numeric(.data[[genus_name]]), abundance_10 = abundance / 0.10)
  test <- stats::wilcox.test(abundance ~ outcome_group, data = genus_df, exact = FALSE)
  model_row <- safe_wald_or(
    as.integer(as.character(sinusitis_binary)) ~ abundance_10 + season + daycare + tobacco_exposure + virus_count,
    genus_df,
    "abundance_10",
    "C1",
    "URI-to-acute-sinusitis progression",
    "adjusted logistic regression per 10 percentage-point relative abundance"
  )
  data.frame(
    dataset_id = "PRJEB35160",
    genus = genus_name,
    median_abundance_sinusitis = median(genus_df$abundance[genus_df$outcome_group == "Sinusitis"], na.rm = TRUE),
    median_abundance_uri = median(genus_df$abundance[genus_df$outcome_group == "URI"], na.rm = TRUE),
    median_difference = median(genus_df$abundance[genus_df$outcome_group == "Sinusitis"], na.rm = TRUE) -
      median(genus_df$abundance[genus_df$outcome_group == "URI"], na.rm = TRUE),
    wilcoxon_pvalue = test$p.value,
    adjusted_odds_ratio_per_10pct = if (!is.null(model_row)) model_row$effect else NA_real_,
    adjusted_ci_lower = if (!is.null(model_row)) model_row$ci_lower else NA_real_,
    adjusted_ci_upper = if (!is.null(model_row)) model_row$ci_upper else NA_real_,
    adjusted_pvalue = if (!is.null(model_row)) model_row$pvalue else NA_real_,
    n = nrow(genus_df),
    analysis_status = "estimated",
    stringsAsFactors = FALSE
  )
})
genus_abundance <- bind_rows(genus_rows) %>%
  mutate(
    wilcoxon_fdr = signif(p.adjust(wilcoxon_pvalue, method = "BH"), 4),
    adjusted_fdr = signif(p.adjust(adjusted_pvalue, method = "BH"), 4),
    across(c(median_abundance_sinusitis, median_abundance_uri, median_difference), ~ round(.x, 4)),
    across(c(adjusted_odds_ratio_per_10pct, adjusted_ci_lower, adjusted_ci_upper), ~ round(.x, 3)),
    wilcoxon_pvalue = signif(wilcoxon_pvalue, 4),
    adjusted_pvalue = signif(adjusted_pvalue, 4)
  ) %>%
  arrange(adjusted_fdr, wilcoxon_fdr)
write_tsv(genus_abundance, file.path(root, "results", "primary", "genus_abundance_outcome.tsv"))

sample_genus_long <- analysis_df %>%
  select(sample_id, child_id, outcome_group, all_of(focus_genera)) %>%
  tidyr::pivot_longer(
    cols = all_of(focus_genera),
    names_to = "genus",
    values_to = "relative_abundance"
  )
write_tsv(sample_genus_long, file.path(root, "results", "primary", "sample_genus_abundance.tsv"))

bootstrap_stability <- bind_rows(
  bootstrap_rr_by_child(analysis_df, "moraxella_dominant"),
  bootstrap_rr_by_child(analysis_df, "cluster_i")
) %>%
  mutate(across(c(effect, ci_lower, ci_upper), ~ round(.x, 3)))
write_tsv(bootstrap_stability, file.path(root, "results", "effect_sizes", "bootstrap_stability.tsv"))

child_level <- analysis_df %>%
  group_by(child_id) %>%
  summarise(
    ever_sinusitis = as.integer(any(sinusitis_binary == 1)),
    any_moraxella_dominant = any(moraxella_dominant == TRUE),
    moraxella_profile_fraction = mean(moraxella_dominant == TRUE),
    cluster_i_profile_fraction = mean(cluster_i == TRUE),
    mean_shannon = mean(shannon, na.rm = TRUE),
    n_profiles = n(),
    .groups = "drop"
  ) %>%
  mutate(
    ever_sinusitis = factor(ever_sinusitis, levels = c(0, 1)),
    any_moraxella_dominant = factor(any_moraxella_dominant, levels = c(FALSE, TRUE)),
    moraxella_fraction_25pct = moraxella_profile_fraction / 0.25,
    cluster_i_fraction_25pct = cluster_i_profile_fraction / 0.25
  )
child_rows <- list(
  safe_wald_or(
    as.integer(as.character(ever_sinusitis)) ~ any_moraxella_dominant,
    child_level,
    "any_moraxella_dominantTRUE",
    "C1",
    "Child-level ever-sinusitis status",
    "child-level logistic regression, any Moraxella-dominant profile"
  ),
  safe_wald_or(
    as.integer(as.character(ever_sinusitis)) ~ moraxella_fraction_25pct,
    child_level,
    "moraxella_fraction_25pct",
    "C1",
    "Child-level ever-sinusitis status",
    "child-level logistic regression per 25 percentage-point Moraxella-dominant profile fraction"
  ),
  safe_wald_or(
    as.integer(as.character(ever_sinusitis)) ~ cluster_i_fraction_25pct,
    child_level,
    "cluster_i_fraction_25pct",
    "C1",
    "Child-level ever-sinusitis status",
    "child-level logistic regression per 25 percentage-point cluster I profile fraction"
  )
)
child_level_sensitivity <- bind_rows(child_rows) %>%
  mutate(
    pvalue = as.numeric(pvalue),
    fdr = p.adjust(pvalue, method = "BH"),
    analysis_status = if_else(!is.finite(ci_upper) | effect > 100, "unstable_separation_diagnostic", analysis_status),
    effect = round(effect, 3),
    ci_lower = round(ci_lower, 3),
    ci_upper = round(ci_upper, 3),
    pvalue = signif(pvalue, 4),
    fdr = signif(fdr, 4),
    n_children = nrow(child_level)
  )
write_tsv(child_level_sensitivity, file.path(root, "results", "effect_sizes", "child_level_sensitivity.tsv"))

loo_rows <- lapply(unique(analysis_df$child_id), function(omitted_child) {
  loo_df <- analysis_df %>% filter(child_id != omitted_child)
  loo_model <- safe_wald_or(
    as.integer(as.character(sinusitis_binary)) ~ moraxella_dominant + season + daycare + tobacco_exposure + virus_count,
    loo_df,
    "moraxella_dominantTRUE",
    "C1",
    "URI-to-acute-sinusitis progression",
    "leave-one-child-out adjusted logistic regression"
  )
  if (is.null(loo_model)) {
    return(data.frame(
      dataset_id = "PRJEB35160",
      omitted_child_id = omitted_child,
      exposure = "Moraxella-dominant state",
      effect_type = "odds_ratio",
      effect = NA_real_,
      ci_lower = NA_real_,
      ci_upper = NA_real_,
      pvalue = NA_real_,
      n = nrow(loo_df),
      analysis_status = "failed",
      stringsAsFactors = FALSE
    ))
  }
  loo_model %>%
    transmute(
      dataset_id = dataset_id,
      omitted_child_id = omitted_child,
      exposure = "Moraxella-dominant state",
      effect_type = effect_type,
      effect = effect,
      ci_lower = ci_lower,
      ci_upper = ci_upper,
      pvalue = pvalue,
      n = n,
      analysis_status = analysis_status
    )
})
leave_one_child_out <- bind_rows(loo_rows) %>%
  mutate(
    effect = round(effect, 3),
    ci_lower = round(ci_lower, 3),
    ci_upper = round(ci_upper, 3),
    pvalue = signif(pvalue, 4)
  )
write_tsv(leave_one_child_out, file.path(root, "results", "effect_sizes", "leave_one_child_out.tsv"))

leave_one_child_out_summary <- leave_one_child_out %>%
  summarise(
    dataset_id = "PRJEB35160",
    exposure = "Moraxella-dominant state",
    model = "leave-one-child-out adjusted logistic regression",
    successful_models = sum(analysis_status == "estimated", na.rm = TRUE),
    omitted_children = n(),
    median_odds_ratio = median(effect, na.rm = TRUE),
    min_odds_ratio = min(effect, na.rm = TRUE),
    max_odds_ratio = max(effect, na.rm = TRUE),
    proportion_or_above_one = mean(effect > 1, na.rm = TRUE),
    min_pvalue = min(pvalue, na.rm = TRUE),
    max_pvalue = max(pvalue, na.rm = TRUE),
    analysis_status = "estimated"
  ) %>%
  mutate(
    across(c(median_odds_ratio, min_odds_ratio, max_odds_ratio, proportion_or_above_one, min_pvalue, max_pvalue), ~ signif(.x, 4))
  )
write_tsv(leave_one_child_out_summary, file.path(root, "results", "effect_sizes", "leave_one_child_out_summary.tsv"))

plot_df <- state_summary %>%
  mutate(ecological_cluster = factor(ecological_cluster, levels = sort(unique(ecological_cluster))))
p <- ggplot(plot_df, aes(x = ecological_cluster, y = sinusitis_fraction)) +
  geom_col(fill = "#4C78A8", width = 0.72) +
  geom_text(aes(label = paste0("n=", n_profiles)), vjust = -0.4, size = 3.2) +
  scale_y_continuous(labels = scales::percent_format(accuracy = 1), limits = c(0, min(1, max(plot_df$sinusitis_fraction) + 0.15))) +
  labs(
    x = "Nasopharyngeal ecological state",
    y = "Profiles associated with sinusitis",
    title = "Sinusitis-associated profiles by nasopharyngeal ecological state"
  ) +
  theme_classic(base_size = 11)
ggsave(file.path(root, "plots", "publication", "pdf", "Figure2_state_outcome.pdf"), p, width = 5.5, height = 4)
ggsave(file.path(root, "plots", "publication", "png", "Figure2_state_outcome.png"), p, width = 5.5, height = 4, dpi = 300)

taxon_plot_df <- genus_abundance %>%
  filter(is.finite(adjusted_odds_ratio_per_10pct), is.finite(adjusted_ci_lower), is.finite(adjusted_ci_upper)) %>%
  mutate(genus = factor(genus, levels = rev(genus[order(adjusted_odds_ratio_per_10pct)])))
if (nrow(taxon_plot_df) > 0) {
  p_taxon <- ggplot(taxon_plot_df, aes(x = adjusted_odds_ratio_per_10pct, y = genus)) +
    geom_vline(xintercept = 1, linetype = "dashed", color = "grey55", linewidth = 0.4) +
    geom_errorbar(aes(xmin = adjusted_ci_lower, xmax = adjusted_ci_upper), orientation = "y", width = 0.18, color = "#333333") +
    geom_point(size = 2.4, color = "#B54A3A") +
    scale_x_log10() +
    labs(
      x = "Adjusted odds ratio per 10 percentage-point relative abundance",
      y = "Dominant upper-airway genus",
      title = "Genus-level associations with sinusitis-associated profiles"
    ) +
    theme_classic(base_size = 11)
  ggsave(file.path(root, "plots", "publication", "pdf", "Figure3_genus_effects.pdf"), p_taxon, width = 6.2, height = 4)
  ggsave(file.path(root, "plots", "publication", "png", "Figure3_genus_effects.png"), p_taxon, width = 6.2, height = 4, dpi = 300)
}

message("Primary PRJEB35160 analysis complete.")
