# Distribution matrix

OSS Downloader Core (`ytd`) must stay multiplatform from the start. The product target is a simple installed command on every supported OS:

```sh
ytd
```

## Tier 1 targets

These are the first targets for public releases.

| OS | Package | Goal | Notes |
| --- | --- | --- | --- |
| Windows x64 | `.zip` + `install.cmd`, later `.msi` | User can install without Python | Build on Windows; include `ytd.exe`, yt-dlp, FFmpeg, ffprobe, Deno |
| macOS arm64 | `.zip` + `install-macos.sh`, later signed `.pkg` | Native Apple Silicon support | Build on macOS arm64; notarization later |
| macOS x64 | `.zip` + `install-macos.sh`, later signed `.pkg` | Intel Mac support | Build on macOS x64 or universal build |
| Linux x64 generic | `.tar.gz` + `install.sh` | Works across most distros | First Linux artifact; no root required |

## Current priority

Windows and macOS packages are more important for the first musician-facing release than distro-specific Linux packages. Linux generic `.tar.gz` remains supported, while `.deb`, `.rpm`, Arch and AppImage are deferred until Windows/macOS packages exist.

## Tier 2 Linux packages

These should be generated from the same staged payload as the generic Linux package.

| Distro family | Package | Typical tool |
| --- | --- | --- |
| Debian / Ubuntu / Mint | `.deb` | `dpkg-deb`, `fpm`, or nfpm |
| Fedora / RHEL / Rocky | `.rpm` | `rpmbuild`, `fpm`, or nfpm |
| openSUSE / SUSE | `.rpm` | `rpmbuild`, `fpm`, or nfpm |
| Arch / Manjaro | `PKGBUILD` / `.pkg.tar.zst` | `makepkg` |
| AppImage | `.AppImage` | appimagetool |

The generic `.tar.gz` should remain available even after distro packages exist. It is the fallback package for unsupported distros.

## Build rule

Every package should be produced from the same staged payload:

```text
stage/
  ytd
  bin/
    yt-dlp
    ffmpeg
    ffprobe
    deno
  legal/
  README.md
  dependencies.json
  manifest.json
  SHA256SUMS.txt
  install.sh or platform installer
  uninstall.sh where applicable
```

The packaging layer changes the container format, not the app behavior.

## CI matrix goal

A future GitHub Actions or external CI setup should build:

```text
windows-latest: ytd-<version>-windows-x64.zip
macos-14:      ytd-<version>-macos-arm64.zip
macos-13:      ytd-<version>-macos-x64.zip
ubuntu-latest: ytd-<version>-linux-x64.tar.gz
windows-latest: ytd-<version>-windows-x64.zip, with install.cmd
# Later:
ubuntu-latest: ytd-<version>-linux-x64.deb
ubuntu-latest: ytd-<version>-linux-x64.rpm
archlinux:     PKGBUILD / pkg.tar.zst
```

CI requires a GitHub token with workflow permission. Until then, workflows can stay outside the committed tree or be added manually through GitHub.

## Packaging principles

- Install into user-writable locations by default.
- Do not require administrator/root for the generic packages.
- Keep per-OS installers thin; selection logic stays in `oss.py`.
- Pin dependency versions and hashes for public releases.
- Include license notices for the exact binaries shipped.
- Do not ship Windows/macOS artifacts built on Linux and call them validated.
