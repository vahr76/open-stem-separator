#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT / 'labs' / 'separation') not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / 'labs' / 'separation'))

import separate  # noqa: E402


def read_json(path: Path) -> dict:
    with path.open('r', encoding='utf-8') as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f'{path} must contain a JSON object')
    return data


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8') as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write('\n')


def resolve_path(path: str | Path, base: Path) -> Path:
    raw = Path(path).expanduser()
    if raw.is_absolute():
        return raw
    return (base / raw).resolve()


def make_clip(item: dict, clip_path: Path, seconds: int, sample_rate: int, channels: int, dry_run: bool) -> dict:
    source = Path(item['source']).expanduser()
    if not source.is_file():
        raise ValueError(f"source not found for {item.get('id')}: {source}")
    clip_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        'ffmpeg', '-y', '-hide_banner', '-loglevel', 'error',
        '-ss', str(item.get('start', 0)),
        '-t', str(item.get('seconds', seconds)),
        '-i', str(source),
        '-ar', str(item.get('sample_rate', sample_rate)),
        '-ac', str(item.get('channels', channels)),
        str(clip_path),
    ]
    if dry_run:
        clip_path.write_bytes(b'oss benchmark dry-run placeholder\n')
        return {'path': str(clip_path), 'command': command, 'status': 'dry-run', 'size': clip_path.stat().st_size}
    started = time.monotonic()
    completed = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    elapsed = round(time.monotonic() - started, 3)
    if completed.returncode != 0:
        raise ValueError(f"ffmpeg failed for {item.get('id')}: {completed.stderr.strip()}")
    return {
        'path': str(clip_path),
        'command': command,
        'status': 'ok',
        'elapsed_seconds': elapsed,
        'size': clip_path.stat().st_size,
    }


def markdown_report(summary: dict) -> str:
    lines = [
        f"# OSS separation benchmark — {summary['name']}",
        '',
        summary.get('description') or '',
        '',
        f"- status: `{summary['status']}`",
        f"- dry run: `{summary['dry_run']}`",
        f"- output root: `{summary['out_root']}`",
        '',
        '## Results',
        '',
        '| Item | Config | Status | Seconds | Outputs | Missing | Run |',
        '| --- | --- | --- | ---: | ---: | --- | --- |',
    ]
    for result in summary['results']:
        run = result.get('run_dir', '')
        missing = ', '.join(result.get('missing_outputs') or [])
        lines.append(
            f"| {result['item_label']} | {result['config_name']} | {result['status']} | "
            f"{result.get('elapsed_seconds', '')} | {result.get('output_count', '')} | {missing} | `{run}` |"
        )
    lines += [
        '',
        '## Listening notes',
        '',
        'Fill this manually while listening to stems. Use 1-5 scores only as a quick memory aid; notes matter more than numbers.',
        '',
        '| Item | Config | Bass clarity | Drum transients | Vocal bleed | Artifacts/noise | Notes |',
        '| --- | --- | --- | --- | --- | --- | --- |',
    ]
    for result in summary['results']:
        lines.append(f"| {result['item_label']} | {result['config_name']} |  |  |  |  |  |")
    lines.append('')
    return '\n'.join(lines)


def run_benchmark(benchmark_path: Path, out_root: Path, dry_run: bool = False, max_items: int | None = None) -> Path:
    benchmark_path = benchmark_path.resolve()
    config = read_json(benchmark_path)
    if config.get('schema') != 1:
        raise ValueError('Unsupported benchmark schema')
    name = config.get('name') or benchmark_path.stem
    run_root = out_root / (separate.utc_now().replace(':', '').replace('+0000', 'Z') + '-' + separate.safe_slug(name))
    clips_root = run_root / 'clips'
    runs_root = run_root / 'runs'
    items = config.get('items') or []
    if max_items is not None:
        items = items[:max_items]
    if not items:
        raise ValueError('Benchmark requires at least one item')
    configs = [resolve_path(path, REPO_ROOT) for path in config.get('configs') or []]
    if not configs:
        raise ValueError('Benchmark requires at least one separation config')

    summary = {
        'schema': 1,
        'kind': 'oss-separation-benchmark-run',
        'name': name,
        'description': config.get('description'),
        'benchmark_path': str(benchmark_path),
        'out_root': str(run_root),
        'dry_run': dry_run,
        'status': 'running',
        'results': [],
    }
    write_json(run_root / 'benchmark.json', summary)

    try:
        for item in items:
            item_id = separate.safe_slug(item.get('id') or item.get('label') or 'item')
            clip_path = clips_root / f'{item_id}.wav'
            clip_info = make_clip(
                item,
                clip_path,
                int(config.get('clip_seconds', 20)),
                int(config.get('sample_rate', 44100)),
                int(config.get('channels', 2)),
                dry_run,
            )
            for sep_config in configs:
                config_name = read_json(sep_config).get('name') or sep_config.stem
                result = {
                    'item_id': item_id,
                    'item_label': item.get('label') or item_id,
                    'item_notes': item.get('notes'),
                    'clip': clip_info,
                    'config_path': str(sep_config),
                    'config_name': config_name,
                    'status': 'dry-run' if dry_run else 'running',
                }
                started = time.monotonic()
                try:
                    if dry_run:
                        run_dir = separate.run_lab(sep_config, clip_path, runs_root / item_id, dry_run=True)
                    else:
                        run_dir = separate.run_lab(sep_config, clip_path, runs_root / item_id, dry_run=False)
                    elapsed = round(time.monotonic() - started, 3)
                    manifest = read_json(run_dir / 'manifest.json')
                    missing = []
                    output_count = 0
                    for stage in manifest.get('stages', []):
                        missing.extend(stage.get('missing_outputs') or [])
                        output_count += len(stage.get('outputs') or [])
                    result.update({
                        'status': manifest.get('status'),
                        'run_dir': str(run_dir),
                        'elapsed_seconds': elapsed,
                        'output_count': output_count,
                        'missing_outputs': missing,
                    })
                except Exception as exc:  # keep benchmark report useful across failures
                    result.update({'status': 'error', 'error': str(exc), 'elapsed_seconds': round(time.monotonic() - started, 3)})
                summary['results'].append(result)
                write_json(run_root / 'benchmark.json', summary)
        summary['status'] = 'ok' if all(result['status'] in ('ok', 'dry-run') for result in summary['results']) else 'error'
    finally:
        write_json(run_root / 'benchmark.json', summary)
        (run_root / 'REPORT.md').write_text(markdown_report(summary), encoding='utf-8')
    return run_root


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Run OSS separation benchmark configs against local excerpts')
    parser.add_argument('--benchmark', type=Path, required=True, help='Benchmark JSON file')
    parser.add_argument('--out', type=Path, required=True, help='Output root')
    parser.add_argument('--dry-run', action='store_true', help='Build report/manifests without running ffmpeg or engines')
    parser.add_argument('--max-items', type=int, help='Limit number of benchmark items')
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(argv)
        run_root = run_benchmark(args.benchmark, args.out, args.dry_run, args.max_items)
        print(f'Benchmark: {run_root}')
        print(f'Report: {run_root / "REPORT.md"}')
        return 0
    except (OSError, ValueError) as exc:
        print(f'OSS separation benchmark: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
