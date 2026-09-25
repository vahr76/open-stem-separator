# Separation measurement — demucs-htdemucs-direct

- run: `/tmp/oss-benchmark-real-one/2026-09-25T021903.895843Z-minimal-local/runs/blur-beetlebum/20260925-021904-demucs-htdemucs-direct`
- input: `/tmp/oss-benchmark-real-one/2026-09-25T021903.895843Z-minimal-local/clips/blur-beetlebum.wav`
- input duration: `20.000s`
- final summed outputs: `4`
- reconstruction residual RMS vs original: `-30.49 dB`
- residual peak: `0.052521`

## Outputs

| Stage | Role | RMS dBFS | Peak dBFS | Clipped samples | Length delta frames | Included in sum |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| stage-01-demucs-htdemucs | bass | -20.36 | -8.83 | 0 | 0 | True |
| stage-01-demucs-htdemucs | drums | -21.39 | -0.28 | 0 | 0 | True |
| stage-01-demucs-htdemucs | other | -21.07 | -2.25 | 0 | 0 | True |
| stage-01-demucs-htdemucs | vocals | -19.32 | -2.76 | 0 | 0 | True |

These measurements check technical consistency only. They do not replace listening tests or ground-truth SDR when real stems are available.
