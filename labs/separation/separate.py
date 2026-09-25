#!/usr/bin/env python3
"""OSS source-separation laboratory runner.

This script is not part of the stable ytd user flow. It creates reproducible lab
runs for testing separation engines and pipelines.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from datetime import datetime, timezone
import time


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_slug(value: str) -> str:
    cleaned = ''.join(ch if ch.isalnum() or ch in ('-', '_', '.') else '-' for ch in str(value).strip())
    while '--' in cleaned:
        cleaned = cleaned.replace('--', '-')
    return cleaned.strip('-._') or 'run'


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


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


def make_run_dir(out_root: Path, config_name: str) -> Path:
    run_id = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S') + '-' + safe_slug(config_name)
    run_dir = out_root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def engine_python() -> str:
    override = os.environ.get('OSS_LAB_PYTHON')
    if override:
        return override
    if getattr(sys, 'frozen', False):
        python = shutil.which('python3') or shutil.which('python')
        if python:
            return python
        raise ValueError('Demucs requires Python. Set OSS_LAB_PYTHON to a Python executable with demucs installed.')
    return sys.executable



def engine_subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
    for key in list(env):
        if key.startswith('_PYI_'):
            env.pop(key, None)
    if env.get('LD_LIBRARY_PATH', '').startswith('/tmp/_MEI'):
        env.pop('LD_LIBRARY_PATH', None)
    original_ld_path = env.pop('LD_LIBRARY_PATH_ORIG', None)
    if original_ld_path:
        env['LD_LIBRARY_PATH'] = original_ld_path
    env.pop('PYTHONHOME', None)
    return env

def detect_torch_device(python_executable: str) -> str:
    override = os.environ.get('OSS_LAB_DEVICE')
    if override:
        normalized = override.strip().lower()
        if normalized in {'cuda', 'cpu', 'mps'} or normalized.startswith('cuda:'):
            return normalized
        if normalized != 'auto':
            raise ValueError('OSS_LAB_DEVICE must be auto, cuda, cuda:N, cpu or mps')

    probe = subprocess.run(
        [
            python_executable,
            '-c',
            'import torch; print("cuda" if torch.cuda.is_available() else "cpu")',
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
        env=engine_subprocess_env(),
    )
    if probe.returncode == 0:
        detected = (probe.stdout or '').strip().splitlines()[-1:]
        if detected and detected[0] in {'cuda', 'cpu'}:
            return detected[0]
    return 'cpu'


def stage_device(stage: dict, python_executable: str) -> str | None:
    requested = stage.get('device') or 'auto'
    if requested == 'auto':
        return detect_torch_device(python_executable)
    return str(requested)


def demucs_command(stage: dict, input_path: Path, stage_dir: Path) -> tuple[list[str], str | None]:
    model = stage.get('model')
    if not model:
        raise ValueError('Demucs stage requires model')
    python_executable = engine_python()
    command = [python_executable, '-m', 'demucs', '-n', model, '-o', str(stage_dir / 'stems')]
    device = stage_device(stage, python_executable)
    if device:
        command += ['-d', device]
    two_stems = stage.get('two_stems')
    if two_stems:
        command += ['--two-stems', str(two_stems)]
    for option in ('segment', 'shifts', 'overlap'):
        value = stage.get(option)
        if value is not None:
            command += [f'--{option}', str(value)]
    if stage.get('float32'):
        command.append('--float32')
    command.append(str(input_path))
    return command, device


def resolve_stage_input(stage: dict, original_input: Path, run_dir: Path, dry_run: bool) -> Path:
    input_spec = stage.get('input') or 'original'
    if input_spec == 'original':
        return original_input
    if not isinstance(input_spec, str) or not input_spec.startswith('stage:'):
        raise ValueError(f'Unsupported stage input: {input_spec}')
    parts = input_spec.split(':', 2)
    if len(parts) != 3 or not parts[1] or not parts[2]:
        raise ValueError(f'Invalid stage input reference: {input_spec}')
    stage_id = safe_slug(parts[1])
    pattern = parts[2]
    source_dir = run_dir / stage_id
    matches = sorted(path for path in source_dir.glob(pattern) if path.is_file())
    if matches:
        return matches[0]
    if dry_run:
        return source_dir / pattern
    raise ValueError(f'Stage input not found: {input_spec}')


def run_stage(stage: dict, input_path: Path, run_dir: Path, dry_run: bool = False) -> dict:
    stage_id = safe_slug(stage.get('id') or f"stage-{stage.get('engine', 'unknown')}")
    stage_dir = run_dir / stage_id
    stage_dir.mkdir(parents=True, exist_ok=False)
    started_at = utc_now()
    started_monotonic = time.monotonic()
    engine = stage.get('engine')
    status = 'dry-run' if dry_run else 'ok'
    command: list[str]
    effective_device: str | None = None
    stdout = ''
    stderr = ''
    returncode = 0

    if engine == 'demucs':
        command, effective_device = demucs_command(stage, input_path, stage_dir)
    else:
        raise ValueError(f'Unsupported engine: {engine}')

    if not dry_run:
        completed = subprocess.run(
            command,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            env=engine_subprocess_env(),
        )
        stdout = completed.stdout or ''
        stderr = completed.stderr or ''
        returncode = completed.returncode
        status = 'ok' if returncode == 0 else 'error'
        if stdout:
            (stage_dir / 'stdout.log').write_text(stdout, encoding='utf-8')
        if stderr:
            (stage_dir / 'stderr.log').write_text(stderr, encoding='utf-8')

    finished_at = utc_now()
    elapsed_seconds = round(time.monotonic() - started_monotonic, 3)
    outputs = []
    stems_dir = stage_dir / 'stems'
    if stems_dir.exists():
        for path in sorted(stems_dir.rglob('*')):
            if path.is_file():
                outputs.append({
                    'path': str(path.relative_to(stage_dir)),
                    'size': path.stat().st_size,
                    'sha256': sha256(path),
                })

    expected_stems = stage.get('expected_stems') or stage.get('outputs') or []
    present_stems = {Path(output['path']).stem for output in outputs}
    missing_outputs = [] if dry_run else sorted(stem for stem in expected_stems if stem not in present_stems)
    if not dry_run and returncode == 0 and missing_outputs:
        status = 'error'

    stage_manifest = {
        'schema': 1,
        'id': stage_id,
        'engine': engine,
        'model': stage.get('model'),
        'role': stage.get('role'),
        'input': str(input_path),
        'command': command,
        'requested_device': stage.get('device') or 'auto',
        'effective_device': effective_device,
        'dry_run': dry_run,
        'status': status,
        'returncode': returncode,
        'started_at': started_at,
        'finished_at': finished_at,
        'elapsed_seconds': elapsed_seconds,
        'expected_stems': expected_stems,
        'missing_outputs': missing_outputs,
        'outputs': outputs,
    }
    write_json(stage_dir / 'stage.json', stage_manifest)
    return {
        'id': stage_id,
        'engine': engine,
        'model': stage.get('model'),
        'role': stage.get('role'),
        'status': status,
        'returncode': returncode,
        'path': str(stage_dir.relative_to(run_dir)),
        'requested_device': stage.get('device') or 'auto',
        'effective_device': effective_device,
        'elapsed_seconds': elapsed_seconds,
        'expected_stems': expected_stems,
        'missing_outputs': missing_outputs,
        'outputs': outputs,
    }


def run_lab(config_path: Path, input_path: Path, out_root: Path, dry_run: bool = False) -> Path:
    config = read_json(config_path)
    if config.get('schema') != 1:
        raise ValueError('Unsupported config schema')
    if not input_path.is_file():
        raise ValueError(f'Input file not found: {input_path}')
    stages = config.get('stages')
    if not isinstance(stages, list) or not stages:
        raise ValueError('Config requires at least one stage')

    run_dir = make_run_dir(out_root, config.get('name') or config_path.stem)
    manifest = {
        'schema': 1,
        'kind': 'oss-separation-lab-run',
        'config': {
            'path': str(config_path),
            'name': config.get('name'),
            'mode': config.get('mode'),
            'description': config.get('description'),
        },
        'input': {
            'path': str(input_path),
            'size': input_path.stat().st_size,
            'sha256': sha256(input_path),
        },
        'dry_run': dry_run,
        'started_at': utc_now(),
        'stages': [],
    }
    write_json(run_dir / 'manifest.json', manifest)

    completed = False
    try:
        for stage in stages:
            current_input = resolve_stage_input(stage, input_path, run_dir, dry_run)
            stage_result = run_stage(stage, current_input, run_dir, dry_run)
            manifest['stages'].append(stage_result)
            write_json(run_dir / 'manifest.json', manifest)
            if stage_result['returncode'] or stage_result.get('missing_outputs'):
                break
        completed = True
    finally:
        manifest['finished_at'] = utc_now()
        manifest['status'] = 'ok' if completed and all(stage.get('returncode') == 0 for stage in manifest['stages']) else 'error'
        write_json(run_dir / 'manifest.json', manifest)
    return run_dir


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='OSS separation laboratory runner')
    parser.add_argument('--config', type=Path, required=True, help='JSON lab config')
    parser.add_argument('--input', type=Path, required=True, help='Input audio file')
    parser.add_argument('--out', type=Path, required=True, help='Output root for lab runs')
    parser.add_argument('--dry-run', action='store_true', help='Write manifests without executing the engine')
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(argv)
        run_dir = run_lab(args.config.expanduser().resolve(), args.input.expanduser().resolve(), args.out.expanduser().resolve(), args.dry_run)
        print(f'Run: {run_dir}')
        print(f'Manifest: {run_dir / "manifest.json"}')
        return 0
    except (OSError, ValueError) as exc:
        print(f'OSS separation lab: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
