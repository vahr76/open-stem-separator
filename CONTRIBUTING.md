# Contributing

Thanks for helping improve OSS Downloader Core (`ytd`).

## Development setup

```sh
python3 -m unittest discover -s tests -v
python3 oss.py doctor
python3 oss.py
```

The core intentionally avoids third-party Python packages. External tools are discovered from `bin/` next to the app first, then from PATH.

## Product rules

- Keep the default flow simple: URL, download type, format.
- Do not ask the user to choose quality. The program should always select the best available quality for the chosen format.
- Video means a complete playable video with audio.
- Both means two files: one complete video and one separate audio file.
- Cookies should be automatic fallback, not a normal user-facing flag.
- Thumbnails must not be able to break a normal download.
- Downloads should go to user-writable folders.
- Filenames should be safe for scripts and terminals.

## Tests

Add or update tests when changing command construction, project folder detection, cookie fallback, filename handling, or installer behavior.
