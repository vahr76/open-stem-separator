# OSS separation comparison

- input: `/tmp/oss-benchmark-real-one/2026-09-25T021903.895843Z-minimal-local/clips/blur-beetlebum.wav`
- REAPER project: `/tmp/oss-compare-blur/comparison.rpp`

## Technical comparison

| Run | Residual dB vs original | Residual peak | Outputs summed | Reconstruction WAV | Residual WAV |
| --- | ---: | ---: | ---: | --- | --- |
| direct | -30.49 | 0.052521 | 4 | `/tmp/oss-compare-blur/01-direct-reconstruction.wav` | `/tmp/oss-benchmark-real-one/2026-09-25T021903.895843Z-minimal-local/runs/blur-beetlebum/20260925-021904-demucs-htdemucs-direct/reconstruction_residual.wav` |
| cascade | -18.66 | 0.196189 | 5 | `/tmp/oss-compare-blur/02-cascade-reconstruction.wav` | `/tmp/oss-benchmark-real-one/2026-09-25T021903.895843Z-minimal-local/runs/blur-beetlebum/20260925-021915-demucs-vocal-then-instrumental/reconstruction_residual.wav` |

## How to listen

1. Open the `.rpp` in REAPER.
2. Solo `00 original` and one reconstruction to compare tonal changes.
3. Solo each residual track. A lower/quieter residual means the summed stems reconstruct the original more closely.
4. Residual is not automatically “bad”; listen for musical content that should not be missing, phasing, pumping, hiss, or transients.
