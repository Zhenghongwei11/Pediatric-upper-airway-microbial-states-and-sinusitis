#!/usr/bin/env Rscript

expected_r <- package_version("4.4.3")
if (getRversion() != expected_r) {
  stop("This workflow is pinned to R 4.4.3; found R ", getRversion(), call. = FALSE)
}

options(repos = c(CRAN = "https://cloud.r-project.org"))

if (!requireNamespace("remotes", quietly = TRUE)) {
  install.packages("remotes")
}
if (!requireNamespace("BiocManager", quietly = TRUE)) {
  install.packages("BiocManager")
}

cran_versions <- c(readr = "2.1.5", vegan = "2.7-1", permute = "0.9-8")
for (package in names(cran_versions)) {
  expected <- cran_versions[[package]]
  installed <- if (requireNamespace(package, quietly = TRUE)) {
    as.character(utils::packageVersion(package))
  } else {
    NA_character_
  }
  if (is.na(installed) || package_version(installed) != package_version(expected)) {
    remotes::install_version(package, version = expected, upgrade = "never", quiet = TRUE)
  }
}

BiocManager::install(version = "3.20", ask = FALSE, update = FALSE, quiet = TRUE)
if (!requireNamespace("phyloseq", quietly = TRUE) ||
    as.character(utils::packageVersion("phyloseq")) != "1.50.0") {
  BiocManager::install("phyloseq", version = "3.20", ask = FALSE,
                       update = FALSE, quiet = TRUE)
}

expected <- c(phyloseq = "1.50.0", readr = "2.1.5", vegan = "2.7-1", permute = "0.9-8")
installed <- vapply(names(expected), function(package) {
  as.character(utils::packageVersion(package))
}, character(1))
if (!all(mapply(function(a, b) package_version(a) == package_version(b), installed, expected))) {
  stop("R package versions do not match the pinned environment: ",
       paste(names(installed), installed, sep = "=", collapse = ", "),
       call. = FALSE)
}
cat("Verified R 4.4.3 and pinned analysis packages.\n")
