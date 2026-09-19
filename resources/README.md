# Resources

Large reference, Ensembl annotation, VEP cache, and SpliceAI data are deliberately untracked. Install them with `scripts/setup_resources.sh`; ordinary Snakemake execution never downloads them. The generated `resource_manifest.tsv`, `resource_manifest.json`, checksums, and completion markers describe the local installation.

Transcript-aware category assignment requires the Ensembl GTF to match the VEP/cache release exactly. For the pinned release 115 workflow, install it explicitly:

```bash
bash scripts/setup_resources.sh --resource-dir resources --vep-cache-version 115 --download-gtf
```

Set `categories.gtf` to the installed `annotation/Homo_sapiens.GRCh38.115.gtf.gz` and retain `categories.annotation_release: 115`. The category rule fails before annotation if this release does not equal `vep.cache_version`; a shared GRCh38 GTF from a different Ensembl release must not be substituted silently.
