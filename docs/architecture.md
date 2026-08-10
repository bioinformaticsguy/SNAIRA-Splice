# Architecture

The DAG is layered: manifest resolution → immutable input validation → normalization → VEP consequence annotation → canonical extraction → allele collapse → summaries/provenance. Raw VEP products remain an audit boundary. Pure parsing and ranking functions live outside Snakemake so they can be unit tested and reused by later modules.

Consequence annotation and splice-effect prediction are separate interfaces. VEP assigns transcript consequences. Future predictors consume normalized alleles and emit their own evidence without changing VEP-derived candidate truth. Empty or fabricated predictor records are forbidden.

Manifest records are loaded while constructing the DAG so invalid cohorts fail before expensive jobs. The same library writes the in-run resolved table, avoiding divergent discovery logic. Output paths use a validated sample wildcard and never point alongside input files.
