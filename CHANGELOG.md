# Changelog

## Unreleased

- Correct the SpliceAI 1.3.1 reporting-distance default to its supported maximum of 4999 bp; 5000 was rejected by the predictor CLI during the first real cluster run.
- Add a compact, read-only SLURM failure-bundle helper that excludes source data and large logs.
- Raise the Kircherlab SLURM controller allocation to 64 GB and VEP/SpliceAI child allocations to 32 GB after the VEP 115.2 Conda solve exceeded the original controller memory limit.
- Add a Kircherlab BRCA1 smoke-test SLURM helper using the verified account, partitions, Miniforge path, shared rule-environment prefix, and controller email notifications.
- Add a read-only SLURM site-inspection helper for collecting controller configuration without copying individual diagnostic commands.
- Add a checked-in Kircherlab resource configuration and reproducible BRCA1-region smoke-test helper to replace repeated interactive path exports.
- Align the pinned VEP executable and default offline cache with Ensembl release 115 (VEP 115.2), including the assembly-qualified indexed-cache directory layout.
- Add a standalone SpliceAI 1.3.1 branch, explicit score/missingness parsing, candidate/review integration, one-sample wrapper, and variant-centric portable HTML report.
- Preserve canonical and splice-region VEP candidates while admitting noncanonical exonic/intronic alleles using configurable SpliceAI thresholds.
- Add an optional SLURM executor/controller deployment with preflight checks and a git-ignored site-local launcher while retaining laptop execution as the default.
- Freeze `TSG-SPLICE-CATEGORIES/1.0.0`, defining assembly-aware canonical, near-splice, exonic-motif, and deep-intronic boundaries plus the versioned VIPER hand-off contract.

## 0.1.0 - 2026-07-21

- Initial canonical splice consequence pipeline with manifest validation, normalization, VEP, transcript/allele tables, summaries, profiles, provenance, resource setup, and synthetic tests.
