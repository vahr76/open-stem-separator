# OSS separation comparison

- input: `/tmp/oss-lp-lost-on-you-real-venv/2026-09-25T025909.055156Z-lp-lost-on-you/clips/lp-lost-on-you.wav`
- REAPER project: `/tmp/oss-lp-lost-on-you-compare/comparison.rpp`

## Technical comparison

| Run | Residual dB vs original | Residual peak | Outputs summed | Reconstruction WAV | Residual WAV |
| --- | ---: | ---: | ---: | --- | --- |
| htdemucs | -18.63 | 0.216461 | 4 | `/tmp/oss-lp-lost-on-you-compare/01-htdemucs-reconstruction.wav` | `/tmp/oss-lp-lost-on-you-real-venv/2026-09-25T025909.055156Z-lp-lost-on-you/runs/lp-lost-on-you/20260925-025909-demucs-htdemucs-direct/reconstruction_residual.wav` |
| htdemucs_ft | -16.57 | 0.276489 | 4 | `/tmp/oss-lp-lost-on-you-compare/02-htdemucs_ft-reconstruction.wav` | `/tmp/oss-lp-lost-on-you-real-venv/2026-09-25T025909.055156Z-lp-lost-on-you/runs/lp-lost-on-you/20260925-025926-demucs-htdemucs-ft-direct/reconstruction_residual.wav` |
| hdemucs_mmi | -17.20 | 0.249207 | 4 | `/tmp/oss-lp-lost-on-you-compare/03-hdemucs_mmi-reconstruction.wav` | `/tmp/oss-lp-lost-on-you-real-venv/2026-09-25T025909.055156Z-lp-lost-on-you/runs/lp-lost-on-you/20260925-030022-demucs-hdemucs-mmi-direct/reconstruction_residual.wav` |
| cascade | -14.94 | 0.319049 | 5 | `/tmp/oss-lp-lost-on-you-compare/04-cascade-reconstruction.wav` | `/tmp/oss-lp-lost-on-you-real-venv/2026-09-25T025909.055156Z-lp-lost-on-you/runs/lp-lost-on-you/20260925-030031-demucs-vocal-then-instrumental/reconstruction_residual.wav` |

## How to listen

1. Open the `.rpp` in REAPER.
2. Solo `00 original` and one reconstruction to compare tonal changes.
3. Solo each residual track. A lower/quieter residual means the summed stems reconstruct the original more closely.
4. Residual is not automatically “bad”; listen for musical content that should not be missing, phasing, pumping, hiss, or transients.
