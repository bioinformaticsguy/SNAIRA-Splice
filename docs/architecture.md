# Architecture

The standalone MVP DAG branches after normalization: VEP supplies transcript consequences while local SpliceAI supplies gene-level effect predictions. Their parsed outputs meet only in a dedicated candidate-integration stage, followed by deterministic allele collapse and a static HTML report. Legacy canonical extraction and cohort summaries remain available in parallel.

```text
manifest -> validate -> normalize -> VEP ---------\
                                \-> SpliceAI ------+-> joined transcript evidence
                                                    -> allele candidates/review
                                                    -> standalone HTML
```

Raw VEP and SpliceAI VCFs remain audit boundaries. Source manifests and VCFs are immutable. Normalized alleles receive stable `CHROM:POS:REF:ALT` identifiers before either annotation branch, preventing joins based on display-oriented VEP locations.

Consequence annotation and splice-effect prediction are separate interfaces. VEP assigns transcript consequences. SpliceAI runs over all supported normalized alleles rather than only canonical sites. Candidate membership is the union of donor/acceptor/splice-region VEP evidence and configured SpliceAI score evidence. Missing prediction, a genuine zero, and workflow failure are not interchangeable.

The normative category boundaries and non-exclusive assignment model are versioned in `splice-category-specification-v1.0.md`. The executable MVP uses conservative coarse labels; without exact transcript-relative exon-boundary calculations, intronic rows are `intronic_noncanonical`, not `deep_intronic`. VIPER/CALIGO integration is not part of this DAG.

Manifest records are loaded while constructing the DAG so invalid cohorts fail before expensive jobs. The same library writes the in-run resolved table, avoiding divergent discovery logic. Output paths use a validated sample wildcard and never point alongside input files.
