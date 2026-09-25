from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / 'labs' / 'separation' / 'tools' / 'benchmark.py'
spec = importlib.util.spec_from_file_location('oss_separation_benchmark', MODULE_PATH)
benchmark = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(benchmark)


class SeparationBenchmarkTests(unittest.TestCase):
    def test_dry_run_creates_report_and_lab_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'source.flac'
            source.write_bytes(b'fake source')
            bench = root / 'benchmark.json'
            bench.write_text(json.dumps({
                'schema': 1,
                'name': 'unit-benchmark',
                'clip_seconds': 5,
                'sample_rate': 44100,
                'channels': 2,
                'items': [{
                    'id': 'song-a',
                    'label': 'Song A',
                    'source': str(source),
                    'start': 0,
                }],
                'configs': ['labs/separation/configs/demucs-htdemucs.json'],
            }), encoding='utf-8')

            run_root = benchmark.run_benchmark(bench, root / 'out', dry_run=True)

            summary = json.loads((run_root / 'benchmark.json').read_text(encoding='utf-8'))
            self.assertEqual(summary['status'], 'ok')
            self.assertEqual(len(summary['results']), 1)
            self.assertEqual(summary['results'][0]['status'], 'ok')
            self.assertTrue((run_root / 'REPORT.md').is_file())
            self.assertTrue(Path(summary['results'][0]['clip']['path']).is_file())


if __name__ == '__main__':
    unittest.main()
