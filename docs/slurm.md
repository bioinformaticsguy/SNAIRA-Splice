# Optional SLURM execution

Local laptop execution remains the default. The SLURM layer is optional and uses a controller model: one small batch job runs Snakemake, and `snakemake-executor-plugin-slurm` submits each workflow rule as a child job. No cluster-specific account, partition, path, or email is committed.

## Requirements

The controller environment from `environment.yaml` already pins the SLURM executor plugin. On the cluster, `snakemake`, `python`, `sbatch`, and `sacct` must be available. Rule Conda environments need a shared filesystem visible from compute nodes; set `SNAIRA_CONDA_PREFIX` to a shared writable directory.

## Configure once per cluster

Inspect the available partitions, account associations, Conda installation,
and controller dependencies without submitting a job:

```bash
bash scripts/slurm/inspect_slurm_site.sh
```

```bash
cp scripts/slurm/submit_snaira_splice_controller.local.example.sh \
  scripts/slurm/submit_snaira_splice_controller.local.sh
chmod +x scripts/slurm/submit_snaira_splice_controller.local.sh
```

Edit the copied file with the cluster's Miniforge path, short/long partitions, optional account and email, job limit, and shared Conda prefix. The copied local launcher is git-ignored.

VEP and SpliceAI are assigned to the configured long partition; other rules use the short partition. Rule `threads`, `mem_mb`, and `runtime` still come from the workflow configuration/profile and can be overridden through ordinary Snakemake arguments.

## Preflight without submission

Run this on a cluster login node after resources and configuration are installed:

```bash
bash scripts/slurm/check_slurm_profile.sh config/config.yaml
```

This validates commands, plugin import, configuration, and the production DAG using `--dry-run`. It does not submit jobs.

## Submit

```bash
bash scripts/slurm/submit_snaira_splice_controller.local.sh \
  --configfile config/config.yaml
```

To request specific Snakemake targets, put them after `--`:

```bash
bash scripts/slurm/submit_snaira_splice_controller.local.sh \
  --configfile config/config.yaml -- \
  results/S001/05_report/S001.snaira_splice.html
```

Controller logs are written under `logs/`; child-job logs use `logs/slurm/`. Both are ignored by Git. Rule-specific workflow logs remain under the configured result root.

Monitor with your site's normal commands, commonly `squeue -u "$USER"`, `sacct -j JOB_ID`, and the controller log. If a controller dies, fix the cause and resubmit: `rerun-incomplete` is enabled. Do not use `--forceall` against shared results. If Snakemake reports a stale lock only after confirming no controller is still active, run `snakemake --unlock` with the same configuration and working directory.

## Regional smoke test

Use a small region from a real sample to validate installed resources before a
whole-genome run. First copy `config/site.example.yaml` to the git-ignored
`config/site.yaml` and replace the placeholder paths. Then prepare a region;
the source VCF remains immutable:

```bash
bash scripts/run_region_test.sh \
  --vcf /absolute/path/sample.vcf.gz \
  --sample-id S001 \
  --reference /absolute/path/GRCh38.fa \
  --region chr17:43000000-43200000 \
  --dry-run
```

After copying and configuring the git-ignored local launcher described above,
preflight or submit the generated run configuration:

```bash
bash scripts/slurm/submit_region_test.sh --sample-id S001 --preflight
bash scripts/slurm/submit_region_test.sh --sample-id S001 --submit
```

Controller email is configured with `SNAIRA_MAIL_USER` in the local launcher.
Child rule jobs do not request email independently, avoiding one notification
stream per workflow rule. For first-time environment creation, a controller
allocation of 64 GB is a reasonable starting point: Conda solving for the
pinned VEP environment can be memory-intensive. The example site template
allocates 32 GB each to VEP and SpliceAI; adjust these values from observed
usage at your site.

## Collecting a failure bundle

To share a failed controller run without copying large data, create a compact
diagnostic bundle from the repository root:

```bash
bash scripts/slurm/collect_job_diagnostics.sh 1234567 \
  --configfile output/results/metadata/single_sample_input/S001/config.yaml
```

This creates `diagnostics/slurm-job-3326218/` with SLURM accounting, controller
log tails, matching-log inventory, the generated run configuration, and Git
state. It excludes VCFs, references, Conda environments, and full logs. Inspect
the bundle before committing it because retained logs can include filesystem
paths and sample identifiers.
