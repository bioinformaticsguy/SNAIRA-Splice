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

## Kircherlab regional smoke test

The checked-in Kircherlab helper contains the site values verified on
2026-09-18: account `hassan`, `shortterm` for the controller and ordinary
rules, `longterm` for VEP/SpliceAI, and the shared Miniforge and rule-environment
prefixes. After preparing the regional test and generating its configuration,
preflight and submit with:

```bash
bash scripts/slurm/submit_kircherlab_region_test.sh --preflight
bash scripts/slurm/submit_kircherlab_region_test.sh --submit
```

The controller submission requests SLURM mail type `ALL` for
`alihassan1697@gmail.com`. Child rule jobs do not request email independently,
which avoids one notification stream per workflow rule.

The helper is intentionally specific to this smoke test. Update it if the site
account, partitions, paths, or sample change; the generic launcher above remains
the interface for other sites and production runs.
