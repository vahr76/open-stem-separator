# OSS separation laboratory

This laboratory is intentionally separate from the `ytd` downloader command. It is for testing source-separation engines, pipelines, manifests and resource behavior before any model becomes part of the user-facing product.

The lab follows the multistage direction documented for OSS:

```text
original audio
  ├─ direct multistem baseline
  └─ stage 1 vocal/instrumental candidate
       └─ stage 2 instrumental separation candidate
```

No model is considered a default until local tests compare quality, time, memory, artifacts and reconstruction behavior.

## Current scope

Implemented now:

- lab folder layout;
- JSON configs;
- `separate.py` CLI;
- Demucs subprocess runner;
- direct and two-stage cascade configs;
- stage-to-stage input references;
- dry-run mode that writes a manifest without requiring Demucs;
- per-run `manifest.json` and per-stage `stage.json`;
- input SHA-256 and timestamps.

Not implemented yet:

- BS-RoFormer / MelBand execution;
- python-audio-separator integration;
- reconciliation and residual calculation;
- audio alignment checks;
- memory/VRAM measurement;
- cancellation/resume beyond preserving completed folders.

## Setup

Use an isolated environment. Do not install heavy ML dependencies into the system Python.

```sh
python3 -m venv .venv-separation
. .venv-separation/bin/activate
python -m pip install --upgrade pip
python -m pip install demucs
```

Then run a direct Demucs experiment:

```sh
python3 labs/separation/separate.py \
  --config labs/separation/configs/demucs-htdemucs.json \
  --input /path/to/audio.flac \
  --out /tmp/oss-separation-lab
```

Dry run, useful for testing manifests without ML dependencies:

```sh
python3 labs/separation/separate.py \
  --config labs/separation/configs/demucs-htdemucs.json \
  --input /path/to/audio.flac \
  --out /tmp/oss-separation-lab \
  --dry-run
```


Cascade dry run, matching the current multistage design direction:

```sh
python3 labs/separation/separate.py \
  --config labs/separation/configs/demucs-vocal-then-instrumental.json \
  --input /path/to/audio.flac \
  --out /tmp/oss-separation-lab \
  --dry-run
```

In real cascade mode the second stage resolves its input from the first stage with a reference like `stage:stage-01-vocal-instrumental:stems/**/no_vocals.wav`.


## Minimal benchmark

The first benchmark harness compares the direct baseline and the cascade on local excerpts.

Dry-run the benchmark structure without running Demucs:

```sh
python3 labs/separation/tools/benchmark.py \
  --benchmark labs/separation/benchmarks/minimal-local.json \
  --out /tmp/oss-separation-benchmark \
  --dry-run
```

Run only the first excerpt, useful on CPU:

```sh
. .venv-separation/bin/activate
python3 labs/separation/tools/benchmark.py \
  --benchmark labs/separation/benchmarks/minimal-local.json \
  --out /tmp/oss-separation-benchmark \
  --max-items 1
```

The benchmark writes `benchmark.json`, `REPORT.md`, generated clips and full lab runs. Listening notes stay manual for now because the decision we need first is perceptual: direct model versus cascade.


## Listening in REAPER

The lab can generate a simple `.rpp` session from any separation run. Each stem is imported as an aligned track starting at zero.

```sh
python3 labs/separation/tools/reaper_project.py /path/to/lab-run
```

For the first Blur benchmark, the generated projects were:

```text
/tmp/oss-benchmark-real-one/2026-09-25T021903.895843Z-minimal-local/runs/blur-beetlebum/20260925-021904-demucs-htdemucs-direct/20260925-021904-demucs-htdemucs-direct.rpp
/tmp/oss-benchmark-real-one/2026-09-25T021903.895843Z-minimal-local/runs/blur-beetlebum/20260925-021915-demucs-vocal-then-instrumental/20260925-021915-demucs-vocal-then-instrumental.rpp
```

Use REAPER here as a reference listening environment. The OSS player can later borrow the useful workflow ideas: aligned stems, mute/solo, level controls, residual tracks, waveform overview, markers and simple export.

## Output layout

```text
/tmp/oss-separation-lab/<run-id>/
  manifest.json
  stage-01-demucs-htdemucs/
    stage.json
    stems/                 # real run only
  stage-02-instrumental-stems/
    stage.json
    stems/                 # cascade run only
```

`manifest.json` records the input file, selected pipeline, stages, timing and output paths. `stage.json` records the effective command and status for that stage.

## Rules

- Preserve the original input.
- Do not overwrite old runs.
- Prefer WAV/float intermediates when a stage feeds another stage.
- Keep residual and unexpected outputs instead of deleting them silently.
- Treat cascades as experimental until compared against direct separation.
