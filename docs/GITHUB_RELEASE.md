# GitHub release guide

This guide describes how to publish OSS Downloader Core (`ytd`) on GitHub.

## Repository files

A public repository should include at least:

```text
README.md
LICENSE
COPYRIGHT_AND_USAGE.md
legal/THIRD_PARTY_NOTICES.md
CONTRIBUTING.md
SECURITY.md
oss.py
dependencies.json
install-linux.sh
install-macos.sh
install-windows.ps1
tools/build-linux.sh
docs/PACKAGING.md
docs/ROADMAP.md
docs/GITHUB_RELEASE.md
tests/test_core.py
```

## Suggested repository name

Good options:

- `oss-downloader-core`
- `open-stem-separator`
- `oss-ytd`

If the final product will become larger than the downloader, use `open-stem-separator` and title the first release `OSS Downloader Core v0.1.0`.

## Before creating a release

Run:

```sh
python3 -m unittest discover -s tests -v
python3 oss.py doctor
```

Then test manually:

```sh
python3 oss.py
python3 oss.py flac 'https://example.com/video'
python3 oss.py mp3 'https://example.com/video'
python3 oss.py video 'https://example.com/video'
python3 oss.py both 'https://example.com/video'
```

Use a URL you have permission to download.

## Build artifacts

A complete public release should attach:

```text
ytd-0.1.0-windows-x64.zip
ytd-0.1.0-macos-universal.zip
ytd-0.1.0-linux-x64.tar.gz
oss-0.1.0-source.tar.gz
SHA256SUMS.txt
```

For the current prototype, Linux/source artifacts may exist before Windows/macOS artifacts. Mark the release as pre-release if not all operating systems are validated.

## Tag and release

```sh
git init
git add .
git commit -m "Initial OSS Downloader Core release"
git branch -M main
git remote add origin https://github.com/USER/REPO.git
git push -u origin main
git tag v0.1.0
git push origin v0.1.0
```

Then create a GitHub Release from tag `v0.1.0` and upload the artifacts.

If using GitHub CLI:

```sh
gh release create v0.1.0 \
  --title "OSS Downloader Core v0.1.0" \
  --notes-file docs/release-notes/v0.1.0.md \
  release/dist-linux-x64-*/ytd-0.1.0-linux-x64.tar.gz \
  ../oss-package/oss-0.1.0-source.tar.gz
```

Adjust paths to the artifacts actually built.

## SHA-256 checksums

Generate checksums before upload:

```sh
sha256sum ytd-0.1.0-linux-x64.tar.gz oss-0.1.0-source.tar.gz > SHA256SUMS.txt
```

On macOS:

```sh
shasum -a 256 ytd-0.1.0-macos-universal.zip > SHA256SUMS.txt
```

On Windows PowerShell:

```powershell
Get-FileHash .\ytd-0.1.0-windows-x64.zip -Algorithm SHA256
```

## Legal checklist

Before publishing binary packages:

- confirm the license of each bundled yt-dlp artifact;
- confirm the license of the FFmpeg build used;
- include third-party notices and required license files;
- include source links for bundled tools;
- avoid implying that the app grants rights over third-party media;
- include `COPYRIGHT_AND_USAGE.md` in the repo and release package.
