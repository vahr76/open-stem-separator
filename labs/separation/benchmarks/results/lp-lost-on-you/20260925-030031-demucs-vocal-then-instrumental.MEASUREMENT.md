# Separation measurement — demucs-vocal-then-instrumental

- run: `/tmp/oss-lp-lost-on-you-real-venv/2026-09-25T025909.055156Z-lp-lost-on-you/runs/lp-lost-on-you/20260925-030031-demucs-vocal-then-instrumental`
- input: `/tmp/oss-lp-lost-on-you-real-venv/2026-09-25T025909.055156Z-lp-lost-on-you/clips/lp-lost-on-you.wav`
- input duration: `30.000s`
- final summed outputs: `5`
- reconstruction residual RMS vs original: `-14.94 dB`
- residual peak: `0.319049`

## Outputs

| Stage | Role | RMS dBFS | Peak dBFS | Clipped samples | Length delta frames | Included in sum |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| stage-01-vocal-instrumental | no_vocals | -16.57 | -0.09 | 0 | 0 | False |
| stage-01-vocal-instrumental | vocals | -18.02 | -4.48 | 0 | 0 | True |
| stage-02-instrumental-stems | bass | -27.18 | -11.29 | 0 | 0 | True |
| stage-02-instrumental-stems | drums | -18.77 | -0.09 | 0 | 0 | True |
| stage-02-instrumental-stems | other | -26.04 | -7.79 | 0 | 0 | True |
| stage-02-instrumental-stems | vocals_residual | -55.26 | -27.23 | 0 | 0 | True |

These measurements check technical consistency only. They do not replace listening tests or ground-truth SDR when real stems are available.
