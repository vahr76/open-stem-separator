#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_ID="${OSS_BUILD_ID:-$(date +%Y%m%d-%H%M%S)}"
DIST_DIR="${ROOT_DIR}/release/dist-linux-x64-${BUILD_ID}"
PAYLOAD_DIR="${DIST_DIR}/ytd-0.1.0-linux-x64"
ARCHIVE="${DIST_DIR}/ytd-0.1.0-linux-x64.tar.gz"

find_python() {
  command -v python3
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
    "$python_bin" -m PyInstaller --onefile --name ytd --distpath "$PAYLOAD_DIR" --workpath "$DIST_DIR/build" --specpath "$DIST_DIR" "$ROOT_DIR/oss.py"
  elif command -v pyinstaller >/dev/null 2>&1; then
    pyinstaller --onefile --name ytd --distpath "$PAYLOAD_DIR" --workpath "$DIST_DIR/build" --specpath "$DIST_DIR" "$ROOT_DIR/oss.py"
  else
    mkdir -p "$PAYLOAD_DIR"
    cp "$ROOT_DIR/oss.py" "$PAYLOAD_DIR/ytd.py"
    cat > "$PAYLOAD_DIR/ytd" <<'EOF'
#!/usr/bin/env sh
exec python3 "$(dirname "$0")/ytd.py" "$@"
EOF
    chmod +x "$PAYLOAD_DIR/ytd"
    printf '%s\n' "PyInstaller no está disponible; generé un paquete fuente que requiere Python 3."
  fi
}

mkdir -p "$PAYLOAD_DIR/bin" "$PAYLOAD_DIR/legal"

python_bin="$(find_python)"
build_app "$python_bin"

copy_if_found yt-dlp "$PAYLOAD_DIR/bin"
copy_if_found ffmpeg "$PAYLOAD_DIR/bin"
copy_if_found ffprobe "$PAYLOAD_DIR/bin"
copy_if_found deno "$PAYLOAD_DIR/bin"

cp "$ROOT_DIR/README.md" "$PAYLOAD_DIR/README.md"
cp "$ROOT_DIR/dependencies.json" "$PAYLOAD_DIR/dependencies.json"
cp "$ROOT_DIR/legal/THIRD_PARTY_NOTICES.md" "$PAYLOAD_DIR/legal/THIRD_PARTY_NOTICES.md"

tar -czf "$ARCHIVE" -C "$DIST_DIR" "ytd-0.1.0-linux-x64"
printf 'Build listo: %s\n' "$ARCHIVE"
