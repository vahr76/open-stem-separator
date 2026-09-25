#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


def q(value: str) -> str:
    return '"' + value.replace('\\', '\\\\').replace('"', '\\"') + '"'


def load_manifest(run_dir: Path) -> dict:
    manifest_path = run_dir / 'manifest.json'
    if not manifest_path.is_file():
        raise ValueError(f'manifest not found: {manifest_path}')
    with manifest_path.open('r', encoding='utf-8') as handle:
        return json.load(handle)


def stem_role(path: Path) -> str:
    name = path.stem.lower()
    if name == 'vocals':
        return 'vocals'
    if name == 'no_vocals':
        return 'no_vocals'
    if name in {'bass', 'drums', 'other', 'guitar', 'piano'}:
        return name
    return name


def track_name(stage_id: str, wav: Path) -> str:
    role = stem_role(wav)
    if stage_id == 'stage-02-instrumental-stems' and role == 'vocals':
        role = 'vocals_residual'
    return f'{stage_id} · {role}'


def color_for_role(role: str) -> int:
    colors = {
        'bass': 3358730,
        'drums': 255,
        'vocals': 16724787,
        'vocals_residual': 16753920,
        'no_vocals': 8421504,
        'other': 65280,
        'guitar': 16744448,
        'piano': 10066176,
    }
    return colors.get(role, 0)


def render_track(name: str, wav: Path) -> str:
    role = name.split(' · ')[-1]
    color = color_for_role(role)
    return f'''  <TRACK
    NAME {q(name)}
    PEAKCOL {color}
    BEAT -1
    AUTOMODE 0
    VOLPAN 1 0 -1 -1 1
    MUTESOLO 0 0 0
    IPHASE 0
    PLAYOFFS 0 1
    ISBUS 0 0
    BUSCOMP 0 0 0 0 0
    SHOWINMIX 1 0.6667 0.5 1 0.5 0 -1 0
    FREEMODE 0
    SEL 0
    REC 0 0 0 0 0 0 0 0
    VU 2
    TRACKHEIGHT 0 0 0 0 0 0
    INQ 0 0 0 0.5 100 0 0 100
    NCHAN 2
    FX 1
    TRACKID {{{name}}}
    PERF 0
    MIDIOUT -1
    MAINSEND 1 0
    <ITEM
      POSITION 0
      SNAPOFFS 0
      LENGTH 20
      LOOP 0
      ALLTAKES 0
      FADEIN 1 0 0 1 0 0 0
      FADEOUT 1 0 0 1 0 0 0
      MUTE 0 0
      SEL 0
      IGUID {{{name}-item}}
      IID 1
      NAME {q(wav.name)}
      VOLPAN 1 0 1 -1
      SOFFS 0
      PLAYRATE 1 1 0 -1 0 0.0025
      CHANMODE 0
      GUID {{{name}-take}}
      <SOURCE WAVE
        FILE {q(str(wav))}
      >
    >
  >'''


def collect_wavs(run_dir: Path, manifest: dict) -> list[tuple[str, Path]]:
    wavs: list[tuple[str, Path]] = []
    for stage in manifest.get('stages', []):
        stage_id = stage.get('id') or 'stage'
        stage_dir = run_dir / (stage.get('path') or stage_id)
        for output in stage.get('outputs') or []:
            path = stage_dir / output.get('path', '')
            if path.suffix.lower() == '.wav' and path.is_file():
                wavs.append((track_name(stage_id, path), path.resolve()))
    return wavs


def write_reaper_project(run_dir: Path, output: Path) -> Path:
    manifest = load_manifest(run_dir)
    wavs = collect_wavs(run_dir, manifest)
    if not wavs:
        raise ValueError(f'no wav outputs found in {run_dir}')
    title = manifest.get('config', {}).get('name') or run_dir.name
    lines = [
        '<REAPER_PROJECT 0.1 "7.x" 1700000000',
        f'  RIPPLE 0',
        f'  GROUPOVERRIDE 0 0 0',
        f'  AUTOXFADE 1',
        f'  ENVATTACH 1',
        f'  POOLEDENVATTACH 0',
        f'  MIXERUIFLAGS 11 48',
        f'  PEAKGAIN 1',
        f'  FEEDBACK 0',
        f'  PANLAW 1',
        f'  PROJOFFS 0 0 0',
        f'  MAXPROJLEN 0 600',
        f'  GRID 3199 8 1 8 1 0 0 0',
        f'  TIMEMODE 1 5 -1 30 0 0 -1',
        f'  VIDEO_CONFIG 0 0 256',
        f'  PANMODE 3',
        f'  CURSOR 0',
        f'  ZOOM 100 0 0',
        f'  VZOOMEX 6 0',
        f'  USE_REC_CFG 0',
        f'  RECMODE 1',
        f'  SMPTESYNC 0 30 100 40 1000 300 0 0 1 0 0',
        f'  LOOP 0',
        f'  LOOPGRAN 0 4',
        f'  RECORD_PATH "" ""',
        f'  <NOTES 0 2',
        f'    | OSS separation lab: {title}',
        f'    | Source run: {run_dir}',
        f'  >',
    ]
    lines.extend(render_track(name, wav) for name, wav in wavs)
    lines.append('>')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return output


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Create a basic REAPER project from an OSS separation lab run')
    parser.add_argument('run_dir', type=Path, help='Lab run directory containing manifest.json')
    parser.add_argument('--output', type=Path, help='Output .rpp file')
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(argv)
        run_dir = args.run_dir.expanduser().resolve()
        output = args.output.expanduser().resolve() if args.output else run_dir / f'{run_dir.name}.rpp'
        path = write_reaper_project(run_dir, output)
        print(path)
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f'OSS REAPER export: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
