#!/usr/bin/env Rscript
suppressPackageStartupMessages({library(phyloseq);library(vegan);library(readr)})
set.seed(20261020)
out <- "results/primary"
meta <- read_tsv("data/processed/prjeb35160_sample_metadata.tsv",show_col_types=FALSE)
otu <- read_tsv(file.path(out,"otu_relative_abundance.tsv"),show_col_types=FALSE)
meta <- meta[meta$outcome_group %in% c("URI","Sinusitis"),]
mat <- as.matrix(otu[match(meta$matrix_sample_id,otu$matrix_sample_id),-1])
rownames(mat) <- meta$sample_id
childmat <- rowsum(mat,group=meta$child_id)/as.vector(table(meta$child_id))
child <- meta[match(rownames(childmat),meta$child_id),c("child_id","outcome_group")]
child$outcome_group <- factor(child$outcome_group)
stopifnot(nrow(child)==45,nrow(childmat)==45)
dist <- vegdist(childmat,method="bray")
test <- adonis2(dist~outcome_group,data=child,permutations=9999,by="margin")
disp <- betadisper(dist,child$outcome_group,type="median",bias.adjust=TRUE,add="lingoes")
disp_test <- permutest(disp,permutations=9999)
result <- data.frame(analysis=c("PERMANOVA_mean_child_composition","PERMDISP_mean_child_composition"),term="followup_outcome_group",n_children=45,n_profiles=323,df=c(test$Df[1],disp_test$tab$Df[1]),r2=c(test$R2[1],NA),statistic=c(test$F[1],disp_test$tab$F[1]),pvalue=c(test$`Pr(>F)`[1],disp_test$tab$`Pr(>F)`[1]),permutations=9999,seed=20261020,exchangeability_unit="independent_child",input="mean_eligible_OTU_relative_composition_per_child",multiplicity="descriptive_tests_raw_P_no_confirmatory_claim")
write_tsv(result,file.path(out,"community_tests.tsv"))
write_tsv(data.frame(child_id=rownames(childmat),childmat,check.names=FALSE),file.path(out,"child_mean_otu_composition.tsv"))
capture.output(list(PERMANOVA=test,PERMDISP=disp_test,dispersion=disp),file=file.path(out,"community_diagnostics.txt"))
diagnostics <- data.frame(
  diagnostic=c("mean_distance_to_median_Sinusitis", "mean_distance_to_median_URI",
               "positive_pcoa_eigenvalues", "negative_pcoa_eigenvalues_after_lingoes"),
  value=c(mean(disp$distances[disp$group == "Sinusitis"]),
          mean(disp$distances[disp$group == "URI"]),
          sum(disp$eig > 1e-12), sum(disp$eig < -1e-12))
)
write_tsv(diagnostics,file.path(out,"community_diagnostics_summary.tsv"))
print(result)
