#!/usr/bin/env python3
from __future__ import annotations

import argparse
from array import array
import json
from pathlib import Path
import sys

TOOL_DIR = Path(__file__).resolve().parent
if str(TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(TOOL_DIR))

import measure_run  # noqa: E402


def q(value: str) -> str:
    return '"' + value.replace('\\', '\\\\').replace('"', '\\"') + '"'


def read_json(path: Path) -> dict:
    with path.open('r', encoding='utf-8') as handle:
        return json.load(handle)


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8') as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write('\n')


def decode_run_outputs(run_dir: Path, measurement: dict) -> tuple[array, int, int]:
    sample_rate = int(measurement['input']['sample_rate'])
    channels = int(measurement['input']['channels'])
    original = measure_run.decode_f32(Path(measurement['input']['path']), sample_rate, channels)
    final_sum = array('f', [0.0]) * len(original)
    for output in measurement['outputs']:
        if not output.get('include_in_final_sum'):
            continue
        samples = measure_run.decode_f32(Path(output['path']), sample_rate, channels)
        n = min(len(original), len(samples))
        for i in range(n):
            final_sum[i] += samples[i]
    return final_sum, sample_rate, channels


def ensure_measurement(run_dir: Path) -> dict:
    measurement_path = run_dir / 'measurement.json'
    if measurement_path.is_file():
        return read_json(measurement_path)
    measurement = measure_run.measure_run(run_dir, run_dir / 'reconstruction_residual.wav')
    write_json(measurement_path, measurement)
    (run_dir / 'MEASUREMENT.md').write_text(measure_run.markdown(measurement), encoding='utf-8')
    return measurement


def render_track(name: str, wav: Path, position: float = 0.0, color: int = 0) -> str:
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
      POSITION {position}
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


def write_reaper_comparison(summary: dict, output: Path) -> None:
    lines = [
        '<REAPER_PROJECT 0.1 "7.x" 1700000000',
        '  RIPPLE 0',
        '  AUTOXFADE 1',
        '  PANMODE 3',
        '  CURSOR 0',
        '  ZOOM 100 0 0',
        '  <NOTES 0 2',
        '    | OSS separation comparison',
        '    | Solo Original + one reconstruction, or solo one residual to hear what remains.',
        '  >',
    ]
    original = Path(summary['input'])
    lines.append(render_track('00 original', original, color=16777215))
    for index, run in enumerate(summary['runs'], start=1):
        label = run['label']
        lines.append(render_track(f'{index:02d} {label} · reconstruction', Path(run['reconstruction_wav']), color=65280))
        lines.append(render_track(f'{index:02d} {label} · residual original-minus-reconstruction', Path(run['residual_wav']), color=16724787))
    lines.append('>')
    output.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def markdown(summary: dict) -> str:
    lines = [
        '# OSS separation comparison',
        '',
        f"- input: `{summary['input']}`",
        f"- REAPER project: `{summary['reaper_project']}`",
        '',
        '## Technical comparison',
        '',
        '| Run | Residual dB vs original | Residual peak | Outputs summed | Reconstruction WAV | Residual WAV |',
        '| --- | ---: | ---: | ---: | --- | --- |',
    ]
    for run in summary['runs']:
        residual = run['measurement']['reconstruction_residual']
        db = residual.get('rms_db_vs_original')
        db_text = '' if db is None else f'{db:.2f}'
        lines.append(
            f"| {run['label']} | {db_text} | {residual.get('peak', 0):.6f} | "
            f"{run['measurement']['final_sum_output_count']} | `{run['reconstruction_wav']}` | `{run['residual_wav']}` |"
        )
    lines += [
        '',
        '## How to listen',
        '',
        '1. Open the `.rpp` in REAPER.',
        '2. Solo `00 original` and one reconstruction to compare tonal changes.',
        '3. Solo each residual track. A lower/quieter residual means the summed stems reconstruct the original more closely.',
        '4. Residual is not automatically “bad”; listen for musical content that should not be missing, phasing, pumping, hiss, or transients.',
        '',
    ]
    return '\n'.join(lines)


def compare_runs(run_dirs: list[Path], out_dir: Path, labels: list[str] | None = None) -> Path:
    if len(run_dirs) < 2:
        raise ValueError('compare requires at least two run directories')
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = {'schema': 1, 'kind': 'oss-separation-run-comparison', 'runs': []}
    input_path = None
    for index, run_dir in enumerate(run_dirs):
        run_dir = run_dir.expanduser().resolve()
        label = labels[index] if labels and index < len(labels) else run_dir.name
        measurement = ensure_measurement(run_dir)
        current_input = measurement['input']['path']
        if input_path is None:
            input_path = current_input
        elif current_input != input_path:
            raise ValueError('all runs must use the same input audio')
        reconstruction, sample_rate, channels = decode_run_outputs(run_dir, measurement)
        reconstruction_wav = out_dir / f'{index + 1:02d}-{label}-reconstruction.wav'
        residual_wav = Path(measurement['reconstruction_residual'].get('wav') or run_dir / 'reconstruction_residual.wav')
        measure_run.write_f32_wav(reconstruction_wav, reconstruction, sample_rate, channels)
        summary['runs'].append({
            'label': label,
            'run_dir': str(run_dir),
            'measurement': measurement,
            'reconstruction_wav': str(reconstruction_wav),
            'residual_wav': str(residual_wav),
        })
    summary['input'] = input_path
    summary['reaper_project'] = str(out_dir / 'comparison.rpp')
    write_json(out_dir / 'comparison.json', summary)
    (out_dir / 'COMPARISON.md').write_text(markdown(summary), encoding='utf-8')
    write_reaper_comparison(summary, out_dir / 'comparison.rpp')
    return out_dir


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Compare OSS separation runs with reconstruction and residual audio')
    parser.add_argument('run_dirs', nargs='+', type=Path, help='Run directories to compare')
    parser.add_argument('--out', type=Path, required=True, help='Output comparison directory')
    parser.add_argument('--label', action='append', help='Optional label, repeat in run order')
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(argv)
        out = compare_runs(args.run_dirs, args.out.expanduser().resolve(), args.label)
        print(out / 'COMPARISON.md')
        print(out / 'comparison.rpp')
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f'OSS compare runs: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
