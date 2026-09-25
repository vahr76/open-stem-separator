#!/usr/bin/env python3
from __future__ import annotations

import argparse
from array import array
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import wave


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


def ffprobe(path: Path) -> dict:
    command = [
        'ffprobe', '-v', 'error', '-select_streams', 'a:0',
        '-show_entries', 'stream=sample_rate,channels,duration',
        '-of', 'json', str(path),
    ]
    completed = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if completed.returncode != 0:
        raise ValueError(f'ffprobe failed for {path}: {completed.stderr.strip()}')
    data = json.loads(completed.stdout)
    streams = data.get('streams') or []
    if not streams:
        raise ValueError(f'no audio stream found: {path}')
    stream = streams[0]
    return {
        'sample_rate': int(stream.get('sample_rate') or 0),
        'channels': int(stream.get('channels') or 0),
        'duration': float(stream.get('duration') or 0),
    }


def decode_f32(path: Path, sample_rate: int, channels: int) -> array:
    command = [
        'ffmpeg', '-v', 'error', '-i', str(path),
        '-ar', str(sample_rate), '-ac', str(channels),
        '-f', 'f32le', '-acodec', 'pcm_f32le', '-',
    ]
    completed = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if completed.returncode != 0:
        raise ValueError(f'ffmpeg decode failed for {path}: {completed.stderr.decode(errors="replace").strip()}')
    samples = array('f')
    samples.frombytes(completed.stdout)
    return samples


def write_f32_wav(path: Path, samples: array, sample_rate: int, channels: int) -> None:
    clipped = array('h')
    for sample in samples:
        value = max(-1.0, min(1.0, float(sample)))
        clipped.append(int(round(value * 32767)))
    with wave.open(str(path), 'wb') as handle:
        handle.setnchannels(channels)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(clipped.tobytes())


def stats(samples: array, sample_rate: int, channels: int) -> dict:
    if not samples:
        return {'frames': 0, 'duration': 0, 'peak': 0, 'rms': 0, 'rms_dbfs': None, 'clipped_samples': 0}
    total = 0.0
    peak = 0.0
    clipped = 0
    for sample in samples:
        value = abs(float(sample))
        peak = max(peak, value)
        total += value * value
        if value >= 0.999:
            clipped += 1
    rms = math.sqrt(total / len(samples))
    return {
        'frames': len(samples) // channels,
        'duration': (len(samples) // channels) / sample_rate,
        'peak': peak,
        'peak_dbfs': 20 * math.log10(peak) if peak > 0 else None,
        'rms': rms,
        'rms_dbfs': 20 * math.log10(rms) if rms > 0 else None,
        'clipped_samples': clipped,
    }


def output_role(stage_id: str, output_path: str) -> str:
    stem = Path(output_path).stem
    if stage_id == 'stage-02-instrumental-stems' and stem == 'vocals':
        return 'vocals_residual'
    return stem


def include_in_final_sum(stage_id: str, role: str) -> bool:
    if role == 'no_vocals':
        return False
    if stage_id == 'stage-01-vocal-instrumental':
        return role == 'vocals'
    return role in {'bass', 'drums', 'other', 'guitar', 'piano', 'vocals', 'vocals_residual'}


def collect_outputs(run_dir: Path, manifest: dict) -> list[dict]:
    outputs = []
    for stage in manifest.get('stages') or []:
        stage_id = stage.get('id') or 'stage'
        stage_dir = run_dir / (stage.get('path') or stage_id)
        for output in stage.get('outputs') or []:
            rel = output.get('path') or ''
            path = stage_dir / rel
            if path.suffix.lower() == '.wav' and path.is_file():
                role = output_role(stage_id, rel)
                outputs.append({
                    'stage_id': stage_id,
                    'role': role,
                    'path': path,
                    'include_in_final_sum': include_in_final_sum(stage_id, role),
                })
    return outputs


def measure_run(run_dir: Path, residual_wav: Path | None = None) -> dict:
    manifest = read_json(run_dir / 'manifest.json')
    input_path = Path(manifest.get('input', {}).get('path', ''))
    if not input_path.is_file():
        raise ValueError(f'input audio not found: {input_path}')
    info = ffprobe(input_path)
    sample_rate = info['sample_rate']
    channels = info['channels']
    original = decode_f32(input_path, sample_rate, channels)
    original_stats = stats(original, sample_rate, channels)
    outputs = collect_outputs(run_dir, manifest)
    if not outputs:
        raise ValueError(f'no wav outputs found: {run_dir}')

    measured_outputs = []
    final_sum = array('f', [0.0]) * len(original)
    final_count = 0
    for output in outputs:
        samples = decode_f32(output['path'], sample_rate, channels)
        n = min(len(original), len(samples))
        output_stats = stats(samples, sample_rate, channels)
        output_stats.update({
            'stage_id': output['stage_id'],
            'role': output['role'],
            'path': str(output['path']),
            'include_in_final_sum': output['include_in_final_sum'],
            'length_delta_frames': (len(samples) - len(original)) // channels,
        })
        measured_outputs.append(output_stats)
        if output['include_in_final_sum']:
            final_count += 1
            for i in range(n):
                final_sum[i] += samples[i]

    residual = array('f', [0.0]) * len(original)
    for i, sample in enumerate(original):
        residual[i] = sample - final_sum[i]
    residual_stats = stats(residual, sample_rate, channels)
    original_rms = original_stats['rms'] or 0.0
    residual_ratio = (residual_stats['rms'] / original_rms) if original_rms else 0.0
    residual_db_vs_original = 20 * math.log10(residual_ratio) if residual_ratio > 0 else None
    if residual_wav:
        write_f32_wav(residual_wav, residual, sample_rate, channels)

    return {
        'schema': 1,
        'kind': 'oss-separation-run-measurement',
        'run_dir': str(run_dir),
        'config': manifest.get('config'),
        'input': {
            'path': str(input_path),
            **info,
            **original_stats,
        },
        'outputs': measured_outputs,
        'final_sum_output_count': final_count,
        'reconstruction_residual': {
            **residual_stats,
            'rms_ratio_vs_original': residual_ratio,
            'rms_db_vs_original': residual_db_vs_original,
            'wav': str(residual_wav) if residual_wav else None,
        },
    }


def markdown(measurement: dict) -> str:
    residual = measurement['reconstruction_residual']
    lines = [
        f"# Separation measurement — {measurement.get('config', {}).get('name')}",
        '',
        f"- run: `{measurement['run_dir']}`",
        f"- input: `{measurement['input']['path']}`",
        f"- input duration: `{measurement['input']['duration']:.3f}s`",
        f"- final summed outputs: `{measurement['final_sum_output_count']}`",
        f"- reconstruction residual RMS vs original: `{residual['rms_db_vs_original']:.2f} dB`" if residual['rms_db_vs_original'] is not None else '- reconstruction residual RMS vs original: `n/a`',
        f"- residual peak: `{residual['peak']:.6f}`",
        '',
        '## Outputs',
        '',
        '| Stage | Role | RMS dBFS | Peak dBFS | Clipped samples | Length delta frames | Included in sum |',
        '| --- | --- | ---: | ---: | ---: | ---: | --- |',
    ]
    for output in measurement['outputs']:
        rms = '' if output['rms_dbfs'] is None else f"{output['rms_dbfs']:.2f}"
        peak = '' if output['peak_dbfs'] is None else f"{output['peak_dbfs']:.2f}"
        lines.append(
            f"| {output['stage_id']} | {output['role']} | {rms} | {peak} | {output['clipped_samples']} | {output['length_delta_frames']} | {output['include_in_final_sum']} |"
        )
    lines.append('')
    lines.append('These measurements check technical consistency only. They do not replace listening tests or ground-truth SDR when real stems are available.')
    lines.append('')
    return '\n'.join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Measure an OSS separation lab run against its original audio')
    parser.add_argument('run_dir', type=Path, help='Lab run directory containing manifest.json')
    parser.add_argument('--output-json', type=Path, help='Measurement JSON path')
    parser.add_argument('--output-md', type=Path, help='Measurement Markdown path')
    parser.add_argument('--residual-wav', type=Path, help='Write original-minus-summed-stems residual WAV')
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(argv)
        run_dir = args.run_dir.expanduser().resolve()
        output_json = args.output_json.expanduser().resolve() if args.output_json else run_dir / 'measurement.json'
        output_md = args.output_md.expanduser().resolve() if args.output_md else run_dir / 'MEASUREMENT.md'
        residual_wav = args.residual_wav.expanduser().resolve() if args.residual_wav else run_dir / 'reconstruction_residual.wav'
        measurement = measure_run(run_dir, residual_wav)
        write_json(output_json, measurement)
        output_md.write_text(markdown(measurement), encoding='utf-8')
        print(output_json)
        print(output_md)
        print(residual_wav)
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f'OSS measure run: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
