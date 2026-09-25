# Separation engine coverage

This file tracks what has actually been run and what is still only a candidate.

## Covered now

- Demucs `htdemucs` direct four-stem baseline.
- Demucs `htdemucs_ft` direct four-stem candidate.
- Demucs `hdemucs_mmi` direct four-stem candidate.
- Demucs `htdemucs_ft` cascade:
  - stage 1: vocals / no_vocals;
  - stage 2: bass / drums / other / residual vocals from no_vocals.

## Not covered yet

- BS-RoFormer.
- MelBand RoFormer.
- MDX23C / MDX-Net family.
- `python-audio-separator` API integration.
- Six-stem guitar/piano candidates such as `htdemucs_6s`.
- GPU-specific runs and memory measurements.
- Cross-machine runs on Fedora and Ubuntu.

## Why this matters

The first measurement favored direct `htdemucs` over the current Demucs-only cascade for reconstruction consistency on one Blur fragment. That result is useful but narrow. It does not decide the whole OSS separation strategy, because the intended cascade depends on stronger vocal/instrumental models such as BS-RoFormer or MelBand RoFormer.
