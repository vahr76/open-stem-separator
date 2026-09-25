#!/usr/bin/env python3
"""Open Stem Separator: núcleo de descarga, sin dependencias Python externas."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from urllib.parse import urlsplit

ROOT = Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent
PROFILES = ('original', 'wav', 'flac', 'mp3', 'video', 'mp4')
PROFILE_LABELS = {
    'original': 'Audio original (mejor fuente)',
    'wav': 'WAV (mejor fuente)',
    'flac': 'FLAC (mejor fuente)',
    'mp3': 'MP3 320 kbps',
    'video': 'Video (mejor calidad)',
    'mp4': 'MP4 (mejor MP4 disponible)',
}
FLOW_FORMATS = {
    'audio': ('original', 'wav', 'flac', 'mp3'),
    'video': ('video', 'mp4'),
    'both': ('original', 'wav', 'flac', 'mp3'),
}
THUMBNAIL_MODES = ('none', 'write', 'embed')
BROWSERS = ('firefox', 'chrome', 'chromium', 'edge', 'brave', 'vivaldi')
DEFAULT_DOWNLOADS = Path.home() / 'Music' / 'OSS' / 'downloads'
NOISE_WORDS = (
    'official video', 'official music video', 'official audio', 'lyrics', 'lyric video',
    'letra', 'sub. espanol', 'sub español', 'subtitulado', 'traduccion', 'traducción',
    'remastered', 'full version', 'hd', 'hq', '4k', 'video', 'audio'
)
REVERSE_TITLE_HINTS = ('lyrics', 'lyric', 'letra', 'sub.', 'sub ', 'subtitulado', 'traduccion', 'traducción')


def config_dir():
    if os.name == 'nt':
        base = Path(os.environ.get('APPDATA') or Path.home() / 'AppData' / 'Roaming')
        return base / 'OSS'
    if sys.platform == 'darwin':
        return Path.home() / 'Library' / 'Application Support' / 'OSS'
    return Path(os.environ.get('XDG_CONFIG_HOME') or Path.home() / '.config') / 'oss'


CONFIG_PATH = config_dir() / 'config.json'
_ACTIVE_CONFIG_PATH = None


def active_config_path():
    if _ACTIVE_CONFIG_PATH is not None:
        return _ACTIVE_CONFIG_PATH
    explicit = os.environ.get('OSS_CONFIG')
    if explicit:
        return Path(explicit).expanduser()
    directory = os.environ.get('OSS_CONFIG_DIR')
    if directory:
        return Path(directory).expanduser() / 'config.json'
    return CONFIG_PATH


def set_config_path(path):
    global _ACTIVE_CONFIG_PATH
    _ACTIVE_CONFIG_PATH = Path(path).expanduser() if path else None


def load_config(path=None):
    path = path or active_config_path()
    try:
        with path.open('r', encoding='utf-8') as handle:
            data = json.load(handle)
    except FileNotFoundError:
        return {}
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def save_config(values, path=None):
    path = path or active_config_path()
    current = load_config(path)
    current.update({key: str(value) for key, value in values.items() if value is not None})
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8') as handle:
        json.dump(current, handle, ensure_ascii=False, indent=2)
        handle.write('\n')


def default_downloads():
    value = load_config().get('downloads_dir')
    return Path(value).expanduser() if value else DEFAULT_DOWNLOADS


def configured(name, fallback=None):
    value = load_config().get(name)
    return value if value not in ('', None) else fallback


def state_dir():
    if _ACTIVE_CONFIG_PATH is not None or os.environ.get('OSS_CONFIG') or os.environ.get('OSS_CONFIG_DIR'):
        return active_config_path().parent
    return config_dir()


def history_path():
    configured_path = configured('history_file')
    if configured_path:
        return Path(configured_path).expanduser()
    return state_dir() / 'history.jsonl'


def append_history(entry, path=None):
    path = Path(path).expanduser() if path else history_path()
    data = dict(entry)
    data.setdefault('timestamp', datetime.now(timezone.utc).isoformat())
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('a', encoding='utf-8') as handle:
            json.dump(data, handle, ensure_ascii=False, sort_keys=True)
            handle.write('\n')
    except OSError as exc:
        print(f'OSS: no pude escribir historial en {path}. ({exc})', file=sys.stderr)


def read_history(limit=None, path=None):
    path = Path(path).expanduser() if path else history_path()
    try:
        lines = path.read_text(encoding='utf-8').splitlines()
    except FileNotFoundError:
        return []
    rows = []
    for line in lines:
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            rows.append({'status': 'invalid', 'raw': line})
    return rows[-limit:] if limit else rows


def last_history_entry():
    rows = [row for row in read_history() if row.get('status') != 'invalid']
    return rows[-1] if rows else None


def print_config():
    print(f'Config: {active_config_path()}')
    print(f'Descargas: {default_downloads()}')
    print(f'Historial: {history_path()}')
    print(f'Miniaturas: {configured("thumbnail_mode", "none")}')
    return 0


def print_last():
    row = last_history_entry()
    if not row:
        print('No hay descargas registradas todavía.')
        return 1
    print('Última descarga:')
    if row.get('artist'):
        print(f'Artista: {row.get("artist")}')
    if row.get('track'):
        print(f'Tema: {row.get("track")}')
    if row.get('title'):
        print(f'Título: {row.get("title")}')
    print(f'Perfil: {row.get("profile", "")}')
    print(f'Estado: {row.get("status", "")}')
    if row.get('project_dir'):
        print(f'Carpeta: {row.get("project_dir")}')
    print(f'URL: {row.get("url", "")}')
    return 0


def resolve_project_target(target='last'):
    if target in (None, '', 'last'):
        row = last_history_entry()
        if not row or not row.get('project_dir'):
            raise ValueError('No hay último proyecto registrado todavía.')
        return Path(row['project_dir']).expanduser().resolve()
    return Path(target).expanduser().resolve()


def print_project(target='last'):
    project_dir = resolve_project_target(target)
    manifest_path = project_dir / 'project.json'
    manifest = read_json_object(manifest_path)
    if not manifest:
        raise ValueError(f'No encontré project.json válido en {project_dir}.')
    identity = manifest.get('identity') if isinstance(manifest.get('identity'), dict) else {}
    source = manifest.get('source') if isinstance(manifest.get('source'), dict) else {}
    media = manifest.get('media') if isinstance(manifest.get('media'), list) else []
    stems = manifest.get('stems') if isinstance(manifest.get('stems'), list) else []
    analysis = manifest.get('analysis') if isinstance(manifest.get('analysis'), dict) else {}
    lyrics = manifest.get('lyrics') if isinstance(manifest.get('lyrics'), dict) else {}
    print('Proyecto OSS:')
    print(f'Carpeta: {project_dir}')
    print(f'Artista: {identity.get("artist", "")}')
    print(f'Tema: {identity.get("track", "")}')
    print(f'Confianza: {identity.get("confidence", "")}')
    print(f'URL: {source.get("webpage_url") or source.get("url") or ""}')
    print(f'Media: {len(media)}')
    for item in media:
        if not isinstance(item, dict):
            continue
        parts = [item.get('path', '')]
        details = []
        if item.get('kind'):
            details.append(item['kind'])
        if item.get('profile'):
            details.append(item['profile'])
        if item.get('size') is not None:
            details.append(f'{item["size"]} bytes')
        if details:
            parts.append('(' + ', '.join(str(part) for part in details) + ')')
        print('  - ' + ' '.join(parts))
    print(f'Stems: {len(stems)}')
    print(f'Análisis: {len(analysis)}')
    print(f'Letras: {len(lyrics)}')
    return 0


def short_time(value):
    if not value:
        return ''
    return str(value).replace('T', ' ')[:19]


def clip(value, width):
    value = '' if value is None else str(value)
    return value if len(value) <= width else value[:max(0, width - 1)] + '…'


def print_history(limit=20, json_output=False):
    rows = read_history(limit)
    if json_output:
        for row in rows:
            print(json.dumps(row, ensure_ascii=False))
        return 0
    if not rows:
        print('No hay descargas registradas todavía.')
        return 0
    headers = ('Fecha', 'Estado', 'Perfil', 'Artista', 'Tema')
    widths = (19, 6, 8, 22, 32)
    print('  '.join(header.ljust(width) for header, width in zip(headers, widths)))
    print('  '.join('-' * width for width in widths))
    for row in rows:
        values = (
            short_time(row.get('timestamp')),
            row.get('status', ''),
            row.get('profile', ''),
            row.get('artist', ''),
            row.get('track') or row.get('title') or row.get('url', ''),
        )
        print('  '.join(clip(value, width).ljust(width) for value, width in zip(values, widths)))
    return 0


def open_path(path):
    path = Path(path).expanduser().resolve()
    if os.name == 'nt':
        os.startfile(str(path))  # type: ignore[attr-defined]
        return 0
    opener = 'open' if sys.platform == 'darwin' else 'xdg-open'
    executable_path = shutil.which(opener)
    if not executable_path:
        raise ValueError(f'No encontré {opener} para abrir {path}.')
    subprocess.Popen([executable_path, str(path)])
    return 0


def open_target(target='last'):
    if target in (None, '', 'last'):
        row = last_history_entry()
        if row and row.get('project_dir'):
            return open_path(row['project_dir'])
        return open_path(default_downloads())
    if target == 'downloads':
        return open_path(default_downloads())
    return open_path(target)


def history_entry(url, profile, project_dir=None, status='ok', code=0, kind=None):
    entry = {
        'url': validate_url(url),
        'profile': profile,
        'status': status,
        'code': code,
    }
    if kind:
        entry['kind'] = kind
    if project_dir is not None:
        project = Path(project_dir)
        entry['project_dir'] = str(project)
        metadata_file = project / 'metadata.json'
        metadata = load_config(metadata_file)
        if metadata:
            entry['artist'] = metadata.get('artist_guess')
            entry['track'] = metadata.get('track_guess')
            entry['title'] = metadata.get('title')
            entry['source_id'] = metadata.get('id')
    return entry


def run_tracked(url, profile, project_dir, label=None, kind=None):
    code = run(command(url, profile, output=project_dir, label=label))
    if code == 0:
        register_project_media(project_dir, profile, kind)
    append_history(history_entry(url, profile, project_dir, 'ok' if code == 0 else 'error', code, kind))
    return code


def run_many_tracked(entries):
    final_code = 0
    for item in entries:
        code = run(command(item['url'], item['profile'], output=item['project_dir'], label=item.get('label')))
        if code == 0:
            register_project_media(item['project_dir'], item['profile'], item.get('kind'))
        append_history(history_entry(item['url'], item['profile'], item['project_dir'], 'ok' if code == 0 else 'error', code, item.get('kind')))
        if code:
            final_code = code
            break
    return final_code


def executable(name):
    bundled = ROOT / 'bin' / (name + ('.exe' if os.name == 'nt' else ''))
    return str(bundled) if bundled.is_file() else shutil.which(name)


def external_env():
    env = os.environ.copy()
    original_ld = env.get('LD_LIBRARY_PATH_ORIG')
    if original_ld is not None:
        env['LD_LIBRARY_PATH'] = original_ld
    elif getattr(sys, 'frozen', False):
        env.pop('LD_LIBRARY_PATH', None)
    for key in ('PYTHONHOME', 'PYTHONPATH'):
        env.pop(key, None)
    for key in list(env):
        if key.startswith('PYI_') or key.startswith('_PYI_'):
            env.pop(key, None)
    return env


def run_external(args, **kwargs):
    kwargs.setdefault('env', external_env())
    return subprocess.run(args, **kwargs)


def browser_available(browser):
    if browser == 'edge':
        candidates = ('msedge', 'microsoft-edge', 'microsoft-edge-stable')
    elif browser == 'brave':
        candidates = ('brave', 'brave-browser')
    elif browser == 'vivaldi':
        candidates = ('vivaldi', 'vivaldi-stable')
    elif browser == 'chrome':
        candidates = ('google-chrome', 'google-chrome-stable', 'chrome')
    else:
        candidates = (browser,)
    return any(shutil.which(candidate) for candidate in candidates)


def browser_profile_exists(browser):
    home = Path.home()
    if os.name == 'nt':
        appdata = Path(os.environ.get('APPDATA') or home / 'AppData' / 'Roaming')
        localappdata = Path(os.environ.get('LOCALAPPDATA') or home / 'AppData' / 'Local')
        paths = {
            'firefox': [appdata / 'Mozilla' / 'Firefox' / 'Profiles'],
            'chrome': [localappdata / 'Google' / 'Chrome' / 'User Data'],
            'chromium': [localappdata / 'Chromium' / 'User Data'],
            'edge': [localappdata / 'Microsoft' / 'Edge' / 'User Data'],
            'brave': [localappdata / 'BraveSoftware' / 'Brave-Browser' / 'User Data'],
            'vivaldi': [localappdata / 'Vivaldi' / 'User Data'],
        }
    elif sys.platform == 'darwin':
        paths = {
            'firefox': [home / 'Library' / 'Application Support' / 'Firefox' / 'Profiles'],
            'chrome': [home / 'Library' / 'Application Support' / 'Google' / 'Chrome'],
            'chromium': [home / 'Library' / 'Application Support' / 'Chromium'],
            'edge': [home / 'Library' / 'Application Support' / 'Microsoft Edge'],
            'brave': [home / 'Library' / 'Application Support' / 'BraveSoftware' / 'Brave-Browser'],
            'vivaldi': [home / 'Library' / 'Application Support' / 'Vivaldi'],
        }
    else:
        config_home = Path(os.environ.get('XDG_CONFIG_HOME') or home / '.config')
        paths = {
            'firefox': [home / '.mozilla' / 'firefox'],
            'chrome': [config_home / 'google-chrome'],
            'chromium': [config_home / 'chromium'],
            'edge': [config_home / 'microsoft-edge'],
            'brave': [config_home / 'BraveSoftware' / 'Brave-Browser', config_home / 'brave-browser'],
            'vivaldi': [config_home / 'vivaldi'],
        }
    return any(path.exists() for path in paths.get(browser, ()))


def detected_browsers():
    preferred = configured('cookies_from_browser')
    browsers = [preferred] if preferred else []
    browsers += [browser for browser in BROWSERS
                 if browser not in browsers and (browser_available(browser) or browser_profile_exists(browser))]
    return browsers


def normalize_url(value):
    value = str(value).strip().strip('"\'<>')
    markdown = re.fullmatch(r'\[([^\]]+)\]\((https?://[^)\s]+)\)', value)
    if markdown:
        return markdown.group(2)
    if value.startswith('[') and '](' in value:
        start = value.find('](') + 2
        end = value.find(')', start)
        if end > start:
            return value[start:end].strip().strip('"\'<>')
    return value


def validate_url(value):
    value = normalize_url(value)
    try:
        parsed = urlsplit(value)
        if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError()
    except ValueError:
        raise ValueError('Ingresá una URL HTTP/HTTPS válida, sin credenciales.') from None
    return value


def is_url(value):
    try:
        validate_url(value)
        return True
    except ValueError:
        return False


def validate_cookie_file(value):
    if not value:
        return None
    path = Path(value).expanduser().resolve()
    if not path.is_file():
        raise ValueError(f'No existe el archivo de cookies: {path}')
    try:
        with path.open('rb'):
            pass
    except OSError as exc:
        raise ValueError(f'No se puede leer el archivo de cookies: {path}. ({exc})') from exc
    return path


def safe_name(value, fallback='Unknown'):
    value = re.sub(r'[^\w\s.-]+', '', str(value), flags=re.UNICODE)
    value = re.sub(r'\s+', '_', value.strip())
    value = re.sub(r'_+', '_', value).strip('.- ')
    return value[:120] or fallback


def clean_title_part(value):
    value = re.sub(r'\([^)]*\)', '', str(value))
    value = re.sub(r'\[[^]]*\]', '', value)
    for word in NOISE_WORDS:
        value = re.sub(re.escape(word), '', value, flags=re.IGNORECASE)
    value = re.sub(r'\b(19|20)\d{2}\b', '', value)
    value = re.sub(r'\s+', ' ', value)
    return value.strip(' -_')


def word_count(value):
    return len([part for part in re.split(r'[\s_]+', str(value).strip()) if part])


def looks_like_reversed_title(left, right_raw, right_clean):
    right_lower = str(right_raw).lower()
    return (any(hint in right_lower for hint in REVERSE_TITLE_HINTS)
            and word_count(right_clean) <= 4
            and word_count(left) >= 4)


def guess_artist_track(info):
    title = info.get('title') or 'Unknown'
    artist = info.get('artist') or info.get('creator')
    track = info.get('track')
    source = 'metadata' if artist or track else 'fallback'
    confidence = 'medium' if artist or track else 'low'
    if not artist or not track:
        match = re.match(r'^\s*(.+?)\s+[-–—:]\s+(.+?)\s*$', title)
        if match:
            left = clean_title_part(match.group(1))
            right_raw = match.group(2)
            right = clean_title_part(right_raw)
            if looks_like_reversed_title(left, right_raw, right):
                artist = artist or right
                track = track or left
            else:
                artist = artist or left
                track = track or right
            source = 'title'
            confidence = 'medium'
    if not artist:
        artist = '_unsorted'
    if not track:
        track = clean_title_part(title) or title
    return {
        'artist': safe_name(artist, '_unsorted'),
        'track': safe_name(track, 'Unknown_Track'),
        'source': source,
        'confidence': confidence,
    }


def metadata_command(url):
    url = validate_url(url)
    engine = executable('yt-dlp')
    if not engine:
        raise ValueError('Falta yt-dlp. Ejecutá el diagnóstico y revisá README.md.')
    args = [engine, '--ignore-config', '--no-plugin-dirs', '--no-playlist',
            '--dump-single-json', '--skip-download', '--no-warnings']
    deno = executable('deno')
    if deno:
        args += ['--js-runtimes', 'deno:' + deno]
    return args + ['--', url]


def fetch_metadata(url):
    result = run_external(metadata_command(url), check=False, capture_output=True, text=True, timeout=60)
    if result.returncode:
        return {'webpage_url': validate_url(url), 'title': 'Unknown', 'metadata_error': result.stderr.strip()}
    try:
        info = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {'webpage_url': validate_url(url), 'title': 'Unknown', 'metadata_error': 'json inválido'}
    if isinstance(info, dict):
        return info
    return {'webpage_url': validate_url(url), 'title': 'Unknown', 'metadata_error': 'metadata inválida'}


def write_json(path, data):
    with Path(path).open('w', encoding='utf-8') as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write('\n')


def read_json_object(path):
    try:
        with Path(path).open('r', encoding='utf-8') as handle:
            data = json.load(handle)
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def initial_project_manifest(url, info, guess, existing=None):
    existing = dict(existing or {})
    now = datetime.now(timezone.utc).isoformat()
    webpage_url = info.get('webpage_url') or info.get('original_url') or validate_url(url)
    manifest = {
        'schema': 1,
        'app': 'oss',
        'kind': 'song-project',
        'created_at': existing.get('created_at') or now,
        'updated_at': now,
        'source': {
            **(existing.get('source') if isinstance(existing.get('source'), dict) else {}),
            'url': validate_url(url),
            'extractor': 'yt-dlp',
            'webpage_url': webpage_url,
            'id': info.get('id'),
        },
        'identity': {
            **(existing.get('identity') if isinstance(existing.get('identity'), dict) else {}),
            'artist': guess['artist'],
            'track': guess['track'],
            'artist_slug': guess['artist'],
            'track_slug': guess['track'],
            'confidence': guess['confidence'],
            'source': guess['source'],
        },
        'media': existing.get('media') if isinstance(existing.get('media'), list) else [],
        'stems': existing.get('stems') if isinstance(existing.get('stems'), list) else [],
        'analysis': existing.get('analysis') if isinstance(existing.get('analysis'), dict) else {},
        'lyrics': existing.get('lyrics') if isinstance(existing.get('lyrics'), dict) else {},
        'exports': existing.get('exports') if isinstance(existing.get('exports'), list) else [],
        'notes': existing.get('notes') if isinstance(existing.get('notes'), list) else [],
    }
    return manifest


MEDIA_EXTENSIONS = {
    '.aac', '.aiff', '.alac', '.ape', '.flac', '.m4a', '.mka', '.mp3', '.ogg', '.opus', '.wav', '.webm',
    '.avi', '.m4v', '.mkv', '.mov', '.mp4', '.mpeg', '.mpg'
}
AUDIO_EXTENSIONS = {'.aac', '.aiff', '.alac', '.ape', '.flac', '.m4a', '.mka', '.mp3', '.ogg', '.opus', '.wav', '.webm'}
VIDEO_EXTENSIONS = {'.avi', '.m4v', '.mkv', '.mov', '.mp4', '.mpeg', '.mpg'}


def media_kind(path):
    suffix = Path(path).suffix.lower()
    if suffix in VIDEO_EXTENSIONS:
        return 'video'
    if suffix in AUDIO_EXTENSIONS:
        return 'audio'
    return 'media'


def project_media_files(project_dir):
    project_dir = Path(project_dir)
    if not project_dir.is_dir():
        return []
    files = []
    for path in sorted(project_dir.iterdir()):
        if not path.is_file():
            continue
        if path.name in ('metadata.json', 'project.json'):
            continue
        if path.name.endswith(('.part', '.ytdl', '.tmp')):
            continue
        if path.suffix.lower() in MEDIA_EXTENSIONS:
            files.append(path)
    return files


def register_project_media(project_dir, profile=None, kind=None):
    project_dir = Path(project_dir)
    project_path = project_dir / 'project.json'
    manifest = read_json_object(project_path)
    if not manifest:
        return False
    existing_media = manifest.get('media') if isinstance(manifest.get('media'), list) else []
    by_path = {item.get('path'): item for item in existing_media if isinstance(item, dict) and item.get('path')}
    changed = False
    for path in project_media_files(project_dir):
        relative = path.relative_to(project_dir).as_posix()
        stat = path.stat()
        item = by_path.get(relative, {})
        updated = {
            **item,
            'path': relative,
            'kind': item.get('kind') or media_kind(path),
            'profile': item.get('profile') or profile,
            'role': item.get('role') or kind,
            'size': stat.st_size,
            'modified_at': datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
        }
        if updated != item:
            by_path[relative] = updated
            changed = True
    ordered = [by_path[key] for key in sorted(by_path)]
    if ordered != existing_media:
        manifest['media'] = ordered
        changed = True
    if changed:
        manifest['updated_at'] = datetime.now(timezone.utc).isoformat()
        write_json(project_path, manifest)
    return changed


def create_project(url, download_root=None, info=None):
    info = info or fetch_metadata(url)
    guess = guess_artist_track(info)
    root = Path(download_root or default_downloads()).expanduser().resolve()
    project_dir = root / guess['artist'] / guess['track']
    project_dir.mkdir(parents=True, exist_ok=True)
    metadata = {
        'source_url': validate_url(url),
        'webpage_url': info.get('webpage_url') or info.get('original_url') or validate_url(url),
        'title': info.get('title'),
        'artist_guess': guess['artist'],
        'track_guess': guess['track'],
        'artist_source': guess['source'],
        'confidence': guess['confidence'],
        'uploader': info.get('uploader') or info.get('channel'),
        'duration': info.get('duration'),
        'id': info.get('id'),
    }
    write_json(project_dir / 'metadata.json', metadata)
    project_path = project_dir / 'project.json'
    project_manifest = initial_project_manifest(url, info, guess, read_json_object(project_path))
    write_json(project_path, project_manifest)
    return project_dir


def output_template(label=None):
    suffix = f' - {label}' if label else ''
    return f'%(title).160B{suffix}.%(ext)s'


def command(url, profile='original', output=None, formats=False, playlist=False, cookies_file=None,
            cookies_from_browser=None, thumbnail_mode=None, label=None):
    url = validate_url(url)
    if profile not in PROFILES:
        raise ValueError('Perfil desconocido.')
    thumbnail_mode = thumbnail_mode or configured('thumbnail_mode', 'none')
    if thumbnail_mode not in THUMBNAIL_MODES:
        raise ValueError('Modo de thumbnail desconocido.')
    engine = executable('yt-dlp')
    if not engine:
        raise ValueError('Falta yt-dlp. Ejecutá el diagnóstico y revisá README.md.')
    args = [engine, '--ignore-config', '--no-plugin-dirs', '--no-playlist' if not playlist else '--yes-playlist',
            '--socket-timeout', '30', '--retries', '3', '--fragment-retries', '3']
    cookie_path = validate_cookie_file(cookies_file or configured('cookies_file'))
    browser_cookies = cookies_from_browser or configured('cookies_from_browser')
    if cookie_path and browser_cookies:
        raise ValueError('Elegí archivo de cookies o cookies del navegador, no ambos.')
    if cookie_path:
        args += ['--cookies', str(cookie_path)]
    elif browser_cookies:
        args += ['--cookies-from-browser', browser_cookies]
    deno = executable('deno')
    if deno:
        args += ['--js-runtimes', 'deno:' + deno]
    if formats:
        return args + ['--list-formats', '--', url]
    ffmpeg = executable('ffmpeg')
    if profile != 'original':
        if not ffmpeg or not executable('ffprobe'):
            raise ValueError('Este perfil necesita ffmpeg y ffprobe. Ejecutá: oss doctor')
        args += ['--ffmpeg-location', str(Path(ffmpeg).parent)]
    destination = Path(output or default_downloads()).expanduser().resolve()
    args += ['--paths', str(destination), '--output', output_template(label),
             '--windows-filenames', '--restrict-filenames', '--no-overwrites', '--continue', '--newline']
    if thumbnail_mode == 'none':
        args += ['--no-write-thumbnail', '--no-embed-thumbnail']
    elif thumbnail_mode == 'write':
        args += ['--write-thumbnail']
    else:
        args += ['--embed-thumbnail']
    if profile == 'original':
        args += ['--format', 'bestaudio']
    elif profile in ('wav', 'flac'):
        args += ['--format', 'bestaudio/best', '--extract-audio', '--audio-format', profile,
                 '--audio-quality', '0']
    elif profile == 'mp3':
        args += ['--format', 'bestaudio/best', '--extract-audio', '--audio-format', 'mp3',
                 '--audio-quality', '320K']
    elif profile == 'video':
        args += ['--format', 'bestvideo+bestaudio/best[vcodec!=none][acodec!=none]', '--merge-output-format', 'mkv']
    else:
        args += ['--format', 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4][vcodec!=none][acodec!=none]', '--merge-output-format', 'mp4']
    return args + ['--', url]


def doctor():
    missing = False
    for name in ('yt-dlp', 'ffmpeg', 'ffprobe', 'deno'):
        path = executable(name)
        if not path:
            print(f'FALTA {name}')
            missing = True
            continue
        try:
            result = run_external([path, '-version' if name in ('ffmpeg', 'ffprobe') else '--version'],
                                  capture_output=True, text=True, timeout=15)
            lines = (result.stdout or result.stderr).splitlines()
            print(f'{"OK" if result.returncode == 0 else "ERROR"} {name}: {lines[0] if lines else path}')
            missing |= result.returncode != 0
        except (OSError, subprocess.TimeoutExpired) as exc:
            print(f'ERROR {name}: {exc}')
            missing = True
    print('YouTube también requiere EJS compatible; doctor no comprueba acceso a sitios.')
    return int(missing)


def check_ytdlp_update():
    engine = executable('yt-dlp')
    if not engine:
        print('No encontré yt-dlp. Ejecutá doctor o reinstalá OSS.')
        return 1
    print('Verificando nueva versión de yt-dlp...')
    try:
        result = run_external([engine, '-U'], check=False, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f'No pude comprobar actualizaciones de yt-dlp ahora. Sigo con la versión instalada. ({exc})')
        return 1
    if result.stdout:
        print(result.stdout, end='')
    if result.stderr:
        print(result.stderr, end='', file=sys.stderr)
    if result.returncode:
        print('No pude actualizar yt-dlp ahora. Sigo con la versión instalada.')
    return 0


def choose_download_kind():
    print('\n¿Qué querés descargar?')
    print('1 Audio')
    print('2 Video')
    print('3 Ambos')
    choice = input('Opción [1]: ').strip() or '1'
    mapping = {'1': 'audio', '2': 'video', '3': 'both'}
    if choice not in mapping:
        raise ValueError('Opción inválida.')
    return mapping[choice]


def choose_profile(kind='audio'):
    profiles = FLOW_FORMATS[kind]
    if kind == 'both':
        print('\nFormato del audio separado:')
    else:
        print('\nFormato de salida:')
    for index, profile in enumerate(profiles, start=1):
        print(f'{index} {PROFILE_LABELS[profile]}')
    choice = input('Formato [1]: ').strip() or '1'
    if not choice.isdigit() or not 1 <= int(choice) <= len(profiles):
        raise ValueError('Formato inválido.')
    return profiles[int(choice) - 1]


def console_supports_unicode():
    encoding = getattr(sys.stdout, 'encoding', None) or ''
    return encoding.lower().replace('-', '') in ('utf8', 'utf')


def banner_text():
    if console_supports_unicode():
        return '\n╔══════════════════════════════════════╗\n║ OSS · Open Stem Separator           ║\n║ Núcleo de descarga · versión 0.1     ║\n╚══════════════════════════════════════╝'
    return '\n========================================\nOSS - Open Stem Separator\nNucleo de descarga - version 0.1\n========================================'


def menu():
    print(banner_text())
    check_ytdlp_update()
    print('')
    url = input('URL (o doctor/salir): ').strip()
    if url.lower() in ('0', 'salir', 'exit', 'quit'):
        return 0
    if url.lower() == 'doctor':
        return doctor()
    if not url:
        raise ValueError('Ingresá una URL.')
    kind = choose_download_kind()
    project_dir = create_project(url)
    print(f'Proyecto: {project_dir}')
    if kind == 'both':
        audio_profile = choose_profile('both')
        return run_many_tracked([
            {'url': url, 'profile': 'video', 'project_dir': project_dir, 'label': 'video', 'kind': 'both-video'},
            {'url': url, 'profile': audio_profile, 'project_dir': project_dir, 'label': 'audio', 'kind': 'both-audio'},
        ])
    profile = choose_profile(kind)
    return run_tracked(url, profile, project_dir)


def prepare_output(args):
    if '--paths' not in args:
        return
    destination = Path(args[args.index('--paths') + 1])
    try:
        destination.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryFile(dir=destination) as probe:
            probe.write(b'OSS write check')
            probe.flush()
    except OSError as exc:
        raise ValueError(f'No se puede escribir en {destination}. Elegí otra carpeta. ({exc})') from exc


def configure(downloads_dir, install_mode=None, thumbnail_mode=None):
    destination = Path(downloads_dir).expanduser().resolve()
    prepare_output(['oss', '--paths', str(destination)])
    values = {'downloads_dir': destination}
    if install_mode:
        values['install_mode'] = install_mode
    if thumbnail_mode:
        if thumbnail_mode not in THUMBNAIL_MODES:
            raise ValueError('Modo de thumbnail desconocido.')
        values['thumbnail_mode'] = thumbnail_mode
    save_config(values)
    print(f'Configuración guardada en {active_config_path()}')
    print(f'Descargas: {destination}')
    return 0


def run(args):
    prepare_output(args)
    result = run_process(args)
    if result.returncode and should_retry_with_cookies(args, result):
        for browser in detected_browsers():
            retry_args = with_browser_cookies(args, browser)
            print(f'OSS: reintentando con cookies de {browser}...', file=sys.stderr)
            result = run_process(retry_args)
            if result.returncode == 0 or not cookie_recovery_failed(result):
                break
    if result.returncode:
        print('No se completó la operación. Revisá el mensaje de yt-dlp; podés reintentar para continuar la descarga.', file=sys.stderr)
    return result.returncode if result.returncode >= 0 else 1


def run_all(commands):
    for args in commands:
        code = run(args)
        if code:
            return code
    return 0


def run_process(args):
    result = run_external(args, check=False, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout, end='')
    if result.stderr:
        print(result.stderr, end='', file=sys.stderr)
    return result


def output_text(result):
    return ((getattr(result, 'stdout', None) or '') + '\n' + (getattr(result, 'stderr', None) or '')).lower()


def cookie_recovery_failed(result):
    text = output_text(result)
    return any(fragment in text for fragment in ('could not copy chrome cookie database', 'failed to decrypt', 'cookie'))


def should_retry_with_cookies(args, result):
    if '--cookies' in args or '--cookies-from-browser' in args or '--list-formats' in args:
        return False
    text = output_text(result)
    markers = (
        'sign in to confirm',
        'confirm you’re not a bot',
        "confirm you're not a bot",
        'cookies',
        'cookie',
        'login',
        'logged in',
        'private video',
        'members-only',
        'not available in your country',
        'http error 403',
        '403 forbidden',
    )
    return any(marker in text for marker in markers)


def with_browser_cookies(args, browser):
    insertion = args.index('--') if '--' in args else len(args)
    return args[:insertion] + ['--cookies-from-browser', browser] + args[insertion:]


def parse_global_options(argv):
    argv = list(argv)
    config_path = None
    cleaned = []
    index = 0
    while index < len(argv):
        item = argv[index]
        if item == '--config':
            if index + 1 >= len(argv):
                raise ValueError('--config necesita una ruta.')
            config_path = argv[index + 1]
            index += 2
            continue
        if item.startswith('--config='):
            config_path = item.split('=', 1)[1]
            index += 1
            continue
        cleaned.append(item)
        index += 1
    return cleaned, config_path


def main(argv=None):
    try:
        argv, config_path = parse_global_options(sys.argv[1:] if argv is None else argv)
        if config_path:
            set_config_path(config_path)
    except ValueError as exc:
        print(f'OSS: {exc}', file=sys.stderr)
        return 1
    if argv and argv[0] in PROFILES and len(argv) >= 2:
        profile = argv[0]
        url = argv[1]
        rest = argv[2:]
        try:
            project_dir = create_project(url)
            args = command(url, profile, output=project_dir)
            if '--dry-run' in rest:
                print(json.dumps(args, ensure_ascii=False, indent=2))
                return 0
            print(f'Proyecto: {project_dir}')
            return run_tracked(url, profile, project_dir, kind='shortcut')
        except (ValueError, OSError) as exc:
            print(f'OSS: {exc}', file=sys.stderr)
            return 1
    elif argv and argv[0] == 'both' and len(argv) >= 2:
        url = argv[1]
        rest = argv[2:]
        try:
            project_dir = create_project(url)
            commands = [command(url, 'video', output=project_dir, label='video'),
                        command(url, 'original', output=project_dir, label='audio')]
            if '--dry-run' in rest:
                print(json.dumps(commands, ensure_ascii=False, indent=2))
                return 0
            print(f'Proyecto: {project_dir}')
            return run_many_tracked([
                {'url': url, 'profile': 'video', 'project_dir': project_dir, 'label': 'video', 'kind': 'both-video'},
                {'url': url, 'profile': 'original', 'project_dir': project_dir, 'label': 'audio', 'kind': 'both-audio'},
            ])
        except (ValueError, OSError) as exc:
            print(f'OSS: {exc}', file=sys.stderr)
            return 1
    elif argv and argv[0] not in ('doctor', 'configure', 'config', 'last', 'open', 'history', 'download', 'formats', '-h', '--help') and is_url(argv[0]):
        argv = ['download'] + argv
    parser = argparse.ArgumentParser(description='OSS — Open Stem Separator: núcleo de descarga')
    parser.add_argument('--config', help='Ruta de configuración alternativa para pruebas o instalaciones aisladas')
    sub = parser.add_subparsers(dest='action')
    sub.add_parser('doctor', help='Comprobar motores')
    sub.add_parser('config', help='Mostrar configuración activa')
    sub.add_parser('last', help='Mostrar última descarga registrada')
    project_parser = sub.add_parser('project', help='Mostrar resumen de un proyecto OSS')
    project_parser.add_argument('target', nargs='?', default='last', help='last o una ruta de proyecto')
    open_parser = sub.add_parser('open', help='Abrir carpeta de descargas o último proyecto')
    open_parser.add_argument('target', nargs='?', default='last', help='last, downloads o una ruta')
    history_parser = sub.add_parser('history', help='Mostrar historial local de descargas')
    history_parser.add_argument('--limit', type=int, default=20)
    history_parser.add_argument('--json', action='store_true', help='Mostrar JSON Lines para scripts')
    config_parser = sub.add_parser('configure', help='Guardar carpeta de descargas por usuario')
    config_parser.add_argument('--downloads-dir', type=Path, required=True)
    config_parser.add_argument('--install-mode', choices=('offline', 'online'))
    config_parser.add_argument('--thumbnails', choices=THUMBNAIL_MODES, help='none, write o embed')
    for name in ('download', 'formats'):
        p = sub.add_parser(name)
        p.add_argument('url')
        p.add_argument('--profile', choices=PROFILES, default='original')
        p.add_argument('--output', type=Path)
        p.add_argument('--playlist', action='store_true', help='Habilitar playlists explícitamente')
        p.add_argument('--thumbnails', choices=THUMBNAIL_MODES, help='none, write o embed')
        p.add_argument('--dry-run', action='store_true', help='Mostrar argumentos sin descargar')
    ns = parser.parse_args(argv)
    if getattr(ns, 'config', None):
        set_config_path(ns.config)
    try:
        if ns.action is None:
            if not sys.stdin.isatty():
                parser.print_help()
                return 2
            return menu()
        if ns.action == 'doctor':
            return doctor()
        if ns.action == 'config':
            return print_config()
        if ns.action == 'last':
            return print_last()
        if ns.action == 'project':
            return print_project(ns.target)
        if ns.action == 'open':
            return open_target(ns.target)
        if ns.action == 'history':
            return print_history(ns.limit, ns.json)
        if ns.action == 'configure':
            return configure(ns.downloads_dir, ns.install_mode, ns.thumbnails)
        args = command(ns.url, ns.profile, ns.output, ns.action == 'formats', ns.playlist,
                       thumbnail_mode=ns.thumbnails)
        if ns.dry_run:
            print(json.dumps(args, ensure_ascii=False, indent=2))
            return 0
        code = run(args)
        if ns.action == 'download':
            if code == 0 and ns.output and (Path(ns.output) / 'project.json').is_file():
                register_project_media(ns.output, ns.profile, 'download')
            append_history(history_entry(ns.url, ns.profile, ns.output, 'ok' if code == 0 else 'error', code, 'download'))
        return code
    except (ValueError, OSError) as exc:
        print(f'OSS: {exc}', file=sys.stderr)
        return 1
    except (KeyboardInterrupt, EOFError):
        print('\nCancelado.', file=sys.stderr)
        return 130


if __name__ == '__main__':
    sys.exit(main())
