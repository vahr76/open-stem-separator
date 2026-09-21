# Windows build and package

The user-facing Windows installer should be `install.cmd`, not PowerShell. This avoids Execution Policy prompts and keeps the first run simple for musicians and non-developers.

## Target package

```text
ytd-0.1.0-windows-x64.zip
  install.cmd
  uninstall.cmd
  ytd.exe
  bin/
    yt-dlp.exe
    ffmpeg.exe
    ffprobe.exe
    deno.exe
  legal/
    THIRD_PARTY_NOTICES.md
  README.md
  COPYRIGHT_AND_USAGE.md
  dependencies.json
  manifest.json
  SHA256SUMS.txt
```

If PyInstaller is not available, the build script may create a source wrapper fallback with `ytd.py` and `ytd.cmd`, but public Windows releases should use `ytd.exe`.

## Developer build on Windows

Open PowerShell as a normal user inside the repository root:

```powershell
py -m venv .venv-build
.\.venv-build\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install pyinstaller
.\tools\build-windows.ps1
```

If PowerShell blocks `Activate.ps1`, use the venv Python directly:

```powershell
.\.venv-build\Scripts\python.exe -m pip install --upgrade pip
.\.venv-build\Scripts\python.exe -m pip install pyinstaller
$env:PATH = "$PWD\.venv-build\Scripts;$env:PATH"
.\tools\build-windows.ps1
```

The generated user package should be under:

```text
release\dist-windows-x64-<date>\ytd-0.1.0-windows-x64.zip
```

## User install

The user downloads and extracts the zip, then runs:

```cmd
install.cmd
```

The installer copies the package to:

```text
%LOCALAPPDATA%\OSS\ytd-0.1.0-windows-x64
```

and creates:

```text
%LOCALAPPDATA%\OSS\bin\ytd.cmd
```

It also adds `%LOCALAPPDATA%\OSS\bin` to the user's PATH if it is missing. The user may need to close and reopen the terminal.

## User uninstall

```cmd
uninstall.cmd
```

## Notes

- Build Windows packages on Windows.
- Do not claim Linux-built Windows packages are validated.
- Later we can add `.msi`, code signing, and SmartScreen-friendly distribution.
