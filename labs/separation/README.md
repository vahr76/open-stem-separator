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
