$ErrorActionPreference = "Stop"

$AppName = "ytd"
$AppVersion = "0.1.3"
$Target = "windows-x64"
$PackageName = "$AppName-$AppVersion-$Target"
$RootDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$BuildId = if ($env:OSS_BUILD_ID) { $env:OSS_BUILD_ID } else { Get-Date -Format "yyyyMMdd-HHmmss" }
$DistDir = Join-Path $RootDir "release\dist-$Target-$BuildId"
$PayloadDir = Join-Path $DistDir $PackageName
$Archive = Join-Path $DistDir "$PackageName.zip"

function New-Directory($Path) {
    New-Item -ItemType Directory -Force -Path $Path | Out-Null
}

function Copy-IfFound($Name, $TargetDir) {
    $cmd = Get-Command $Name -ErrorAction SilentlyContinue
    if ($cmd) {
        Copy-Item -Path $cmd.Source -Destination (Join-Path $TargetDir $Name) -Force
    }
}

function Get-FileSha256($Path) {
    return (Get-FileHash -Algorithm SHA256 -Path $Path).Hash.ToLowerInvariant()
}

function Build-App($PayloadDir) {
    $pyinstaller = Get-Command pyinstaller.exe -ErrorAction SilentlyContinue
    if ($pyinstaller) {
        & $pyinstaller.Source --onefile --name ytd --distpath $PayloadDir --workpath (Join-Path $DistDir "build") --specpath $DistDir (Join-Path $RootDir "oss.py")
        Write-Host "Modo de app: binario PyInstaller"
        return
    }

    $python = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($python) {
        & $python.Source -m PyInstaller --version *> $null
        if ($LASTEXITCODE -eq 0) {
            & $python.Source -m PyInstaller --onefile --name ytd --distpath $PayloadDir --workpath (Join-Path $DistDir "build") --specpath $DistDir (Join-Path $RootDir "oss.py")
            Write-Host "Modo de app: binario PyInstaller"
            return
        }
    }

    Copy-Item -Path (Join-Path $RootDir "oss.py") -Destination (Join-Path $PayloadDir "ytd.py") -Force
    Set-Content -Path (Join-Path $PayloadDir "ytd.cmd") -Encoding ASCII -Value '@echo off`r`npy "%~dp0ytd.py" %*`r`n'
    Write-Host "Modo de app: wrapper fuente; requiere Python 3."
}

function Write-InstallCmd($PayloadDir) {
@'
@echo off
setlocal EnableExtensions

set "APP_NAME=ytd"
set "APP_VERSION=0.1.0"
set "PACKAGE_NAME=ytd-0.1.3-windows-x64"
set "SOURCE_DIR=%~dp0"
set "INSTALL_ROOT=%LOCALAPPDATA%\OSS"
set "INSTALL_DIR=%INSTALL_ROOT%\%PACKAGE_NAME%"
set "BIN_DIR=%LOCALAPPDATA%\OSS\bin"
set "LAUNCHER=%BIN_DIR%\ytd.cmd"

if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
if not exist "%BIN_DIR%" mkdir "%BIN_DIR%"

xcopy "%SOURCE_DIR%*" "%INSTALL_DIR%\" /E /I /Y >nul
if errorlevel 1 (
  echo OSS: no se pudo copiar el paquete a "%INSTALL_DIR%".
  exit /b 1
)

> "%LAUNCHER%" echo @echo off
>> "%LAUNCHER%" echo "%INSTALL_DIR%\ytd.exe" %%*
if not exist "%INSTALL_DIR%\ytd.exe" (
  > "%LAUNCHER%" echo @echo off
  >> "%LAUNCHER%" echo "%INSTALL_DIR%\ytd.cmd" %%*
)

set "USER_PATH="
for /f "tokens=2,*" %%A in ('reg query HKCU\Environment /v Path 2^>nul') do set "USER_PATH=%%B"
echo ;%USER_PATH%; | find /I ";%BIN_DIR%;" >nul
if errorlevel 1 (
  if defined USER_PATH (
    setx Path "%USER_PATH%;%BIN_DIR%" >nul
  ) else (
    setx Path "%BIN_DIR%" >nul
  )
  echo Se agrego "%BIN_DIR%" al PATH de usuario.
  echo Cierra y abre la terminal si Windows no reconoce ytd todavia.
)

echo OSS Downloader Core instalado.
echo Comando: ytd
endlocal
'@ | Set-Content -Path (Join-Path $PayloadDir "install.cmd") -Encoding ASCII
}

function Write-UninstallCmd($PayloadDir) {
@'
@echo off
setlocal EnableExtensions

set "PACKAGE_NAME=ytd-0.1.3-windows-x64"
set "INSTALL_ROOT=%LOCALAPPDATA%\OSS"
set "INSTALL_DIR=%INSTALL_ROOT%\%PACKAGE_NAME%"
set "BIN_DIR=%LOCALAPPDATA%\OSS\bin"
set "LAUNCHER=%BIN_DIR%\ytd.cmd"

if exist "%LAUNCHER%" del /f /q "%LAUNCHER%"
if exist "%INSTALL_DIR%" rmdir /s /q "%INSTALL_DIR%"

echo OSS Downloader Core desinstalado.
endlocal
'@ | Set-Content -Path (Join-Path $PayloadDir "uninstall.cmd") -Encoding ASCII
}

function Write-Manifest($PayloadDir) {
    $Files = @()
    Get-ChildItem -Path $PayloadDir -Recurse -File | Sort-Object FullName | ForEach-Object {
        $relative = $_.FullName.Substring($PayloadDir.Length + 1).Replace('\', '/')
        $Files += [ordered]@{
            path = $relative
            size = $_.Length
            sha256 = Get-FileSha256 $_.FullName
        }
    }

    $Bundled = [ordered]@{}
    foreach ($name in @('yt-dlp.exe', 'ffmpeg.exe', 'ffprobe.exe', 'deno.exe')) {
        $file = Join-Path (Join-Path $PayloadDir 'bin') $name
        if (Test-Path $file) {
            $Bundled[$name] = [ordered]@{
                path = "bin/$name"
                sha256 = Get-FileSha256 $file
            }
        }
    }

    $Manifest = [ordered]@{
        name = 'OSS Downloader Core'
        command = 'ytd'
        version = $AppVersion
        target = $Target
        created_at = (Get-Date).ToUniversalTime().ToString('o')
        install = '.\\install.cmd'
        uninstall = '.\\uninstall.cmd'
        bundled = $Bundled
        files = $Files
    }
    $Manifest | ConvertTo-Json -Depth 8 | Set-Content -Path (Join-Path $PayloadDir 'manifest.json') -Encoding UTF8
}

function Write-Checksums($PayloadDir) {
    $Lines = @()
    Get-ChildItem -Path $PayloadDir -Recurse -File | Where-Object { $_.Name -ne 'SHA256SUMS.txt' } | Sort-Object FullName | ForEach-Object {
        $relative = $_.FullName.Substring($PayloadDir.Length + 1).Replace('\', '/')
        $Lines += "$(Get-FileSha256 $_.FullName)  $relative"
    }
    $Lines | Set-Content -Path (Join-Path $PayloadDir 'SHA256SUMS.txt') -Encoding ASCII
}

New-Directory $PayloadDir
New-Directory (Join-Path $PayloadDir "bin")
New-Directory (Join-Path $PayloadDir "legal")

Build-App $PayloadDir
Copy-IfFound "yt-dlp.exe" (Join-Path $PayloadDir "bin")
Copy-IfFound "ffmpeg.exe" (Join-Path $PayloadDir "bin")
Copy-IfFound "ffprobe.exe" (Join-Path $PayloadDir "bin")
Copy-IfFound "deno.exe" (Join-Path $PayloadDir "bin")

Copy-Item -Path (Join-Path $RootDir "README.md") -Destination (Join-Path $PayloadDir "README.md") -Force
Copy-Item -Path (Join-Path $RootDir "COPYRIGHT_AND_USAGE.md") -Destination (Join-Path $PayloadDir "COPYRIGHT_AND_USAGE.md") -Force
Copy-Item -Path (Join-Path $RootDir "dependencies.json") -Destination (Join-Path $PayloadDir "dependencies.json") -Force
Copy-Item -Path (Join-Path $RootDir "legal\THIRD_PARTY_NOTICES.md") -Destination (Join-Path $PayloadDir "legal\THIRD_PARTY_NOTICES.md") -Force

Write-InstallCmd $PayloadDir
Write-UninstallCmd $PayloadDir
Write-Manifest $PayloadDir
Write-Checksums $PayloadDir

Compress-Archive -Path (Join-Path $PayloadDir '*') -DestinationPath $Archive -Force
Write-Host "Payload: $PayloadDir"
Write-Host "Build listo: $Archive"
