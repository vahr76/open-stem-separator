# OSS project structure

A downloaded song is not only a file. For OSS it becomes a local project that can later receive stems, analysis, lyrics, exports and playback state.

This document defines the target folder contract. The current downloader already creates `Artist/Track/` folders and writes `metadata.json`; future versions should evolve that into this structure without breaking existing downloads.

## Goals

- Keep every song self-contained.
- Preserve the original downloaded media.
- Avoid destructive overwrites.
- Allow resumable processing stages.
- Record enough metadata to reproduce a result.
- Keep machine output separate from human edits.
- Prepare for stems, tempo, chords, lyrics, MIDI and exports.

## Target layout

```text
Artist/
└── Track/
    ├── project.json
    ├── metadata.json
    ├── downloads/
    │   ├── audio/
    │   └── video/
    ├── original/
    │   ├── original_audio.ext
    │   └── original_video.ext
    ├── stems/
    │   └── final/
    ├── analysis/
    │   ├── detected/
    │   └── user_edits/
    ├── lyrics/
    ├── midi/
    ├── exports/
    ├── work/
    │   └── stages/
    ├── cache/
    └── logs/
```

Not every folder must exist on day one. The downloader can create the minimum set, while separation and playback features create their own folders later.

## Current minimum

The current `ytd` core may keep using this simpler structure while the project contract is introduced:

```text
Artist/
└── Track/
    ├── metadata.json
    ├── downloaded files...
    └── project.json
```

`project.json` is now written by `ytd` when creating a project. Existing files do not need to be moved immediately.

## `project.json`

`project.json` is the canonical OSS project manifest. It should be small, stable and easy to inspect.

Initial shape:

```json
{
  "schema": 1,
  "app": "oss",
  "kind": "song-project",
  "created_at": "2026-09-24T00:00:00Z",
  "updated_at": "2026-09-24T00:00:00Z",
  "source": {
    "url": "https://example.org/video",
    "extractor": "yt-dlp",
    "webpage_url": "https://example.org/video",
    "id": "video-id"
  },
  "identity": {
    "artist": "Artist",
    "track": "Track",
    "artist_slug": "Artist",
    "track_slug": "Track",
    "confidence": "medium",
    "source": "title"
  },
  "media": [
    {
      "path": "Artist_-_Track.flac",
      "kind": "audio",
      "profile": "flac",
      "role": "shortcut",
      "size": 123456,
      "modified_at": "2026-09-24T00:00:00Z"
    }
  ],
  "stems": [],
  "analysis": {},
  "lyrics": {},
  "exports": [],
  "notes": []
}
```

## `metadata.json`

`metadata.json` remains the raw or lightly normalized metadata captured from yt-dlp:

- title;
- uploader/channel;
- duration;
- webpage URL;
- extractor ID;
- artist/track guess and confidence.

`project.json` should reference the clean identity and OSS state. `metadata.json` should preserve source metadata useful for debugging or later enrichment.


## Media registration

When a download completes successfully, `ytd` scans the project root for final media files and records them in `project.json["media"]`. It ignores `metadata.json`, `project.json`, partial files and temporary files. Existing media entries are deduplicated by relative path so rerunning a command does not create duplicate records.

This is intentionally conservative: files are not moved into nested folders yet. The manifest records what exists today while keeping the folder layout backward-compatible.

## Downloads and originals

`downloads/` stores what the downloader produced. `original/` is reserved for canonical source media selected as input for later processing.

For the current downloader, moving files into nested folders is optional. The important rule is to avoid deleting or overwriting existing downloads silently.

## Work stages

Heavy processing must be resumable:

```text
work/stages/
├── stage-01-demucs/
│   ├── stage.json
│   └── outputs...
├── stage-02-roformer-vocal/
│   ├── stage.json
│   └── outputs...
└── stage-03-reconcile/
    ├── stage.json
    └── outputs...
```

Each `stage.json` should record:

- input file hash;
- engine and version;
- model/checkpoint and hash;
- backend requested and backend used;
- parameters;
- start/end time;
- status;
- warnings and errors;
- output files and hashes.

## Final stems contract

Final stems exposed to the future app must be strict:

- same sample rate;
- same channel count;
- same duration in samples;
- common start at sample 0;
- no unexpected clipping;
- alignment report present;
- residual present when stems are generated from multiple sources.

Raw model outputs should not be treated as final app-ready stems until reconciliation validates them.

## Analysis and user edits

Detected analysis and human edits must remain separate:

```text
analysis/detected/
  tempo.json
  chords.json
  key.json
analysis/user_edits/
  tempo_edits.json
  chord_edits.json
```

The effective view is detected data plus user edits. OSS should never overwrite human corrections when rerunning detection.

## Lyrics

Lyrics can come from providers such as LRCLib or from local transcription later. Store provider results and user corrections separately:

```text
lyrics/
  detected.lrc
  detected.json
  user_edits.json
```

## Versioning rule

`project.json` was introduced in `v0.2.0` as a product-foundation change. Future schema changes should preserve backward compatibility or include migration notes.
