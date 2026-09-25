#!/usr/bin/env bash
set -euo pipefail

APP_NAME="ytd"
APP_VERSION="0.2.1"
TARGET="linux-x64"
PACKAGE_NAME="${APP_NAME}-${APP_VERSION}-${TARGET}"

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_ID="${OSS_BUILD_ID:-$(date +%Y%m%d-%H%M%S)}"
DIST_DIR="${ROOT_DIR}/release/dist-${TARGET}-${BUILD_ID}"
PAYLOAD_DIR="${DIST_DIR}/${PACKAGE_NAME}"
ARCHIVE="${DIST_DIR}/${PACKAGE_NAME}.tar.gz"

find_python() {
  command -v python3
}

version_of() {
  local exe="$1"
  if [ -x "$exe" ]; then
    "$exe" --version 2>&1 | head -n 1 || true
  fi
}

sha256_of() {
  local file="$1"
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$file" | awk '{print $1}'
  elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$file" | awk '{print $1}'
  else
    printf '%s' "unavailable"
  fi
}

copy_if_found() {
  local name="$1"
  local target="$2"
  local source
  source="$(command -v "$name" || true)"
  if [ -n "$source" ]; then
    cp "$source" "$target/$name"
    chmod +x "$target/$name"
  fi
}

build_app() {
  local python_bin="$1"
  if "$python_bin" -m PyInstaller --version >/dev/null 2>&1; then
    "$python_bin" -m PyInstaller --onefile --name "$APP_NAME" --distpath "$PAYLOAD_DIR" --workpath "$DIST_DIR/build" --specpath "$DIST_DIR" "$ROOT_DIR/oss.py"
    printf '%s\n' "Modo de app: binario PyInstaller"
  elif command -v pyinstaller >/dev/null 2>&1; then
    pyinstaller --onefile --name "$APP_NAME" --distpath "$PAYLOAD_DIR" --workpath "$DIST_DIR/build" --specpath "$DIST_DIR" "$ROOT_DIR/oss.py"
    printf '%s\n' "Modo de app: binario PyInstaller"
  else
    cp "$ROOT_DIR/oss.py" "$PAYLOAD_DIR/ytd.py"
    cat > "$PAYLOAD_DIR/ytd" <<'WRAPPER'
#!/usr/bin/env sh
exec python3 "$(dirname "$0")/ytd.py" "$@"
WRAPPER
    chmod +x "$PAYLOAD_DIR/ytd"
    printf '%s\n' "Modo de app: wrapper fuente; requiere Python 3."
  fi
}

write_installers() {
  cat > "$PAYLOAD_DIR/install.sh" <<'INSTALL'
#!/usr/bin/env sh
set -eu

APP_NAME="ytd"
APP_VERSION="0.2.1"
PACKAGE_NAME="ytd-0.2.1-linux-x64"
SOURCE_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
INSTALL_ROOT="${OSS_INSTALL_ROOT:-$HOME/.local/share/oss}"
INSTALL_DIR="$INSTALL_ROOT/$PACKAGE_NAME"
BIN_DIR="${OSS_BIN_DIR:-$HOME/.local/bin}"
LAUNCHER="$BIN_DIR/$APP_NAME"

mkdir -p "$INSTALL_DIR" "$BIN_DIR"
cp -R "$SOURCE_DIR/." "$INSTALL_DIR/"
cat > "$LAUNCHER" <<EOF_LAUNCHER
#!/usr/bin/env sh
exec "$INSTALL_DIR/ytd" "\$@"
EOF_LAUNCHER
chmod +x "$LAUNCHER"

printf '%s\n' "OSS Downloader Core instalado."
printf '%s\n' "Comando: $LAUNCHER"
printf '%s\n' "Si tu shell no lo encuentra, agregá $BIN_DIR a PATH."
INSTALL
  chmod +x "$PAYLOAD_DIR/install.sh"

  cat > "$PAYLOAD_DIR/uninstall.sh" <<'UNINSTALL'
#!/usr/bin/env sh
set -eu

APP_NAME="ytd"
APP_VERSION="0.2.1"
PACKAGE_NAME="ytd-0.2.1-linux-x64"
INSTALL_ROOT="${OSS_INSTALL_ROOT:-$HOME/.local/share/oss}"
INSTALL_DIR="$INSTALL_ROOT/$PACKAGE_NAME"
BIN_DIR="${OSS_BIN_DIR:-$HOME/.local/bin}"
LAUNCHER="$BIN_DIR/$APP_NAME"

if [ -f "$LAUNCHER" ]; then
  rm -f "$LAUNCHER"
fi
if [ -d "$INSTALL_DIR" ]; then
  rm -rf "$INSTALL_DIR"
fi
printf '%s\n' "OSS Downloader Core desinstalado."
UNINSTALL
  chmod +x "$PAYLOAD_DIR/uninstall.sh"
}

write_manifest() {
  local app_mode="source-wrapper"
  if [ ! -f "$PAYLOAD_DIR/ytd.py" ]; then
    app_mode="pyinstaller-onefile"
  fi
  python3 - "$PAYLOAD_DIR" "$APP_VERSION" "$TARGET" "$app_mode" <<'PY'
import json
import os
import pathlib
import subprocess
import sys
from datetime import datetime, timezone

payload = pathlib.Path(sys.argv[1])
version = sys.argv[2]
target = sys.argv[3]
app_mode = sys.argv[4]

def sha256(path):
    import hashlib
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def first_line(command):
    try:
        completed = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False)
    except OSError:
        return None
    return (completed.stdout or '').splitlines()[0] if completed.stdout else None

files = []
for path in sorted(payload.rglob('*')):
    if path.is_file():
        files.append({
            'path': str(path.relative_to(payload)),
            'size': path.stat().st_size,
            'sha256': sha256(path),
        })

bundled = {}
for name in ('yt-dlp', 'ffmpeg', 'ffprobe', 'deno'):
    exe = payload / 'bin' / name
    if exe.exists():
        bundled[name] = {
            'path': f'bin/{name}',
            'version': first_line([str(exe), '--version']),
            'sha256': sha256(exe),
        }

manifest = {
    'name': 'OSS Downloader Core',
    'command': 'ytd',
    'version': version,
    'target': target,
    'app_mode': app_mode,
    'created_at': datetime.now(timezone.utc).isoformat(),
    'install': './install.sh',
    'uninstall': './uninstall.sh',
    'bundled': bundled,
    'files': files,
}
(payload / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
PY
}

write_checksums() {
  (
    cd "$PAYLOAD_DIR"
    find . -type f ! -name SHA256SUMS.txt -print | sort | while IFS= read -r file; do
      if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "${file#./}"
      else
        shasum -a 256 "${file#./}"
      fi
    done > SHA256SUMS.txt
  )
}

mkdir -p "$PAYLOAD_DIR/bin" "$PAYLOAD_DIR/legal"

python_bin="$(find_python)"
build_app "$python_bin"

copy_if_found yt-dlp "$PAYLOAD_DIR/bin"
copy_if_found ffmpeg "$PAYLOAD_DIR/bin"
copy_if_found ffprobe "$PAYLOAD_DIR/bin"
copy_if_found deno "$PAYLOAD_DIR/bin"

cp "$ROOT_DIR/README.md" "$PAYLOAD_DIR/README.md"
cp "$ROOT_DIR/COPYRIGHT_AND_USAGE.md" "$PAYLOAD_DIR/COPYRIGHT_AND_USAGE.md"
cp "$ROOT_DIR/dependencies.json" "$PAYLOAD_DIR/dependencies.json"
cp "$ROOT_DIR/legal/THIRD_PARTY_NOTICES.md" "$PAYLOAD_DIR/legal/THIRD_PARTY_NOTICES.md"

write_installers
write_manifest
write_checksums

tar -czf "$ARCHIVE" -C "$DIST_DIR" "$PACKAGE_NAME"
printf 'Payload: %s\n' "$PAYLOAD_DIR"
printf 'Build listo: %s\n' "$ARCHIVE"
