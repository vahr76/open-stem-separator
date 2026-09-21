# Third-party notices

This downloader module invokes or bundles third-party tools depending on the package variant.

## yt-dlp

- Project: https://github.com/yt-dlp/yt-dlp
- Purpose: media extraction and download engine.
- License: see the upstream project and the exact binary/source distribution used for a release.

## FFmpeg / ffprobe

- Project: https://ffmpeg.org/
- Purpose: media probing, merging, remuxing and audio conversion.
- License: FFmpeg builds may be LGPL or GPL depending on build flags and linked libraries. Release packages must identify the exact build and license terms.

## Deno

- Project: https://deno.com/
- Purpose: JavaScript runtime used by yt-dlp for extractor challenges when needed.
- License: see the upstream project and the exact binary/source distribution used for a release.

## Release rule

Before publishing an autocontained package, pin exact versions, store SHA-256 hashes, and include the license texts required by the binaries actually shipped.
