#!/usr/bin/env bash
set -euo pipefail

APP_NAME="OSS"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_INSTALL_DIR="${HOME}/.local/share/oss"
DEFAULT_DOWNLOADS_DIR="${HOME}/Music/OSS/downloads"
DEFAULT_COMMAND_DIR="${HOME}/.local/bin"

prompt() {
  local label="$1"
  local fallback="$2"
  local value
  read -r -p "${label} [${fallback}]: " value
  printf '%s\n' "${value:-$fallback}"
}

require_writable_dir() {
  local directory="$1"
  mkdir -p "$directory"
  local probe
  probe="$(mktemp "${directory}/.oss-write-check.XXXXXX")"
  rm -f "$probe"
}

copy_app() {
  local install_dir="$1"
  mkdir -p "$install_dir"
  cp "$SCRIPT_DIR/oss.py" "$install_dir/oss.py"
  if [ -d "$SCRIPT_DIR/bin" ]; then
    mkdir -p "$install_dir/bin"
    cp -R "$SCRIPT_DIR/bin/." "$install_dir/bin/"
  fi
  chmod +x "$install_dir/oss.py"
}

write_command() {
  local command_dir="$1"
  local install_dir="$2"
  mkdir -p "$command_dir"
  cat > "${command_dir}/ytd" <<EOF
#!/usr/bin/env sh
exec python3 "${install_dir}/oss.py" "\$@"
EOF
  chmod +x "${command_dir}/ytd"
}

path_hint() {
  local command_dir="$1"
  case ":${PATH}:" in
    *":${command_dir}:"*) ;;
    *) printf '%s\n' "Agregá esto a tu shell si ytd no aparece como comando: export PATH=\"${command_dir}:\$PATH\"" ;;
  esac
}

download_if_missing() {
  local install_dir="$1"
  mkdir -p "$install_dir/bin"
  if ! command -v yt-dlp >/dev/null 2>&1 && [ ! -x "$install_dir/bin/yt-dlp" ]; then
    printf '%s\n' "Descargando yt-dlp..."
    curl -L --fail --output "$install_dir/bin/yt-dlp" "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp"
    chmod +x "$install_dir/bin/yt-dlp"
  fi
  if ! command -v ffmpeg >/dev/null 2>&1 || ! command -v ffprobe >/dev/null 2>&1; then
    printf '%s\n' "FFmpeg/ffprobe no están en PATH. Instalalos con tu gestor de paquetes o agregalos a ${install_dir}/bin."
  fi
  if ! command -v deno >/dev/null 2>&1; then
    printf '%s\n' "Deno no está en PATH. YouTube puede requerirlo para JavaScript/EJS."
  fi
}

printf '%s\n' "Instalando ytd..."
install_dir="$DEFAULT_INSTALL_DIR"
command_dir="$DEFAULT_COMMAND_DIR"
downloads_dir="$(prompt "Carpeta de descargas" "$DEFAULT_DOWNLOADS_DIR")"

require_writable_dir "$install_dir"
require_writable_dir "$downloads_dir"
require_writable_dir "$command_dir"
copy_app "$install_dir"
write_command "$command_dir" "$install_dir"

download_if_missing "$install_dir"

python3 "$install_dir/oss.py" configure --downloads-dir "$downloads_dir" --install-mode online

printf '%s\n' ""
printf '%s\n' "$APP_NAME instalado."
printf '%s\n' "Comando: ytd"
path_hint "$command_dir"
