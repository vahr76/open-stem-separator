# ytd CLI reference

`ytd` is the downloader command for OSS Downloader Core. It wraps yt-dlp with a simple music-study oriented flow.

## Basic interactive mode

```sh
ytd
```

Starts the interactive flow:

1. checks for a yt-dlp update;
2. asks for a URL;
3. asks whether to download audio, video, or both;
4. asks for the output format when needed;
5. downloads into the configured downloads folder.

Default downloads folder:

```text
~/Music/OSS/downloads
```

On Windows, the equivalent user music folder is used when configured by the installer.

## Shortcut commands

### Download best original audio

```sh
ytd 'URL'
ytd original 'URL'
```

Uses the best audio stream selected by yt-dlp without converting it.

### Download WAV

```sh
ytd wav 'URL'
```

Uses the best available audio source and converts to WAV. This avoids further lossy compression but cannot restore quality missing from the source.

### Download FLAC

```sh
ytd flac 'URL'
```

Uses the best available audio source and converts to FLAC. This avoids further lossy compression but cannot restore quality missing from the source.

### Download MP3 320 kbps

```sh
ytd mp3 'URL'
```

Uses the best available audio source and converts to MP3 at 320 kbps.

### Download complete video

```sh
ytd video 'URL'
```

Downloads a complete playable video with audio, selecting the best available video and audio combination.

### Download video plus separate audio

```sh
ytd both 'URL'
```

Downloads two files:

- a complete video file;
- a separate audio file using the original audio profile.

In interactive mode, `Ambos` lets you choose the separate audio format.

## Configuration commands

### Show active configuration

```sh
ytd config
```

Shows:

- config file path;
- downloads folder;
- history file path;
- thumbnail mode.

### Configure downloads folder

```sh
ytd configure --downloads-dir '/path/with/write/permission'
```

Stores the downloads folder in the user config file.

Optional flags:

```sh
ytd configure --downloads-dir '/path' --thumbnails none
ytd configure --downloads-dir '/path' --thumbnails write
ytd configure --downloads-dir '/path' --thumbnails embed
```

Thumbnail modes:

- `none`: default; safest; thumbnails do not affect downloads.
- `write`: writes thumbnail as a side file.
- `embed`: tries to embed thumbnail in the output file; advanced mode and may fail depending on format/c codecs.

`--install-mode` is kept for installer metadata:

```sh
ytd configure --downloads-dir '/path' --install-mode online
```

## Isolated config for tests

Use a separate config file:

```sh
ytd --config /tmp/oss-test/config.json configure --downloads-dir /tmp/oss-test/downloads
ytd --config /tmp/oss-test/config.json mp3 'URL'
ytd --config /tmp/oss-test/config.json history
```

Or isolate a config directory:

```sh
OSS_CONFIG_DIR=/tmp/oss-test/config ytd configure --downloads-dir /tmp/oss-test/downloads
OSS_CONFIG_DIR=/tmp/oss-test/config ytd history
```

This avoids changing the real user config.

## History and convenience commands

### Show raw local history

```sh
ytd history
```

Shows recent history entries as JSON lines.

Limit entries:

```sh
ytd history --limit 5
```

History is stored as `history.jsonl` next to the active config, unless a custom history file is configured internally.

### Show last download

```sh
ytd last
```

Shows the last registered download in a readable form.

### Open last project folder

```sh
ytd open
```

Opens the last project folder from history. If there is no history, opens the configured downloads folder.

### Open downloads folder

```sh
ytd open downloads
```

Opens the configured downloads folder.

### Open a specific path

```sh
ytd open '/path/to/folder'
```

Platform behavior:

- Linux: uses `xdg-open`.
- Windows: uses `os.startfile`.
- macOS: uses `open` when macOS packaging exists.

## Diagnostics

```sh
ytd doctor
```

Checks bundled or PATH executables:

- `yt-dlp`
- `ffmpeg`
- `ffprobe`
- `deno`

`doctor` does not prove that a specific website/URL is accessible. It only checks local tools.

## Advanced commands

### Explicit download action

```sh
ytd download 'URL'
ytd download 'URL' --profile original
ytd download 'URL' --profile wav
ytd download 'URL' --profile flac
ytd download 'URL' --profile mp3
ytd download 'URL' --profile video
ytd download 'URL' --profile mp4
```

Profiles:

| Profile | Behavior |
| --- | --- |
| `original` | Best audio stream without conversion |
| `wav` | Best audio source converted to WAV |
| `flac` | Best audio source converted to FLAC |
| `mp3` | Best audio source converted to MP3 320 kbps |
| `video` | Best complete video with audio, MKV container |
| `mp4` | Best MP4/M4A combination available, MP4 container |

### Custom output folder for one command

```sh
ytd download 'URL' --profile flac --output '/path/to/project'
```

### Enable playlist explicitly

```sh
ytd download 'URL' --playlist
```

By default, playlists are disabled. A YouTube URL with playlist parameters downloads only the video unless `--playlist` is set.

### List formats

```sh
ytd formats 'URL'
```

Shows formats exposed by yt-dlp for inspection. Manual format ID selection is not implemented yet.

### Dry run

```sh
ytd download 'URL' --profile flac --dry-run
ytd flac 'URL' --dry-run
ytd both 'URL' --dry-run
```

Prints the generated yt-dlp command arguments without downloading.

## Global flags

Global flags go before the command:

```sh
ytd --config /tmp/oss-test/config.json history
ytd --config /tmp/oss-test/config.json download 'URL' --profile mp3
```

| Flag | Meaning |
| --- | --- |
| `--config PATH` | Use an alternate config file |

## Download quality rule

`ytd` does not ask the user to choose quality. It always asks yt-dlp for the best available source compatible with the selected profile.

The chosen format controls preservation/conversion, not source quality.

## Cookies

Cookies are automatic fallback. The normal flow does not ask for cookie flags.

If yt-dlp fails with login/session/cookie/403 style errors, `ytd` tries detected browser cookies automatically.

Advanced cookie options exist internally but are not part of the simple user flow yet.

## Thumbnails

Thumbnails are disabled by default:

```text
--thumbnails none
```

This prevents thumbnail failures from interrupting the main audio/video download.
