#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 1:
        print('usage: summarize_run.py /path/to/separation/run', file=sys.stderr)
        return 2
    run_dir = Path(args[0])
    manifest_path = run_dir / 'manifest.json'
    if not manifest_path.is_file():
        print(f'manifest not found: {manifest_path}', file=sys.stderr)
        return 1
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    print(f"run: {run_dir}")
    print(f"status: {manifest.get('status')}")
    print(f"mode: {manifest.get('config', {}).get('mode')}")
    print(f"input: {manifest.get('input', {}).get('path')}")
    for stage in manifest.get('stages', []):
        outputs = stage.get('outputs') or []
        missing = stage.get('missing_outputs') or []
        elapsed = stage.get('elapsed_seconds')
        print(f"stage: {stage.get('id')} status={stage.get('status')} elapsed={elapsed}s outputs={len(outputs)}")
        if missing:
            print(f"  missing: {', '.join(missing)}")
        for output in outputs:
            print(f"  - {output.get('path')} ({output.get('size')} bytes)")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
