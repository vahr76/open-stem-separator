from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / 'oss_lab.py'
spec = importlib.util.spec_from_file_location('oss_lab_cli', MODULE_PATH)
oss_lab = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(oss_lab)


class OssLabCliTests(unittest.TestCase):
    def test_help_parser_has_expected_commands(self):
        parser = oss_lab.build_parser()
        help_text = parser.format_help()
        self.assertIn('benchmark', help_text)
        self.assertIn('compare', help_text)
        self.assertIn('reaper', help_text)

    def test_benchmark_dry_run_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'source.flac'
            source.write_bytes(b'fake source')
            benchmark = Path(tmp) / 'benchmark.json'
            benchmark.write_text('{\n  "schema": 1,\n  "name": "cli-test",\n  "items": [{"id": "item", "label": "Item", "source": "' + str(source).replace('\\', '\\\\') + '"}],\n  "configs": ["labs/separation/configs/demucs-htdemucs.json"]\n}\n', encoding='utf-8')
            status = oss_lab.main([
                'benchmark',
                '--benchmark', str(benchmark),
                '--out', tmp,
                '--dry-run',
                '--max-items', '1',
            ])
            self.assertEqual(status, 0)
            self.assertTrue(any(Path(tmp).iterdir()))


if __name__ == '__main__':
    unittest.main()
