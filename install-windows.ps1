param(
    [string]$InstallDir,
    [string]$DownloadsDir,
    [string]$CommandDir
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

function Read-Default {
    param([string]$Label, [string]$Default)
    $value = Read-Host "$Label [$Default]"
    if ([string]::IsNullOrWhiteSpace($value)) { return $Default }
    return $value
}

function Require-WritableDir {
    param([string]$Directory)
    New-Item -ItemType Directory -Force -Path $Directory | Out-Null
    $probe = Join-Path $Directory (".oss-write-check." + [Guid]::NewGuid().ToString("N"))
    Set-Content -Path $probe -Value "OSS write check" -Encoding ASCII
    Remove-Item -Path $probe -Force
}

function Copy-App {
    param([string]$Target)
    New-Item -ItemType Directory -Force -Path $Target | Out-Null
    Copy-Item -Path (Join-Path $ScriptDir "oss.py") -Destination (Join-Path $Target "oss.py") -Force
    $sourceBin = Join-Path $ScriptDir "bin"
    if (Test-Path $sourceBin) {
        New-Item -ItemType Directory -Force -Path (Join-Path $Target "bin") | Out-Null
        Copy-Item -Path (Join-Path $sourceBin "*") -Destination (Join-Path $Target "bin") -Recurse -Force
    }
}

function Write-Command {
    param([string]$Target, [string]$InstallDir)
    New-Item -ItemType Directory -Force -Path $Target | Out-Null
    $command = Join-Path $Target "ytd.cmd"
    $content = "@echo off`r`n"
    $content += "py `"$InstallDir\oss.py`" %*`r`n"
    Set-Content -Path $command -Value $content -Encoding ASCII
}

function Write-PathHint {
    param([string]$Target)
    $items = $env:Path -split ";"
    if ($items -notcontains $Target) {
        Write-Host "Agrega esta carpeta al PATH si ytd no aparece como comando: $Target"
    }
}

function Download-IfMissing {
    param([string]$Target)
    $binDir = Join-Path $Target "bin"
    New-Item -ItemType Directory -Force -Path $binDir | Out-Null
    $ytDlp = Join-Path $binDir "yt-dlp.exe"
    if (-not (Get-Command "yt-dlp.exe" -ErrorAction SilentlyContinue) -and -not (Test-Path $ytDlp)) {
        Write-Host "Descargando yt-dlp..."
        Invoke-WebRequest -Uri "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe" -OutFile $ytDlp
    }
    if (-not (Get-Command "ffmpeg.exe" -ErrorAction SilentlyContinue) -or -not (Get-Command "ffprobe.exe" -ErrorAction SilentlyContinue)) {
        Write-Host "FFmpeg/ffprobe no estan en PATH. Instalalos con winget o agregalos a $binDir."
    }
    if (-not (Get-Command "deno.exe" -ErrorAction SilentlyContinue)) {
        Write-Host "Deno no esta en PATH. YouTube puede requerirlo para JavaScript/EJS."
    }
}

Write-Host "Instalando ytd..."

if ([string]::IsNullOrWhiteSpace($InstallDir)) {
    $InstallDir = Join-Path $env:LOCALAPPDATA "OSS"
}

if ([string]::IsNullOrWhiteSpace($DownloadsDir)) {
    $DownloadsDir = Read-Default "Carpeta de descargas" (Join-Path ([Environment]::GetFolderPath("MyMusic")) "OSS\downloads")
}

if ([string]::IsNullOrWhiteSpace($CommandDir)) {
    $CommandDir = Join-Path $env:LOCALAPPDATA "Microsoft\WindowsApps"
}

Require-WritableDir $InstallDir
Require-WritableDir $DownloadsDir
Require-WritableDir $CommandDir
Copy-App $InstallDir
Write-Command $CommandDir $InstallDir

Download-IfMissing $InstallDir

$python = Get-Command "py.exe" -ErrorAction SilentlyContinue
if ($python) {
    & $python.Source (Join-Path $InstallDir "oss.py") configure --downloads-dir $DownloadsDir --install-mode online
} else {
    $python = Get-Command "python.exe" -ErrorAction SilentlyContinue
    if (-not $python) { throw "Python no esta disponible todavia. El empaquetado final lo eliminara como requisito." }
    & $python.Source (Join-Path $InstallDir "oss.py") configure --downloads-dir $DownloadsDir --install-mode online
}

Write-Host ""
Write-Host "OSS instalado."
Write-Host "Comando: ytd"
Write-PathHint $CommandDir
