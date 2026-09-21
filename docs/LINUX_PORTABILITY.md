# Linux portability

The generic Linux package must be built on an older Linux base, not on a rolling desktop distribution.

## Why

PyInstaller bundles the Python application, but it does not make glibc portable. A binary built on CachyOS, Arch, or another rolling distribution can require a glibc version that is newer than the one available on Fedora, Ubuntu, Debian, Rocky, or other target machines.

The `v0.1.3` Linux package exposed this problem when a binary built on CachyOS required `GLIBC_2.44` and failed on Fedora.

## Release rule

For public `linux-x64` packages:

- build in GitHub Actions on `ubuntu-22.04`;
- use Python 3.12;
- package with PyInstaller there;
- inspect the resulting `ytd` binary with `objdump`;
- reject the build if it requires a glibc newer than `GLIBC_2.35`.

This does not guarantee compatibility with every Linux distribution, but it avoids publishing a binary tied to a very new rolling-release glibc.


## Bundled FFmpeg rule

The Linux package must not copy `/usr/bin/ffmpeg` or `/usr/bin/ffprobe` from the build runner unless their required shared libraries are bundled too. The release workflow downloads a static FFmpeg build and verifies the packaged `bin/ffmpeg` and `bin/ffprobe` with `-version` before uploading the artifact.

## Manual smoke test

On each target Linux machine, download the release tarball and run:

```sh
mkdir -p /tmp/oss-linux-test
cd /tmp/oss-linux-test

tar -xzf /path/to/ytd-0.1.4-linux-x64.tar.gz
cd ytd-0.1.4-linux-x64

./ytd doctor
./install.sh
ytd doctor
```

Use isolated configuration for download tests:

```sh
OSS_CONFIG_DIR=/tmp/oss-linux-test/config ytd configure --downloads-dir /tmp/oss-linux-test/downloads
OSS_CONFIG_DIR=/tmp/oss-linux-test/config ytd flac 'URL_PERMITIDA_DE_PRUEBA'
OSS_CONFIG_DIR=/tmp/oss-linux-test/config ytd history
OSS_CONFIG_DIR=/tmp/oss-linux-test/config ytd open downloads
```

Expected result:

- `doctor` runs without a glibc error;
- `yt-dlp`, `ffmpeg`, `ffprobe`, and `deno` are found;
- the download lands under `/tmp/oss-linux-test/downloads/Artist/Track/`;
- history records the download;
- uninstall removes the command without deleting downloads or config.

## Do not fix client machines by updating glibc

If the binary fails because of glibc, rebuild the package from an older base. Do not ask users to manually replace or upgrade glibc on their system.
