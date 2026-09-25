# Lab note — LP - Lost On You separation benchmark

Date: 2026-09-25.

This note records the first user-selected song benchmark in OSS. It is part of the project history because it shaped the separation strategy: objective checks are useful, but they do not replace listening, and short benchmark excerpts are not the same as full-song separation.

## Source

Downloaded with `ytd` from:

```text
https://www.youtube.com/watch?v=hn3wJ1_1Zsg
```

Selected output: FLAC.

Local file used as benchmark source:

```text
/home/ahermosa/Music/OSS/downloads/LP/Lost_On_You/LP_-_Lost_On_You_Official_Music_Video.flac
```

The benchmark did **not** process the full song. It created a 30-second excerpt starting at 45 seconds. This was intentional: compare multiple candidates quickly before spending CPU on full-song separation.

## Benchmark command

The benchmark JSON used during the run was temporary:

```text
/tmp/oss-lp-lost-on-you-benchmark.json
```

Equivalent command:

```sh
cd /home/ahermosa/Documents/Codex/2026-09-20/files-mentioned-by-the-user-bass/outputs/oss
. .venv-separation/bin/activate

python3 oss_lab.py benchmark \
  --benchmark /tmp/oss-lp-lost-on-you-benchmark.json \
  --out /tmp/oss-lp-lost-on-you-real-venv
```

The venv was required because Demucs is not bundled in the lightweight `ytd` / `oss-lab` package. The package can run lab dry-runs and reports, but real ML separation currently needs an external Python environment with Demucs installed.

## Real benchmark output

Run root:

```text
/tmp/oss-lp-lost-on-you-real-venv/2026-09-25T025909.055156Z-lp-lost-on-you
```

Versioned report copy:

```text
labs/separation/benchmarks/results/lp-lost-on-you/REPORT.md
```

## Candidates tested

| Candidate | Mode | Result | Time | Outputs |
| --- | --- | --- | ---: | ---: |
| `htdemucs` | direct four-stem | ok | 17.444s | 4 |
| `htdemucs_ft` | direct four-stem | ok | 56.028s | 4 |
| `hdemucs_mmi` | direct four-stem | ok | 8.288s | 4 |
| Demucs cascade | vocal/instrumental then instrumental stems | ok | 113.736s | 6 |

The Demucs-only cascade is not the final intended cascade. The intended future cascade should test stronger vocal/instrumental models such as BS-RoFormer or MelBand RoFormer before deciding anything.

## Objective reconstruction comparison

Comparison root:

```text
/tmp/oss-lp-lost-on-you-compare
```

Versioned comparison copy:

```text
labs/separation/benchmarks/results/lp-lost-on-you/COMPARISON.md
```

| Candidate | Reconstruction residual vs original | Interpretation |
| --- | ---: | --- |
| `htdemucs` | -18.63 dB | Best reconstruction among tested candidates |
| `hdemucs_mmi` | -17.20 dB | Second by reconstruction metric |
| `htdemucs_ft` | -16.57 dB | Slower and worse reconstruction on this excerpt |
| Demucs cascade | -14.94 dB | Worst reconstruction on this excerpt |

More negative residual dB is better for this metric: it means the sum of selected stems is closer to the original excerpt.

This is not a complete perceptual quality score. It does not directly prove bass clarity, vocal bleed, drum transient quality, hiss, musical usefulness, or artifacts. It only measures how much signal remains after summing the selected outputs and subtracting that sum from the original.

## How to listen

Open this comparison project in REAPER:

```text
/tmp/oss-lp-lost-on-you-compare/comparison.rpp
```

Listen in this order:

1. Solo `00 original`.
2. Solo each reconstruction track and compare tonal changes.
3. Solo each residual track.
4. If a residual contains strong musical content, transients, bass, vocal phrases or pumping artifacts, that method altered or failed to reconstruct more material.

Generated individual REAPER sessions were also created in each run directory.

## Current conclusion

For this 30-second LP - Lost On You excerpt, direct `htdemucs` is the best current candidate by reconstruction metric and should be the first full-song separation candidate.

The result does not eliminate other engines. It only says that, among the currently implemented Demucs candidates on this excerpt, the direct `htdemucs` baseline is strongest technically and fastest enough to keep testing.

## Next full-song command

To separate the complete FLAC with the current best candidate:

```sh
cd /home/ahermosa/Documents/Codex/2026-09-20/files-mentioned-by-the-user-bass/outputs/oss
. .venv-separation/bin/activate

python3 oss_lab.py separate \
  --config labs/separation/configs/demucs-htdemucs.json \
  --input "/home/ahermosa/Music/OSS/downloads/LP/Lost_On_You/LP_-_Lost_On_You_Official_Music_Video.flac" \
  --out /tmp/oss-lp-full-separation
```

After that, measure and export to REAPER:

```sh
RUN="$(find /tmp/oss-lp-full-separation -mindepth 1 -maxdepth 1 -type d | sort | tail -n 1)"
python3 labs/separation/tools/measure_run.py "$RUN"
python3 labs/separation/tools/reaper_project.py "$RUN"
```

## Product implications

- `oss-lab` is a good separation development interface, but real ML engines should stay separate from the lightweight downloader package.
- The final OSS app should preserve intermediate files, residuals, manifests and comparison reports.
- A future visual player should expose original, stems, reconstruction and residual in a simplified Reaper-like workflow.
- Benchmarks should include both objective reconstruction checks and human listening notes.
