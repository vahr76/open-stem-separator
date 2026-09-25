# OSS / Open Stem Separator — project status

Last updated: 2026-09-25

This document summarizes what has been implemented, what has been tested, what failed and was fixed, and what remains to be built. It is meant to be the working status document for the project, not marketing copy.

## Project direction

OSS started as a practical downloader core for musicians who need high-quality local audio/video material for study. The long-term target is a web/desktop-style music practice and analysis environment with stem separation, waveform playback, tempo and pitch tools, lyrics sync, metronome/click generation, chord/key analysis, MIDI extraction and export workflows.

The current implementation intentionally starts smaller: a reliable, portable command-line core named `ytd`, plus an experimental separation laboratory named `oss-lab`. The downloader remains lightweight. Heavy ML/audio experiments stay in the lab until the behavior, dependencies and packaging strategy are stable.

## Current public releases

Repository:

<https://github.com/vahr76/open-stem-separator>

Current recommended release:

<https://github.com/vahr76/open-stem-separator/releases/tag/v0.3.2>

Published assets for `v0.3.2`:

- `ytd-0.3.2-linux-x64.tar.gz`
- `ytd-0.3.2-windows-x64.zip`

Older milestones:

- `v0.1.x`: downloader core, installers, GitHub packaging, Linux/Windows release assets.
- `v0.2.x`: project-folder structure and project metadata around downloaded songs.
- `v0.3.0`: experimental `oss-lab` command for source-separation research.
- `v0.3.1`: automatic CUDA/CPU device selection and external Python support for packaged `oss-lab`.
- `v0.3.2`: fixed packaged `oss-lab` environment contamination when launching external ML engines.

## Implemented: downloader core `ytd`

The `ytd` command is the stable user-facing downloader core.

Implemented behavior:

- Interactive download flow.
- URL prompt.
- Download type selection:
  - audio;
  - video;
  - both.
- Audio format selection while always requesting best available source quality for the selected output format:
  - original best audio;
  - WAV;
  - FLAC;
  - MP3 320 kbps.
- Video download behavior oriented around best available video/audio combination.
- Automatic cookie retry for common yt-dlp cookie-related failures.
- Automatic browser cookie detection attempts.
- Filename sanitization.
- Removal of YouTube video ID from normal output names.
- Artist/track folder guessing from metadata/title.
- Local configuration for downloads directory.
- Default user-writable music folder behavior.
- Download history commands.
- Project metadata creation.
- Aliases/commands intended for simple user usage rather than `python path/to/script.py`.

Useful commands:

```sh
ytd
ytd doctor
ytd config
ytd configure --downloads-dir "$HOME/Music/OSS/downloads"
ytd last
ytd open
ytd history
```

## Implemented: project folder structure

Downloads now produce a song-oriented folder layout such as:

```text
~/Music/OSS/downloads/<Artist>/<Track>/
  <downloaded-media>
  metadata.json
  project.json
```

Example from a tested run:

```text
/home/ahermosa/Music/OSS/downloads/LP/Lost_On_You/
  LP_-_Lost_On_You_Official_Music_Video.flac
  metadata.json
  project.json
```

The `project.json` file is intended to become the central project manifest for future stems, analysis, lyrics, MIDI, exports and notes.

## Implemented: packaging and distribution

Implemented packaging:

- Linux x64 portable tarball.
- Windows x64 zip generated through GitHub Actions.
- Linux package includes bundled runtime tools:
  - `yt-dlp`;
  - static `ffmpeg`;
  - static `ffprobe`;
  - `deno`.
- Linux package includes `install.sh` and `uninstall.sh`.
- Windows package includes `.cmd` installer flow to avoid common PowerShell execution-policy friction.
- GitHub release process documented and tested.
- GitHub CLI workflow established.
- Automated GitHub Actions builds for Linux and Windows.

Relevant documentation:

- `docs/INSTALL.md`
- `docs/PACKAGING.md`
- `docs/GITHUB_RELEASE.md`
- `docs/WINDOWS_BUILD.md`
- `docs/LINUX_PORTABILITY.md`
- `docs/DISTRIBUTION_MATRIX.md`

## Implemented: experimental separation lab `oss-lab`

`oss-lab` is experimental and separate from `ytd`.

Implemented commands:

```sh
oss-lab separate
oss-lab benchmark
oss-lab measure
oss-lab compare
oss-lab reaper
```

Implemented lab capabilities:

- JSON-based separation configs.
- Demucs runner.
- Direct model tests.
- Multistage/cascade experiments.
- Stage-to-stage input references.
- Dry-run mode.
- Per-run `manifest.json`.
- Per-stage `stage.json`.
- Runtime command capture.
- Output hashing.
- Timing capture.
- Expected stem checks.
- Objective measurement via summed-stem reconstruction residual.
- Residual WAV generation.
- Comparison report generation between multiple runs.
- REAPER `.rpp` export for listening sessions.
- CUDA/CPU automatic device selection.
- External Python environment support through `OSS_LAB_PYTHON`.
- Device override through `OSS_LAB_DEVICE`.

Current Demucs configs:

```text
labs/separation/configs/demucs-htdemucs.json
labs/separation/configs/demucs-htdemucs-ft.json
labs/separation/configs/demucs-hdemucs-mmi.json
labs/separation/configs/demucs-vocal-then-instrumental.json
```

Device behavior:

- Configs use `"device": "auto"` by default.
- `oss-lab` probes PyTorch in the engine Python.
- If `torch.cuda.is_available()` is true, Demucs runs with `-d cuda`.
- If CUDA is not available, Demucs runs with `-d cpu`.
- `stage.json` records both `requested_device` and `effective_device`.

Example:

```json
"requested_device": "auto",
"effective_device": "cuda"
```

## Important fixed bug: packaged `oss-lab` and external Python

During real testing of `v0.3.1`, packaged `oss-lab` could call an external Demucs Python, but the PyInstaller runtime contaminated the subprocess environment with its own `LD_LIBRARY_PATH`.

Observed failure:

```text
urllib.error.URLError: <urlopen error unknown url type: https>
```

Root cause:

```text
LD_LIBRARY_PATH=/tmp/_MEI...
```

The external Python loaded PyInstaller's bundled `libcrypto.so.3` instead of the system library, breaking Python SSL/HTTPS. Demucs then failed while downloading model weights.

Fixed in `v0.3.2`:

- remove PyInstaller `_PYI_*` variables before launching external engines;
- remove frozen app `LD_LIBRARY_PATH` when it points to `/tmp/_MEI...`;
- restore `LD_LIBRARY_PATH_ORIG` when available;
- remove `PYTHONHOME` from the engine subprocess environment.

Validation after fix:

```text
manifest_status= ok
stage_status= ok
returncode= 0
requested_device= auto
effective_device= cuda
outputs= 4
```

## Real tests performed

### Downloader tests

The downloader was tested with multiple YouTube URLs and formats, including:

- audio-only FLAC;
- video/audio combinations;
- repeated downloads;
- automatic output folder creation;
- metadata generation;
- artist/track folder organization;
- filename sanitization.

Confirmed behaviors:

- downloads go to configured user-writable folder;
- `metadata.json` and `project.json` are written;
- audio format choices request best available source and then convert only when requested;
- output names no longer include YouTube IDs in normal cases;
- cookie fallback retries happen automatically.

### Linux release portability tests

Tested release package extraction from GitHub:

```sh
gh release download v0.3.2 --repo vahr76/open-stem-separator --pattern 'ytd-0.3.2-linux-x64.tar.gz'
tar -xzf ytd-0.3.2-linux-x64.tar.gz
cd ytd-0.3.2-linux-x64
./ytd doctor
```

Confirmed:

```text
OK yt-dlp
OK ffmpeg
OK ffprobe
OK deno
```

A previous Linux package failed because bundled `ffmpeg` depended on unavailable shared libraries such as `libavdevice.so.58`. This was fixed by bundling a static FFmpeg build.

### Windows release build tests

Windows package generation is tested through GitHub Actions. The package is not yet manually tested on a real Windows machine by the project owner.

Confirmed through CI:

- Python setup;
- runtime tool install;
- unit tests;
- Windows package build;
- package inspection;
- artifact upload.

Manual Windows install/runtime testing remains pending.

## Separation benchmark results

### Blur — first lab comparison

Documented results:

- `labs/separation/benchmarks/results/first-benchmark-blur-2026-09-25.md`
- `labs/separation/benchmarks/results/blur-first-comparison/COMPARISON.md`
- `labs/separation/benchmarks/results/blur-first-measurements/`

Result summary:

```text
direct htdemucs: -30.49 dB residual vs original
cascade:         -18.66 dB residual vs original
```

Interpretation:

- Direct `htdemucs` reconstructed the original more consistently than the first Demucs-only cascade on that sample.
- This does not prove direct `htdemucs` is always perceptually better.
- It does show the current Demucs-only cascade is not yet a default strategy.

### LP — Lost On You benchmark

Documented results:

- `docs/lab-notes/2026-09-25-lp-lost-on-you.md`
- `labs/separation/benchmarks/results/lp-lost-on-you/REPORT.md`
- `labs/separation/benchmarks/results/lp-lost-on-you/COMPARISON.md`

Benchmark input:

```text
LP - Lost On You
30-second excerpt starting around 45s
```

Run results:

| Config | Status | Time | Outputs |
| --- | --- | ---: | ---: |
| `demucs-htdemucs-direct` | ok | 17.444s | 4 |
| `demucs-htdemucs-ft-direct` | ok | 56.028s | 4 |
| `demucs-hdemucs-mmi-direct` | ok | 8.288s | 4 |
| `demucs-vocal-then-instrumental` | ok | 113.736s | 6 |

Objective residual comparison:

| Label | Residual RMS vs original | Residual peak | Summed outputs |
| --- | ---: | ---: | ---: |
| `htdemucs` | -18.63 dB | 0.216461 | 4 |
| `htdemucs_ft` | -16.57 dB | 0.276489 | 4 |
| `hdemucs_mmi` | -17.20 dB | 0.249207 | 4 |
| `cascade` | -14.94 dB | 0.319049 | 5 |

Interpretation:

- `htdemucs` direct was the best technical reconstruction in that LP excerpt.
- `hdemucs_mmi` was second.
- `htdemucs_ft` was slower and did not reconstruct better in this objective metric.
- The cascade was slower and reconstructed worse in this Demucs-only test.
- Listening tests are still required because residual is not the same as musical usefulness.

### Beatles — Baby You're A Rich Man

User-downloaded file:

```text
/home/ahermosa/Music/OSS/downloads/The_Beatles/Baby_Youre_A_Rich_Man_Remastered_2009/Baby_You_re_A_Rich_Man_Remastered_2009.flac
```

Measured run:

```text
/home/ahermosa/Music/OSS/separations/20260925-040122-demucs-htdemucs-direct
```

Measurement:

```text
input duration: 181.307s
final summed outputs: 4
reconstruction residual RMS vs original: -25.48 dB
residual peak: 0.150583
```

Output table:

| Stem | RMS dBFS | Peak dBFS | Clipped samples | Length delta frames |
| --- | ---: | ---: | ---: | ---: |
| bass | -21.05 | -3.95 | 0 | 0 |
| drums | -25.09 | -0.12 | 0 | 0 |
| other | -24.88 | -0.27 | 0 | 0 |
| vocals | -22.17 | -2.20 | 0 | 0 |

Interpretation:

- The separation is technically consistent.
- There is no clipping in the generated stems.
- All stems are sample-aligned with the original length.
- `-25.48 dB` residual is a good result for summed-stem reconstruction.
- This still does not prove perceptual quality; bass bleed, vocal artifacts and usefulness for practice must be judged by listening.

## How to run a real separation now

From an extracted release folder such as `ytd-0.3.2-linux-x64`:

```sh
OSS_LAB_PYTHON="/home/ahermosa/Documents/Codex/2026-09-20/files-mentioned-by-the-user-bass/outputs/oss/.venv-separation/bin/python" \
OSS_LAB_DEVICE=auto \
oss-lab separate \
  --config labs/separation/configs/demucs-htdemucs.json \
  --input "/path/to/song.flac" \
  --out "$HOME/Music/OSS/separations"
```

Then measure:

```sh
RUN="$(find "$HOME/Music/OSS/separations" -mindepth 1 -maxdepth 1 -type d | sort | tail -n 1)"
oss-lab measure "$RUN"
cat "$RUN/MEASUREMENT.md"
```

Export to REAPER:

```sh
oss-lab reaper "$RUN"
find "$RUN" -maxdepth 1 -name "*.rpp" -print
```

Compare two runs:

```sh
oss-lab compare "$RUN_A" "$RUN_B" \
  --label htdemucs \
  --label htdemucs_ft \
  --out "$HOME/Music/OSS/comparisons/example"
```

## What the current quality metrics mean

The current measurement does not know the true original stems. It only checks whether the generated stems can reconstruct the original when summed.

Key metric:

```text
reconstruction residual RMS vs original
```

Meaning:

- Sum generated stems.
- Subtract that sum from the original audio.
- Measure the RMS of what remains.
- More negative dB is better.

Practical rough guide:

| Residual RMS | Meaning |
| ---: | --- |
| `-30 dB` or lower | very good reconstruction |
| around `-25 dB` | good / acceptable reconstruction |
| around `-18 dB` | weak reconstruction |
| around `-10 dB` | poor reconstruction |

Limitations:

- It does not measure bass clarity.
- It does not measure vocal bleed.
- It does not detect musical artifacts reliably.
- It does not replace listening.
- It is not SDR/SIR/SAR because there are no ground-truth stems.

## Known technical requirements

For `oss-lab` real Demucs runs:

- a separate Python environment with Demucs installed is required;
- use `OSS_LAB_PYTHON` to point to that environment;
- PyTorch decides whether CUDA is actually usable;
- CUDA is considered available only when `torch.cuda.is_available()` is true;
- `nvidia-smi` should work if NVIDIA CUDA is expected.

Observed CUDA troubleshooting case:

- RTX 3060 was detected by PCI/kernel.
- PyTorch had a CUDA build.
- `nvidia-smi` initially failed to communicate with the NVIDIA driver.
- PyTorch initially returned `cuda_available=False`.
- After environment/driver state was usable, `oss-lab` successfully selected `effective_device=cuda`.

## What remains to implement

### Downloader / `ytd`

- Update old banner/version text so the CLI no longer says `versión 0.1` in newer releases.
- Improve help UX so users do not need to know config paths manually.
- Add friendly shortcuts for common lab actions once they are stable.
- Add safer path display and command examples after downloads complete.
- Add optional post-download action: separate now / open folder / open project.
- Add stronger metadata heuristics for third-party uploads where title/uploader do not equal artist.
- Add playlist/batch strategy.
- Add better failure reports for thumbnails/cookies/site-specific problems.

### `oss-lab`

- Add built-in config aliases, for example:
  - `--config htdemucs`;
  - `--config htdemucs_ft`;
  - `--config hdemucs_mmi`.
- Add a simpler command such as:

```sh
oss-lab separate --preset htdemucs --input song.flac
```

- Default `--out` based on the song project folder.
- Write lab results back into `project.json`.
- Add full-song benchmark presets.
- Add automatic measure after separation.
- Add automatic REAPER export option.
- Add progress parsing from Demucs output.
- Add cancellation/resume behavior.
- Add VRAM/RAM timing stats.
- Add GPU model and torch/CUDA metadata to manifests.
- Add a comparison command that can select the last N runs automatically.
- Add friendlier error messages for missing `OSS_LAB_PYTHON`, missing Demucs, missing CUDA driver, or model download failure.

### Separation engines still pending

Not yet integrated:

- BS-RoFormer.
- MelBand RoFormer.
- MDX / MDX23C.
- `python-audio-separator`.
- `htdemucs_6s` guitar/piano six-stem model tests.
- GPU-specific benchmark matrix.
- CPU vs CUDA speed comparison.
- Fedora and Ubuntu laptop validation.

The strongest current practical default is still direct Demucs `htdemucs`, because it is tested and stable in this codebase. The long-term target still points toward testing stronger open-source models such as BS-RoFormer for quality.

### Audio analysis features pending

Not implemented yet:

- key detection;
- chord detection;
- BPM/downbeat detection;
- click/metronome generation;
- lyric transcription/sync;
- vocal note extraction;
- bass note extraction;
- drum-to-MIDI extraction;
- export to EZdrummer-style MIDI workflows.

### Player/UI pending

Not implemented yet:

- web player;
- waveform display;
- stem mixer;
- mute/solo controls;
- tempo control;
- pitch control;
- karaoke/lyrics view;
- Logic/Reaper-inspired dark UI;
- project browser;
- export mix workflow.

### Packaging/distribution pending

- Manual Windows test on a real Windows machine.
- Manual Fedora test.
- Manual Ubuntu test.
- Decide whether Linux should stay portable tarball only for now.
- Decide later whether `.deb`, `.rpm`, Arch/Manjaro and SUSE packages are worth the maintenance cost.
- macOS packaging is deferred until there is access to macOS/Hackintosh hardware.

## Current recommendation

Short-term next steps:

1. Improve `oss-lab` UX so users do not need to remember config paths.
2. Add automatic `measure` after `separate` or a `--measure` flag.
3. Add project integration so separations are stored under the song project instead of only under a generic output folder.
4. Run a second model on the Beatles file and compare objective residual plus listening in REAPER.
5. Start integrating BS-RoFormer or `python-audio-separator` in the lab, not in the stable downloader.

Recommended next release target:

```text
v0.4.0
```

Reason: the next useful step is feature-level UX improvement for separation workflows, not just a patch fix.
