# First real separation run — 2026-09-25

This note records the first successful local OSS separation-lab run. It is not a quality verdict and does not select a default model.

## Environment

- Host OS: CachyOS/Linux local workstation.
- Python environment: local `.venv-separation`.
- Engine: Demucs 4.1.0.
- Torch: 2.14.0+cu130.
- CUDA availability reported by Torch: false.
- Effective device: CPU.

## Input

A 20-second WAV test clip was generated from an existing local FLAC download:

```text
/home/ahermosa/Music/OSS/downloads/Blur/Beetlebum/Blur_-_Beetlebum_Official_Music_Video - audio.flac
```

The test clip path was:

```text
/tmp/oss-demucs-sample-20s.wav
```

## Direct baseline

Config:

```text
labs/separation/configs/demucs-htdemucs.json
```

Result:

- status: ok
- outputs: bass, drums, other, vocals
- observed wall time from wrapper command: about 4 seconds after model dependencies were available

## Cascade validation

Config:

```text
labs/separation/configs/demucs-vocal-then-instrumental.json
```

Validated run:

```text
/tmp/oss-separation-real-validated/20260925-021513-demucs-vocal-then-instrumental
```

Result:

- manifest status: ok
- missing outputs: none
- stage 1 output: vocals, no_vocals
- stage 1 elapsed: 36.725 seconds
- stage 2 output: bass, drums, other, vocals residual
- stage 2 elapsed: 37.003 seconds

## Immediate findings

- The lab can execute the direct and cascade Demucs flows from JSON config.
- Stage-to-stage input resolution works with `stage:stage-01-vocal-instrumental:stems/**/no_vocals.wav`.
- The first cascade test works on CPU but is slow enough that GPU/device handling must be treated as a product requirement, not an implementation detail.
- The second-stage `vocals.wav` from the instrumental split should be labeled as residual vocals in later UX and manifests.
- Heavy ML dependencies are much larger than the downloader core; installer strategy should stay separate from the lightweight `ytd` package.
