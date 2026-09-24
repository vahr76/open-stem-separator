# Installation

OSS currently ships the downloader command `ytd` as the first public asset of Open Stem Separator. The full stem-separation application is not implemented yet.

## Recommended release install

Download the package for your operating system from the latest GitHub release:

- Linux: `ytd-<version>-linux-x64.tar.gz`
- Windows: `ytd-<version>-windows-x64.zip`

Release page:

```text
https://github.com/vahr76/open-stem-separator/releases
```

## Linux

Extract the package and run the installer:

```sh
tar -xzf ytd-0.1.4-linux-x64.tar.gz
cd ytd-0.1.4-linux-x64
./install.sh
```

The installer creates a user-level command named `ytd`, normally under:

```text
~/.local/bin/ytd
```

If your shell does not find it, add `~/.local/bin` to `PATH`.

Validate the install:

```sh
ytd doctor
ytd config
```

For isolated tests that do not touch your real configuration:

```sh
OSS_CONFIG_DIR=/tmp/oss-test/config ytd configure --downloads-dir /tmp/oss-test/downloads
OSS_CONFIG_DIR=/tmp/oss-test/config ytd doctor
```

## Windows

Extract the zip and run:

```bat
install.cmd
```

The installer creates:

```text
%LOCALAPPDATA%\OSS\bin\ytd.cmd
```

It also adds the OSS bin folder to the user PATH when possible. Open a new terminal after installing and run:

```bat
ytd doctor
ytd config
```

`install.cmd` is preferred over a direct PowerShell installer for normal users because it avoids common execution-policy friction.

## Source checkout for development

From the repository root:

```sh
python3 -m unittest discover -s tests -v
python3 oss.py doctor
python3 oss.py --help
```

The source checkout expects local tools in `PATH` unless you place bundled tools under `bin/`:

- `yt-dlp`
- `ffmpeg`
- `ffprobe`
- `deno`

For normal users, use the release package instead of running `python3 oss.py` manually.

## Uninstall

Linux:

```sh
./uninstall.sh
```

Windows:

```bat
uninstall.cmd
```

Uninstall removes the command and installed package files. It does not delete downloads, project folders, or user configuration.
