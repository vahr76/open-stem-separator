#!/usr/bin/env python3
"""OSS experimental laboratory CLI.

This command is intentionally separate from ytd. It groups source-separation lab,
benchmarking, measurement, comparison and REAPER export commands while the OSS
separation stack is still experimental.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

if getattr(sys, 'frozen', False):
    REPO_ROOT = Path(sys.executable).resolve().parent
else:
    REPO_ROOT = Path(__file__).resolve().parent
SEPARATION_ROOT = REPO_ROOT / 'labs' / 'separation'
TOOLS_ROOT = SEPARATION_ROOT / 'tools'
for path in (SEPARATION_ROOT, TOOLS_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import benchmark as benchmark_tool  # noqa: E402
import compare_runs as compare_tool  # noqa: E402
import measure_run as measure_tool  # noqa: E402
import reaper_project as reaper_tool  # noqa: E402
import separate as separate_tool  # noqa: E402


DEFAULT_BENCHMARK = REPO_ROOT / 'labs' / 'separation' / 'benchmarks' / 'minimal-local.json'
DEFAULT_OUT = Path('/tmp/oss-lab')


def cmd_separate(args: argparse.Namespace) -> int:
    run_dir = separate_tool.run_lab(
        args.config.expanduser().resolve(),
        args.input.expanduser().resolve(),
        args.out.expanduser().resolve(),
        args.dry_run,
    )
    print(f'Run: {run_dir}')
    print(f'Manifest: {run_dir / "manifest.json"}')
    return 0


def cmd_benchmark(args: argparse.Namespace) -> int:
    run_root = benchmark_tool.run_benchmark(
        args.benchmark.expanduser().resolve(),
        args.out.expanduser().resolve(),
        args.dry_run,
        args.max_items,
    )
    print(f'Benchmark: {run_root}')
    print(f'Report: {run_root / "REPORT.md"}')
    return 0


def cmd_measure(args: argparse.Namespace) -> int:
    run_dir = args.run_dir.expanduser().resolve()
    output_json = args.output_json.expanduser().resolve() if args.output_json else run_dir / 'measurement.json'
    output_md = args.output_md.expanduser().resolve() if args.output_md else run_dir / 'MEASUREMENT.md'
    residual_wav = args.residual_wav.expanduser().resolve() if args.residual_wav else run_dir / 'reconstruction_residual.wav'
    measurement = measure_tool.measure_run(run_dir, residual_wav)
    measure_tool.write_json(output_json, measurement)
    output_md.write_text(measure_tool.markdown(measurement), encoding='utf-8')
    print(output_json)
    print(output_md)
    print(residual_wav)
    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    out = compare_tool.compare_runs(
        [path.expanduser().resolve() for path in args.run_dirs],
        args.out.expanduser().resolve(),
        args.label,
    )
    print(out / 'COMPARISON.md')
    print(out / 'comparison.rpp')
    return 0


def cmd_reaper(args: argparse.Namespace) -> int:
    run_dir = args.run_dir.expanduser().resolve()
    output = args.output.expanduser().resolve() if args.output else run_dir / f'{run_dir.name}.rpp'
    path = reaper_tool.write_reaper_project(run_dir, output)
    print(path)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='OSS experimental lab CLI')
    sub = parser.add_subparsers(dest='action', required=True)

    p = sub.add_parser('separate', help='Run a separation lab config')
    p.add_argument('--config', type=Path, required=True)
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--out', type=Path, default=DEFAULT_OUT / 'runs')
    p.add_argument('--dry-run', action='store_true')
    p.set_defaults(func=cmd_separate)

    p = sub.add_parser('benchmark', help='Run a separation benchmark')
    p.add_argument('--benchmark', type=Path, default=DEFAULT_BENCHMARK)
    p.add_argument('--out', type=Path, default=DEFAULT_OUT / 'benchmarks')
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('--max-items', type=int)
    p.set_defaults(func=cmd_benchmark)

    p = sub.add_parser('measure', help='Measure a separation run against its original')
    p.add_argument('run_dir', type=Path)
    p.add_argument('--output-json', type=Path)
    p.add_argument('--output-md', type=Path)
    p.add_argument('--residual-wav', type=Path)
    p.set_defaults(func=cmd_measure)

    p = sub.add_parser('compare', help='Compare runs with reconstruction and residual audio')
    p.add_argument('run_dirs', nargs='+', type=Path)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--label', action='append')
    p.set_defaults(func=cmd_compare)

    p = sub.add_parser('reaper', help='Export a separation run to a REAPER .rpp project')
    p.add_argument('run_dir', type=Path)
    p.add_argument('--output', type=Path)
    p.set_defaults(func=cmd_reaper)

    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = build_parser().parse_args(argv)
        return args.func(args)
    except (OSError, ValueError) as exc:
        print(f'oss-lab: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
