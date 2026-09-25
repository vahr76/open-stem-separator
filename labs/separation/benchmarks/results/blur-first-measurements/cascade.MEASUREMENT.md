# Separation measurement — demucs-vocal-then-instrumental

- run: `/tmp/oss-benchmark-real-one/2026-09-25T021903.895843Z-minimal-local/runs/blur-beetlebum/20260925-021915-demucs-vocal-then-instrumental`
- input: `/tmp/oss-benchmark-real-one/2026-09-25T021903.895843Z-minimal-local/clips/blur-beetlebum.wav`
- input duration: `20.000s`
- final summed outputs: `5`
- reconstruction residual RMS vs original: `-18.66 dB`
- residual peak: `0.196189`

## Outputs

| Stage | Role | RMS dBFS | Peak dBFS | Clipped samples | Length delta frames | Included in sum |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| stage-01-vocal-instrumental | no_vocals | -15.66 | -0.32 | 0 | 0 | False |
| stage-01-vocal-instrumental | vocals | -19.30 | -3.11 | 0 | 0 | True |
| stage-02-instrumental-stems | bass | -20.31 | -9.19 | 0 | 0 | True |
| stage-02-instrumental-stems | drums | -21.28 | -1.08 | 0 | 0 | True |
| stage-02-instrumental-stems | other | -21.49 | -3.92 | 0 | 0 | True |
| stage-02-instrumental-stems | vocals_residual | -32.21 | -8.71 | 0 | 0 | True |

These measurements check technical consistency only. They do not replace listening tests or ground-truth SDR when real stems are available.
